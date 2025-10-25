import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Literal

import aiohttp
from livekit.agents.cli.log import ColoredFormatter, _merge_record_extra

logger = logging.getLogger(__name__)


@dataclass
class LokiRecord:
    created: float
    entry: str
    level: str

    @property
    def ts(self) -> str:
        return str(int(self.created * 1e9))


class Loki(logging.Handler):
    ALL_LOG_LEVELS = frozenset(['noisy', 'debug', 'info', 'warning', 'error', 'critical'])
    IMPORTANT_LOG_LEVELS = frozenset(['warning', 'error', 'critical'])
    MAIN_FILE_NAMES = frozenset(['__main__', '__mp_main__'])

    def __init__(
        self,
        url: str,
        user_id: str,
        api_key: str,
        labels: dict[str, Any],
        mode: Literal["dev", "start", "console"],
        noisy_errors: list[str] = [],
        noisy_strategy: Literal["NOTSET", "supress"] = "supress",
    ):
        super().__init__()
        assert len(labels) <= 15, "Loki labels must be less than 15"
        self.url = url
        self.user_id = user_id
        self.api_key = api_key
        self.labels = {k: str(v) for k, v in labels.items()}
        self.buffer: list[LokiRecord] = []
        self.mode = mode
        self.codepos_to_nrepeats: defaultdict[tuple[str, int], int] = defaultdict(int)
        self.noisy_logs = noisy_errors
        self.noisy_strategy = noisy_strategy
        self.setLevel(logging.DEBUG)  # <- handler accept all logs

        def _single_setup(logger_name: str, propagate: bool, level: int):
            lib_logger = logging.getLogger(logger_name)
            lib_logger.setLevel(level)
            lib_logger.addHandler(self)
            lib_logger.propagate = propagate

        # NOTE by default livekit root logger output to console
        for logger_name in self.MAIN_FILE_NAMES:
            _single_setup(logger_name, True, logging.DEBUG)  # <- main file do not propagate to
        _single_setup("fluently_agents", True, logging.DEBUG)  # <- propagate all logs to console
        if mode in ['dev', 'console']:
            _single_setup("livekit", True, logging.INFO)  # <- propagate all logs to console
        else:  # <- start
            _single_setup("livekit", False, logging.WARNING)  # <- only important logs to loki
        self.formatter = ColoredFormatter(
            "%(timediff)s%(nrepeats)s - %(esc_levelcolor)s%(levelname)s%(esc_reset)s"
            "%(lname)s - %(message)s %(esc_gray)s%(extra)s%(esc_reset)s"
        )
        self.formatter._level_colors["NOISY"] = self.formatter._esc_codes["esc_gray"]

    def emit(self, record: logging.LogRecord):
        def _is_noisy_error(record: logging.LogRecord) -> bool:
            return any(error in record.message for error in self.noisy_logs)

        def _add_timediff(record: logging.LogRecord) -> logging.LogRecord:
            if len(self.buffer) > 0:
                lastrecord: LokiRecord = self.buffer[-1]
                record.timediff = f"[+{record.created - lastrecord.created:.1f}s]"
            else:
                record.timediff = "[firstlog]"
            return record

        def _add_nrepeats(record: logging.LogRecord) -> logging.LogRecord:
            self.codepos_to_nrepeats[(record.pathname, record.lineno)] += 1
            count = self.codepos_to_nrepeats[(record.pathname, record.lineno)]
            if (record.levelname.lower() in self.IMPORTANT_LOG_LEVELS) and (count > 1):
                record.nrepeats = f" x{count}"
            else:
                record.nrepeats = ""
            return record

        def _add_optional_name(record: logging.LogRecord) -> logging.LogRecord:
            if record.name in self.MAIN_FILE_NAMES:
                record.lname = ""
            else:
                record.lname = f" {record.name}"
            return record

        def _add_extra(record: logging.LogRecord) -> logging.LogRecord:
            extra: dict[str, Any] = {}
            _merge_record_extra(record, extra)
            extra.pop("timediff", None)
            if (record.levelname.lower() in self.IMPORTANT_LOG_LEVELS) and (
                record.name not in self.MAIN_FILE_NAMES
            ):
                extra['where'] = f"{record.name} in {record.pathname}:{record.lineno}"
            record.extra = extra
            return record

        record.message = record.getMessage()
        if _is_noisy_error(record):
            if self.noisy_strategy == "NOTSET":
                record.levelname = "NOTSET"
            elif self.noisy_strategy == "supress":
                return
        record = _add_timediff(record)
        record = _add_nrepeats(record)
        record = _add_optional_name(record)
        record = _add_extra(record)
        self.buffer.append(
            LokiRecord(
                record.created,
                self.format(record),
                record.levelname.lower(),
            )
        )

    # TODO finish this
    # @retry_on_failure(max_retries=3, retry_delay=1.0)
    # @log_execution("loki push", measure_time=True)
    async def push(self, timeout: int = 5, max_retries: int = 3, retry_delay: float = 1.0):
        if self.mode == "console":
            return
        if not self.buffer:
            return

        level2entries = defaultdict(list)
        for record in self.buffer:
            level2entries[record.level].append([record.ts, record.entry])
        n_entries = sum(len(entries) for entries in level2entries.values())
        logger.info(f"🔄 Pushing {n_entries} logs to Loki")
        streams = []
        for level, entries in level2entries.items():
            streams.append({"stream": {**self.labels, "level": level}, "values": entries})  # type: ignore
        payload = {"streams": streams}
        headers = {"Content-Type": "application/json"}

        for attempt in range(1, max_retries + 1):
            try:
                auth = aiohttp.BasicAuth(self.user_id, self.api_key)
                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=timeout), auth=auth
                ) as S:
                    async with S.post(self.url, json=payload, headers=headers) as response:
                        status = response.status
                        if 200 <= status < 300:
                            logger.info(f"✅ Sent {n_entries} logs to Loki")
                            self.buffer.clear()
                            return
                        else:
                            response_text = await response.text()
                            raise Exception(f"HTTP {status}: {response_text}")

            except Exception as e:
                if attempt == max_retries:
                    logger.error(f"❌ Failed to send logs after {max_retries} attempts: {e}")
                    raise Exception(f"Failed to send logs after {max_retries} attempts: {e}")
                else:
                    logger.warning(f"🔄 Push logs attempt {attempt}/{max_retries} failed: {e}")
                    await asyncio.sleep(retry_delay)
