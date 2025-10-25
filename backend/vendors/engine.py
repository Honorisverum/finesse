import datetime

import httpx
import httpx_retries


class Engine:
    def __init__(
        self,
        base_url_prefix: str,
        api_key: str,
        *,
        n_tries: int = 3,
        timeout: float = 10,
    ) -> None:
        super().__init__()
        self._client = httpx.AsyncClient(
            base_url=f'{base_url_prefix}-jobs-queue.modal.run',
            headers={'Authorization': f'Bearer {api_key}'},
            transport=httpx_retries.RetryTransport(
                retry=httpx_retries.Retry(
                    total=n_tries,
                    backoff_factor=0.3,
                    allowed_methods=['POST'],
                ),
            ),
            timeout=timeout,
        )

    async def score_chunk(
        self,
        user_id: str,
        session_id: str,
        index: int,
        started_at: datetime.datetime,
        audio_file: bytes,
        *,
        callback_url: str | None = None,
        timeout: float = 15,
    ) -> None:
        files = {'audio_file': ('chunk.wav', audio_file, 'audio/wav')}
        params: dict[str, str | int] = {
            'user_id': user_id,
            'session_id': session_id,
            'index': index,
            'started_at': started_at.isoformat(),
        }
        if callback_url is not None:
            params['callback_url'] = callback_url
        response = await self._client.post(
            url='/score-chunk',
            params=params,
            files=files,
            timeout=timeout,
        )
        response.raise_for_status()
