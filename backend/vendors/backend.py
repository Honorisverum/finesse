import datetime
from typing import Any

import httpx
import httpx_retries


class Backend:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        n_tries: int = 3,
        timeout: float = 10,
    ) -> None:
        super().__init__()
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={'Authorization': f'Bearer {api_key}'},
            transport=httpx_retries.RetryTransport(
                retry=httpx_retries.Retry(
                    total=n_tries,
                    backoff_factor=0.3,
                    allowed_methods=['POST', 'PUT'],
                ),
            ),
            timeout=timeout,
        )

    async def update_first_name(
        self,
        user_id: str,
        first_name: str,
        *,
        timeout: float = 5,
    ) -> None:
        response = await self._client.put(
            url='/webhooks/tutor/first-name',
            json={'user_id': user_id, 'first_name': first_name},
            timeout=timeout,
        )
        response.raise_for_status()

    async def update_transcript(
        self,
        session_id: str,
        transcript: dict[str, Any],
        *,
        timeout: float = 5,
    ) -> None:
        response = await self._client.put(
            url='/webhooks/tutor/transcript',
            json={'session_id': session_id, 'transcript': transcript},
            timeout=timeout,
        )
        response.raise_for_status()

    async def complete_session(
        self,
        user_id: str,
        session_id: str,
        stop_reason: str,
        total_chunks: int,
        submitted_chunks: int,
        started_at: datetime.datetime,
        finished_at: datetime.datetime,
        name: str,
        summary: str,
        highlights: list[str],
        transcript: dict,
        is_scenario_completed: bool | None,
        scenario_score: float | None,
        scenario_feedback: list[dict[str, Any]] | None,
        use_new_storage: bool,
        *,
        timeout: float = 10,
    ) -> None:
        """Complete a session and return the response data."""
        response = await self._client.post(
            url='/webhooks/tutor/complete-session',
            json={
                'user_id': user_id,
                'session_id': session_id,
                'stop_reason': stop_reason,
                'total_chunks': total_chunks,
                'submitted_chunks': submitted_chunks,
                'started_at': started_at.isoformat(),
                'finished_at': finished_at.isoformat(),
                'name': name,
                'summary': summary,
                'highlights': highlights,
                'transcript': transcript,
                'is_scenario_completed': is_scenario_completed,
                'scenario_score': scenario_score,
                'scenario_feedback': scenario_feedback,
                'use_new_storage': use_new_storage,
            },
            timeout=timeout,
        )
        response.raise_for_status()
