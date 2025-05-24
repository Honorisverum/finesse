import asyncio
import json
import logging
import os
import random
import re
import sys
import time
from dataclasses import dataclass
from dotenv import load_dotenv

from livekit import agents
from livekit.agents.voice import room_io
import livekit.agents.cli.cli
from livekit.agents.cli import _run
from livekit.agents.cli.proto import CliArgs
from livekit.agents.plugin import Plugin
from livekit.plugins.turn_detector.english import EnglishModel as EnglishTurnDetector
from livekit.agents import function_tool, RunContext
from livekit.plugins import deepgram, elevenlabs, hume, noise_cancellation, openai, silero
from hume.tts.types.posted_utterance_voice_with_id import PostedUtteranceVoiceWithId

import checker as finesse_checker
import hint as finesse_hint
import postanalyser as finesse_postanalyser
import tts as finesse_tts
import utils as finesse_utils


load_dotenv(override=True)
logger = logging.getLogger("livekit.agents")


@dataclass
class SessionInfo:
    userid: str | None = None
    username: str | None = None
    usergender: str | None = None
    skill: str | None = None
    scenario_name: str | None = None
    scenario_data: dict | None = None


class FinesseChatMessage(agents.ChatMessage):
    duration: float | None = None
    start_offset: float | None = None
    end_offset: float | None = None
FinesseChatMessage.model_rebuild()


class FinesseTutor(agents.Agent, finesse_tts.AdapterStreamingFalseNextTextTTS):
    def __init__(
        self,
        userdata: SessionInfo,
        mode: str = "dev",
    ) -> None:
        self.userdata = userdata
        self.mode = mode
        instructions = finesse_utils.assemble_prompt(
            scenario=userdata.scenario_data,
            username=userdata.username,
            usergender=userdata.usergender,
        )
        super().__init__(instructions=instructions)

    def split_opening(self, text) -> tuple[str, str]:
        roleplay_match = re.search(r'(\*[^*]*\*)', text)
        if not roleplay_match:
            return '', text.strip()
        roleplay = roleplay_match.group(1)
        script = text.replace(roleplay, '', 1).strip()
        return roleplay, script

    async def on_enter(self) -> None:
        self.session._start_ts = time.time()
        self.session._user_turn_start_offset = None
        self.session._user_turn_end_offset = None
        self.session._user_turn_duration = 0.0
        self.session._agent_turn_start_offset = None
        self.session._agent_turn_end_offset = None
        self.session._agent_turn_duration = 0.0
        self.session._last_checker = None
        self.session._hints = []
        self.session._checker = []
        roleplay, script = self.split_opening(self.userdata.scenario_data["opening"])
        self.session.history.add_message(role="user", content=roleplay)
        self.session.say(text=script, allow_interruptions=False, add_to_chat_ctx=True)
    
    def get_session_history(self):
        history = [
            {
                "role": e['role'],
                "text": e['content'][0],
                "start": e['start_offset'],
                "end": e['end_offset'],
            }
            for e in self.session.history.to_dict(exclude_function_call=True)["items"]
        ]
        return history
    
    async def on_user_turn_completed(self, turn_ctx: agents.ChatContext, new_message: agents.ChatMessage):
        logger.info(f"on_user_turn_completed")
        await self.early_termination()
    
    async def make_rpc_call(self, method, payload):
        if self.mode != "console":
            client_identity = next(iter(self.session._room_io._room.remote_participants.keys()))
            logger.info(f"Sending {method} to {client_identity} with payload: {payload}")
            return await self.session._room_io._room.local_participant.perform_rpc(
                destination_identity=client_identity,
                method=method,
                payload=payload,
            )
    
    async def early_termination(self):
        logger.info(f"early_termination: {self.session._last_checker}")
        if self.session._last_checker is not None:
            if self.session._last_checker["is_goal_complete"]:
                logger.info("Good ending")
                goal = self.userdata.scenario_data["goal"]
                await self.session.generate_reply(
                    instructions=(
                        f"The dialogue has naturally progressed to a point where {goal} feels successfully addressed. "
                        f"Conclude the conversation with a strong, in-character statement that reflects your persona's "
                        f"unique perspective on this positive resolution. Make it a memorable final line, true to your "
                        f"character and the preceding interaction."
                    ),
                    allow_interruptions=False,
                ).wait_for_playout()
                payload = {"message": "Congratulations! You have successfully completed the goal."}
                await self.make_rpc_call(method="end_conversation", payload=json.dumps(payload))
            elif self.session._last_checker["is_bad_ending_triggered"]:
                logger.info("Bad ending")
                goal = self.userdata.scenario_data["goal"]
                await self.session.generate_reply(
                    instructions=(
                        f"The dialogue has unfortunately not led to achieving {goal}, or has reached a clear negative turning point. "
                        f"Deliver a final, impactful in-character statement that authentically expresses your persona's reaction to this unfavorable outcome. "
                        f"This should be a powerful line that is true to your character and the situation."
                    ),
                    allow_interruptions=False,
                ).wait_for_playout()
                payload = {"message": "Unfortunately, the conversation has reached a bad ending. Please try again."}
                await self.make_rpc_call(method="end_conversation", payload=json.dumps(payload))
    
    @function_tool()
    async def end_conversation(self, ctx: RunContext[SessionInfo]) -> None:
        """Call this function if the user verbally indicates they want to finish or leave."""
        logger.info("`end_conversation` tool called")
        await self.session.generate_reply(
            instructions=(
                "The user is now choosing to end the conversation. Deliver a final, in-character remark that acknowledges this. "
                "Your closing line should be consistent with your established persona and the overall context of discussion, "
                "perhaps with a subtle, character-appropriate nod to {goal} if it fits the moment."
            ),
            allow_interruptions=False,
        ).wait_for_playout()
        payload = {"message": "Next time you'll do better!"}
        await self.make_rpc_call(method="end_conversation", payload=json.dumps(payload))
        return None


