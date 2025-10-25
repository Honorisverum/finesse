import asyncio
import logging

from livekit import agents

logger = logging.getLogger(__name__)


def is_active(session: agents.AgentSession) -> bool:
    return (
        session._started
        and (session._activity is not None)
        and (not session._activity.scheduling_paused)
        and (session._closing_task is None)
        and ((room := session._room_io._room) is not None)
        and room.isconnected()
        and (len(room.remote_participants) > 0)
    )


def setup_say_on_silence(
    ctx: agents.JobContext,
    session: agents.AgentSession,
    silence_threshold: float = 8.0,
):
    def _silence():
        try:
            return (
                is_active(session)
                and session.user_state == "listening"
                and session.agent_state == "listening"
            )
        except Exception as e:
            logger.error(f"Error in `_silence`: {e}")
            return False

    async def _say_on_silence():
        logger.info("`say_on_silence` started")
        silence_counter = 0.0
        while True:
            if _silence():
                if (silence_counter := silence_counter + 1) > silence_threshold:
                    await session.generate_reply(
                        instructions=(
                            "User is silent for too long and did not respond. "
                            "Shortly (5-7 words) and emotionally ask if they're still there. "
                            "Then continue/rephrase/expand your last thought (10 words at most) to keep the conversation alive."
                        ),
                        allow_interruptions=False,
                    ).wait_for_playout()
                    silence_counter = 0.0
                else:
                    pass
            else:
                silence_counter = 0.0
            await asyncio.sleep(1)

    task = asyncio.create_task(_say_on_silence())

    async def _shutdown():
        task.cancel()

    ctx.add_shutdown_callback(_shutdown)
