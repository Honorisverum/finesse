import asyncio
import contextlib
import logging
import random
import time
from collections import defaultdict
from collections.abc import Generator
from typing import Literal

import aiohttp

logger = logging.getLogger(__name__)


class Grafana:
    def __init__(
        self,
        attributes: dict[str, str],
        api_key: str,
        url: str,
        mode: str,
    ):
        self.attributes = attributes
        self.api_key = api_key
        self.url = url
        self.metrics: dict[str, list[dict]] = defaultdict(list)
        self.kinds: dict[str, Literal["gauge", "enum", "histogram", "counter", "event"]] = {}
        self.mode = mode

    def add_once(
        self,
        name: str,
        kind: Literal["gauge", "enum", "histogram", "counter", "event"],
        value: float | int | str = 1,
        unit: str = "",
    ):
        self._add(name, kind, value, unit, add_once=True)

    def add(
        self,
        name: str,
        kind: Literal["gauge", "enum", "histogram", "counter", "event"],
        value: float | int | str = 1,
        unit: str = "",
    ):
        self._add(name, kind, value, unit, add_once=False)

    @contextlib.contextmanager
    def gauge_time_seconds(
        self,
        name: str,
        *,
        sample_rate: float = 1.0,
        log: bool = False,
        logger: logging.Logger | None = None,
    ) -> Generator[None, None, float | None]:
        assert 0.0 <= sample_rate <= 1.0
        if sample_rate < 1.0 and random.random() > sample_rate:
            yield
            return None
        t0 = time.perf_counter()
        try:
            yield
        finally:
            value = time.perf_counter() - t0
            self.add(name, 'gauge', value, 's')
            if log:
                assert logger is not None
                logger.info(f'gauge {name}', extra={'value': value})
            return value

    def _add(
        self,
        name: str,
        kind: Literal["gauge", "enum", "histogram", "counter", "event"],
        value: float | int | str = 1,
        unit: str = "",
        add_once: bool = False,
    ):
        timestamp_ns = int(time.time() * 1e9)
        if add_once and (name in self.metrics):
            return
        attrs = [{"key": k, "value": {"stringValue": str(v)}} for k, v in self.attributes.items()]

        if kind == "gauge":
            assert isinstance(value, int | float), f"{name}: value must be a number"
            data_point = {
                "asDouble": float(value),
                "timeUnixNano": timestamp_ns,
                "startTimeUnixNano": timestamp_ns,
                "attributes": attrs,
            }
            metric_data = {
                "name": name,
                "unit": unit,
                "gauge": {"dataPoints": [data_point]},
            }

        if kind == "event":
            data_point = {
                "asDouble": 1.0,
                "timeUnixNano": timestamp_ns,
                "startTimeUnixNano": timestamp_ns,
                "attributes": attrs,
            }
            metric_data = {
                "name": name,
                "unit": unit,
                "gauge": {"dataPoints": [data_point]},
            }

        elif kind == "enum":
            assert isinstance(value, str), f"{name}: enum value must be a string"
            attrs.append({"key": name, "value": {"stringValue": value}})
            data_point = {
                "asInt": 1,
                "timeUnixNano": timestamp_ns,
                "startTimeUnixNano": timestamp_ns,
                "attributes": attrs,
            }
            metric_data = {
                "name": name,
                "unit": unit,
                "gauge": {"dataPoints": [data_point]},
            }

        elif kind == "histogram":
            raise NotImplementedError("Histogram metrics are not supported yet")

        elif kind == "counter":
            assert isinstance(value, int | float), f"{name}: counter value must be a number"
            if name in self.metrics and self.metrics[name]:
                existing_metric = self.metrics[name][0]  # Take first (and only) metric
                existing_datapoint = existing_metric["gauge"]["dataPoints"][0]
                existing_datapoint["asDouble"] += float(value)
                existing_datapoint["timeUnixNano"] = timestamp_ns  # Update timestamp
                return
            else:
                data_point = {
                    "asDouble": float(value),
                    "timeUnixNano": timestamp_ns,
                    "startTimeUnixNano": timestamp_ns,
                    "attributes": attrs,
                }
                metric_data = {
                    "name": name,
                    "unit": unit,
                    "gauge": {"dataPoints": [data_point]},
                }

        assert self.kinds.setdefault(name, kind) == kind, f"Metric {name} has wrong kind"
        self.metrics[name].append(metric_data)

    def get(self, name: str, default: float | int | None = None) -> float | str:
        if (name not in self.metrics) and (default is not None):
            return default
        assert name in self.metrics, f"Metric {name} not found"
        assert self.metrics[name], f"Metric {name} is empty"

        if self.kinds[name] in ["gauge", "counter"]:
            metric_data = self.metrics[name][-1]
            data_point = metric_data["gauge"]["dataPoints"][0]
            return (
                data_point["asDouble"] if "asDouble" in data_point else float(data_point["asInt"])
            )
        elif self.kinds[name] == "enum":
            metric_data = self.metrics[name][-1]
            data_point = metric_data["gauge"]["dataPoints"][0]
            for attr in data_point["attributes"]:
                if attr["key"] == name:
                    return attr["value"]["stringValue"]
            raise ValueError(f"Metric `{name}` with kind `enum` has no value")
        elif self.kinds[name] == "event":
            return len(self.metrics[name])
        elif self.kinds[name] == "histogram":
            raise NotImplementedError("Histogram metrics are not supported yet")
        else:
            raise ValueError(f"Metric `{name}` with kind `{self.kinds[name]}` is not supported")

    async def push(self, timeout: int = 5, max_retries: int = 3, retry_delay: float = 1.0):
        if self.mode == "console":
            return
        if not self.metrics:
            return
        payload_metrics = sum(self.metrics.values(), [])
        payload = {"resourceMetrics": [{"scopeMetrics": [{"metrics": payload_metrics}]}]}

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        for attempt in range(1, max_retries + 1):
            try:
                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as session:
                    async with session.post(self.url, json=payload, headers=headers) as response:
                        status = response.status
                        if 200 <= status < 300:
                            logger.info(f"✅ Pushed {len(self.metrics)} metrics to grafana")
                            self.metrics.clear()
                            return
                        else:
                            response_text = await response.text()
                            raise Exception(f"HTTP {status}: {response_text}")

            except Exception as e:
                if attempt == max_retries:
                    logger.error(
                        f"❌ Failed to push grafana metrics after {max_retries} attempts | {e}"
                    )
                    raise e
                else:
                    logger.warning(
                        f"🔄 Retrying to push grafana metrics {attempt}/{max_retries} | {e}"
                    )
                    await asyncio.sleep(retry_delay)
