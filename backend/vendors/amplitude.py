from __future__ import annotations

import asyncio
import logging
import time
from typing import Annotated, Any, Literal

import aiohttp
from pydantic import BeforeValidator, WrapValidator
from typing_extensions import TypeVar

logger = logging.getLogger(__name__)


def _coerce_boolish(v: Any) -> ExpAB:
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.lower() in ('true', '1', '1.0', 'on', 'yes')
    if isinstance(v, int):
        return v == 1
    return False


T = TypeVar('T')


def _coerce_enumish(v: Any, handler) -> ExpABCPlus[T]:
    try:
        return handler(v)
    except Exception:
        return None


ExpAB = Annotated[bool | None, BeforeValidator(_coerce_boolish)]
ExpABCPlus = Annotated[T | None, WrapValidator(_coerce_enumish)]


class Amplitude:
    """
    Amplitude API client for experiments.
    """

    def __init__(self, user_id: str, api_key: str):
        self.user_id = user_id
        self.api_key = api_key
        self._vardata: dict[str, str] | None = None
        self._assigment_url: str = "https://api.lab.amplitude.com/v1"
        self._exposure_url: str = "https://api2.amplitude.com/2/httpapi"
        self._assigment_task: asyncio.Task | None = None
        self._exposure_task: asyncio.Task | None = None

    @property
    def vardata(self) -> dict[str, str]:
        return self._vardata or {}

    async def _request_with_retry(
        self,
        context: str,
        url: str,
        params: dict = {},
        json_data: dict = {},
        method: Literal["GET", "POST"] = "GET",
        n_retries: int = 3,
        timeout: int = 1,
        sleep: float = 0.01,
    ):
        """Make HTTP request with retry logic"""
        assert method in ["GET", "POST"], "Invalid method"
        for attempt in range(1, n_retries + 1):
            try:
                async with aiohttp.ClientSession() as S:
                    if method == "GET":
                        async with S.get(
                            url,
                            headers={"Authorization": f"Api-Key {self.api_key}"},
                            params=params,
                            timeout=aiohttp.ClientTimeout(total=timeout),
                        ) as response:
                            response.raise_for_status()
                            out = await response.json()
                    elif method == "POST":
                        async with S.post(
                            url,
                            headers={"Content-Type": "application/json"},
                            params=params,
                            json=json_data,
                            timeout=aiohttp.ClientTimeout(total=timeout),
                        ) as response:
                            response.raise_for_status()
                            out = await response.json()
                    logger.info(f"✅ amplitude API {context} request completed")
                    return out
            except Exception as e:
                if attempt == n_retries:
                    logger.error(f"❌ amplitude API {context} error | {e}")
                    raise e
                else:
                    logger.warning(
                        f"🔄 amplitude API {context} on attempt {attempt}/{n_retries} | {e}"
                    )
                    await asyncio.sleep(sleep)

    def assign(self, experiments: list[str]) -> asyncio.Task:
        async def _assigment_task():
            if not experiments:
                self._vardata = {}
                return
            t1 = time.time()
            url = f"{self._assigment_url}/vardata"  # could be also /flags for configs
            params = {"user_id": self.user_id, "flag_keys": ",".join(experiments)}
            data = await self._request_with_retry(
                context="assigment", url=url, params=params, method="GET"
            )
            self._vardata = {flag_key: variant.get("key") for flag_key, variant in data.items()}
            t2 = time.time()
            logger.info(f"`assigment` amplitude task completed in {t2 - t1:.1f}s")

        if self._assigment_task is None:
            self._assigment_task = asyncio.create_task(_assigment_task())
        return self._assigment_task

    def expose(self) -> asyncio.Task:
        async def _exposure_task():
            if not self._vardata:
                return
            t1 = time.time()
            url = self._exposure_url
            events = []
            for flag_key, variant in self._vardata.items():
                events.append(
                    {
                        "user_id": str(self.user_id),
                        "event_type": "$exposure",
                        "event_properties": {"flag_key": flag_key, "variant": variant},
                        "time": int(time.time() * 1000),
                    }
                )
            payload = {
                "api_key": self.api_key,
                "events": events,
            }
            await self._request_with_retry(
                context="exposure", url=url, json_data=payload, method="POST"
            )
            t2 = time.time()
            logger.info(f"`exposure` task completed in {t2 - t1:.2f}s")

        if self._exposure_task is None:
            self._exposure_task = asyncio.create_task(_exposure_task())
        return self._exposure_task