NOISE_CANCELLATION = False
TURN_DETECTION = True
TTS = "elevenlabs"  # elevenlabs | nostreamnexttextelevenlabs | hume


async def entrypoint(ctx: agents.JobContext):
    room_name = ctx.room.name
    mode = os.getenv("LIVEKIT_MODE")
    logger.info(f"Starting entrypoint with room_name: {room_name} and mode: {mode}")

    await ctx.connect(auto_subscribe=agents.AutoSubscribe.AUDIO_ONLY)
    if mode != "console":
        await ctx.wait_for_participant()

    ALL_SCENARIOS = finesse_utils.load_scenarios()
    if mode != "console":
        remote_participant_identity = next(iter(ctx.room.remote_participants.keys()))
        remote_participant = ctx.room.remote_participants[remote_participant_identity]
        attributes = remote_participant.attributes
        logger.info(f"attributes {attributes}")
        skill = attributes["skill"]
        scenario_name = attributes["scenarioName"]
        scenario_data = ALL_SCENARIOS[skill][scenario_name]
    else:
        attributes = {}
        skill = random.choice(list(ALL_SCENARIOS.keys()))
        scenario_name = random.choice(list(ALL_SCENARIOS[skill].keys()))
        scenario_data = ALL_SCENARIOS[skill][scenario_name]
    
    userid = attributes.get("user_id", "1234567890")
    username = attributes.get("user_name", "Vlad")
    usergender = attributes.get("user_gender", "male")
    # elevenlabs_voice_id = {'female': 'jB2lPb5DhAX6l1TLkKXy', 'male': 'TX3LPaxmHKxFdv7VOQHJ'}[scenario_data['botgender']]
    elevenlabs_voice_id = scenario_data['elevenlabs_voice_id']

    userdata = SessionInfo(
        userid=userid,
        username=username,
        usergender=usergender,
        skill=skill,
        scenario_name=scenario_name,
        scenario_data=scenario_data,
    )
    logger.info(f"voice_description: {scenario_data['voice_description']}")
    agent_session_kwargs = {
        "userdata": userdata,
        "stt": deepgram.STT(
            model="nova-3-general",
            language="en-US",
            filler_words=True,
            api_key=os.getenv("DEEPGRAM_API_KEY"),
        ),
        "llm": openai.LLM(
            model="gpt-4.1",
            api_key=os.getenv("OPENAI_API_KEY"),
        ),
        "vad": silero.VAD.load(),
        "allow_interruptions": True,
        "min_interruption_duration": 0.5,
        "min_endpointing_delay": 0.5,
        "max_endpointing_delay": 6.0,
    }
    if TTS == "elevenlabs":
        agent_session_kwargs["tts"] = elevenlabs.TTS(
            voice_id=elevenlabs_voice_id,
            encoding="mp3_44100_96",
            model="eleven_turbo_v2_5",
            api_key=os.getenv("ELEVENLABS_API_KEY"),
        )
    elif TTS == "nostreamnexttextelevenlabs":
        agent_session_kwargs["tts"] = finesse_tts.StreamingFalseNextTextTTS(
            voice_id=elevenlabs_voice_id,
            encoding="mp3_44100_96",
            model="eleven_monolingual_v1",
            api_key=os.getenv("ELEVENLABS_API_KEY"),
            next_text=" they say her voice trembling with sadness.",
        )
    elif TTS == "hume":
        agent_session_kwargs["tts"] = hume.TTS(
            voice=PostedUtteranceVoiceWithId(
                id="9e068547-5ba4-4c8e-8e03-69282a008f04",
                provider="HUME_AI",
            ),
            instant_mode=True,
            description="melancholy and frustrated",  # description=scenario_data["voice_description"],
            speed=1.0,
            api_key=os.getenv("HUME_API_KEY"),
        )
    if TURN_DETECTION:
        agent_session_kwargs["turn_detection"] = EnglishTurnDetector()
    session = agents.AgentSession[SessionInfo](**agent_session_kwargs)
    
    @session.on("user_state_changed")
    def _on_user_state_changed(ev: agents.UserStateChangedEvent):
        # logger.info(f"User state changed: {ev.old_state} -> {ev.new_state}")
        if (ev.new_state == 'speaking') and (session._user_turn_start_offset is None):
            session._user_turn_start_offset = time.time() - session._start_ts
        if (ev.new_state == 'speaking'):
            session._user_speaking_start_ts = time.time()
        elif (ev.old_state == 'speaking'):
            session._user_turn_duration += time.time() - session._user_speaking_start_ts
            session._user_turn_end_offset = time.time() - session._start_ts

    @session.on("agent_state_changed")
    def _on_agent_state_changed(ev: agents.AgentStateChangedEvent):
        # logger.info(f"Agent state changed: {ev.old_state} -> {ev.new_state}")
        if (ev.new_state == 'speaking') and (session._agent_turn_start_offset is None):
            session._agent_turn_start_offset = time.time() - session._start_ts
        if (ev.new_state == 'speaking'):
            session._agent_speaking_start_ts = time.time()
        elif (ev.old_state == 'speaking'):
            session._agent_turn_duration += time.time() - session._agent_speaking_start_ts
            session._agent_turn_end_offset = time.time() - session._start_ts
    
    @ctx.room.local_participant.register_rpc_method("postanalyzer")
    async def handle_postanalyzer(payload: dict):
        agent = session.current_agent
        scenario_data = agent.userdata.scenario_data
        postanalyzer_result = await finesse_postanalyser.apostanalyser(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            chat_context=session.history.items,
            goal=scenario_data["goal"],
            username=agent.userdata.username,
            botname=scenario_data["botname"],
            skill=scenario_data["skill"],
            model="openai/gpt-4.1",
            bracket='quotation',
            temperature=0.5,
            context_window_size=100,
        )
        return json.dumps(postanalyzer_result)
    
    @ctx.room.local_participant.register_rpc_method("hint")
    async def handle_hint(payload: dict):
        agent = session.current_agent
        scenario_data = agent.userdata.scenario_data
        hint = await finesse_hint.ahint(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            chat_context=session.history.items,
            botname=scenario_data["botname"],
            username=agent.userdata.username,
            goal=scenario_data["goal"],
            skill=scenario_data["skill"],
            character=scenario_data["character"],
            negprompt=scenario_data["negprompt"],
            previous_hints=session._hints,
            model="openai/gpt-4.1",
            bracket='quotation',
            temperature=0.5,
            context_window_size=20,
        )
        session._hints.append(hint)
        return json.dumps({'hint': hint['hint'], 'category': hint['category']})

    @session.on("conversation_item_added")
    def on_conversation_item_added(event: agents.ConversationItemAddedEvent):
        # logger.info(f"Conversation item added from {event.item.role}: {event.item.text_content}")
        if event.item.role == 'user':
            session._chat_ctx.items[-1] = FinesseChatMessage(
                id=event.item.id,
                type=event.item.type,
                role=event.item.role,
                content=event.item.content,
                duration=session._user_turn_duration,
                start_offset=session._user_turn_start_offset,
                end_offset=session._user_turn_end_offset,
            )
            session._user_turn_duration = 0.0
            session._user_turn_start_offset = None
            session._user_turn_end_offset = None
        elif event.item.role == 'assistant':
            session._chat_ctx.items[-1] = FinesseChatMessage(
                id=event.item.id,
                type=event.item.type,
                role=event.item.role,
                content=event.item.content,
                duration=session._agent_turn_duration,
                start_offset=session._agent_turn_start_offset,
                end_offset=session._agent_turn_end_offset,
            )
            session._agent_turn_duration = 0.0
            session._agent_turn_start_offset = None
            session._agent_turn_end_offset = None

            n_user_messages = len([e for e in session._chat_ctx.items if e.role == 'user'])
            is_agent_message = event.item.role == 'assistant'
            async def handle_checker():
                try:
                    agent = session.current_agent
                    scenario_data = agent.userdata.scenario_data
                    checker_result = await finesse_checker.achecker(
                        api_key=os.getenv("OPENROUTER_API_KEY"),
                        chat_context=session.history.items,
                        goal=scenario_data["goal"],
                        botname=scenario_data["botname"],
                        username=agent.userdata.username,
                        previous_progress=session._last_checker['progress_towards_goal'] if (session._last_checker is not None) else None,
                        model="openai/gpt-4.1",
                        bracket='quotation',
                        temperature=0,
                        context_window_size=20,
                    )
                    session._last_checker = checker_result
                    session._checker.append(checker_result)
                    await agent.make_rpc_call(method="checker", payload=json.dumps(checker_result))
                except Exception as e:
                    logger.error(f"Error getting checker result: {e}")
            if (mode != "console") and (n_user_messages > 0) and (is_agent_message):
                asyncio.create_task(handle_checker())

    output_sr = { "elevenlabs": 44100, "nostreamnexttextelevenlabs": 44100, "hume": hume.tts.DEFAULT_SAMPLE_RATE }[TTS]
    session_start_kwargs = {
        "room": ctx.room,
        "agent": FinesseTutor(userdata=userdata, mode=mode),
        "room_output_options": room_io.RoomOutputOptions(audio_sample_rate=output_sr),
    }
    if NOISE_CANCELLATION:
        session_start_kwargs["room_input_options"] = room_io.RoomInputOptions(noise_cancellation=noise_cancellation.BVC())
    await session.start(**session_start_kwargs)


def run_livekit_worker(mode):
    assert mode in ["dev", "start", "console"]
    logger.info(f"Running livekit worker with mode={mode}")

    # mimic cli-run -> download_files
    try:
        logger.info("plugins", Plugin.registered_plugins)
        for plugin in Plugin.registered_plugins:
            logger.info(f"Downloading files for {plugin}")
            plugin.download_files()
            logger.info(f"Finished downloading files for {plugin}")
    except Exception as e:
        logger.error(f"Error downloading files: {e}")
        raise e

    # mimic cli-run -> dev/start/console
    try:
        if mode == "console":
            opts = agents.WorkerOptions(
                entrypoint_fnc=entrypoint,
                ws_url=os.getenv("LIVEKIT_URL"),
                api_key=os.getenv("LIVEKIT_API_KEY"),
                api_secret=os.getenv("LIVEKIT_API_SECRET"),
            )
            opts.drain_timeout = 0
            opts.job_executor_type = agents.JobExecutorType.THREAD
            args = CliArgs(
                opts=opts,
                log_level="DEBUG",
                devmode=True,
                asyncio_debug=False,
                console=True,
                register=False,
                watch=False,
                simulate_job=agents.SimulateJobInfo(room="mock-console"),
            )
            livekit.agents.cli.cli.CLI_ARGUMENTS = args
            _run.run_worker(args)
        elif mode in ["dev", "start"]:
            opts = agents.WorkerOptions(
                entrypoint_fnc=entrypoint,
                ws_url=os.getenv("LIVEKIT_URL"),
                api_key=os.getenv("LIVEKIT_API_KEY"),
                api_secret=os.getenv("LIVEKIT_API_SECRET"),
            )
            args = CliArgs(
                opts=opts,
                log_level={"dev": "DEBUG", "start": "INFO"}[mode],
                devmode=mode == "dev",
                asyncio_debug=False,
                register=True,
                watch=False,
            )
            livekit.agents.cli.cli.CLI_ARGUMENTS = args
            _run.run_worker(args)
    except Exception as e:
        logger.error(f"Error while running livekit worker: {e}")
        raise e
    
    logger.info("livekit worker end with no error, raising exception for restart")
    raise Exception("Raise exception for restart")


if __name__ == "__main__":
    
    if len(sys.argv) > 1:
        mode = sys.argv[1].strip()
        print(f"mode: {mode}")
    else:
        raise ValueError("mode is not provided")

    os.environ["LIVEKIT_MODE"] = mode

    while True:
        try:
            run_livekit_worker(mode=mode)
        except Exception as e:
            logger.error(f"Livekit worker crashed: {e}")
            logger.info("Restarting in 10 seconds...")
            time.sleep(10)
