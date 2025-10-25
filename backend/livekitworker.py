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
from tenacity import retry, stop_after_attempt
from livekit import agents
from livekit.agents.voice import room_io
import livekit.agents.cli.cli
from livekit.agents.cli import _run
from livekit.agents.cli.proto import CliArgs
from livekit.agents.plugin import Plugin
from livekit.plugins.turn_detector.english import EnglishModel as EnglishTurnDetector
from livekit.agents import function_tool, RunContext
from livekit.plugins import deepgram, elevenlabs, noise_cancellation, openai, silero

import emoji

from silence import setup_say_on_silence

import checker as finesse_checker
import hint as finesse_hint
import postanalyser as finesse_postanalyser
import utils as finesse_utils


# TODO
# 1) [v] update livekit code
# 2) hints: better model, better prompt, reliability, run if 3 turns no improve
# 3) checker: better model, better prompt, reliability
# 4) postanalyzer: best model, better prompt, reliability
# 5) [v] say on silence
# 6) tune prompts for top5 or choose best
# 7) tools calls?


load_dotenv(override=True)
logger = logging.getLogger("livekit.agents")


@dataclass
class SessionInfo:
    userid: str
    username: str
    usergender: str
    skill: str
    scenario_name: str
    scenario_data: dict


class FinesseTutor(agents.Agent):
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
    
    async def on_user_turn_completed(self, turn_ctx: agents.ChatContext, new_message: agents.ChatMessage):
        logger.info("on_user_turn_completed")
        await self.early_termination()
    
    @retry(stop=stop_after_attempt(3))
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
    async def emoji_reaction(self, ctx: RunContext[SessionInfo], reaction: str):
        """Use this tool to show a reaction to the user's last message using emojis. Use this as frequently as needed. Only a single emoji at a time allowed."""
        logger.info(f"`emoji_reaction` tool called with reaction: {reaction}")
        reaction = reaction.strip()
        
        if emoji and not emoji.is_emoji(reaction):
            reaction = reaction.replace(":", "")
            try:
                reaction = emoji.emojize(f":{reaction}:", language='alias')
            except Exception:
                pass
        
        # Send emoji to frontend
        if self.mode != "console":
            asyncio.create_task(
                self.make_rpc_call(method="reaction", payload=reaction)
            )
        return ""
    
    @function_tool()
    async def end_conversation(self, ctx: RunContext[SessionInfo]):
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


async def entrypoint(ctx: agents.JobContext):
    room_name = ctx.room.name
    mode = os.getenv("LIVEKIT_MODE")
    logger.info(f"Starting entrypoint with room_name: {room_name} and mode: {mode}")

    await ctx.connect(auto_subscribe=agents.AutoSubscribe.AUDIO_ONLY)
    if mode != "console":
        await ctx.wait_for_participant()

    ALL_SCENARIOS = finesse_utils.load_scenarios()
    if mode == "console":
        attributes = {'user_id': '1234567890', 'userName': 'Vlad', 'userGender': 'male'}
        skill = random.choice(list(ALL_SCENARIOS.keys()))
        scenario_name = random.choice(list(ALL_SCENARIOS[skill].keys()))
    else:
        remote_participant_identity = next(iter(ctx.room.remote_participants.keys()))
        remote_participant = ctx.room.remote_participants[remote_participant_identity]
        attributes = remote_participant.attributes
        logger.info(f"attributes {attributes}")
        skill = attributes["skill"]
        scenario_name = attributes["scenarioName"]
        attributes['user_id'] = '1234567890'
    scenario_data = ALL_SCENARIOS[skill][scenario_name]
    
    userdata = SessionInfo(
        userid=attributes["user_id"],
        username=attributes["userName"],
        usergender=attributes["userGender"],
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
        "tts": elevenlabs.TTS(
            voice_id=scenario_data['elevenlabs_voice_id'],
            encoding="mp3_44100_96",
            model="eleven_turbo_v2_5",
            api_key=os.getenv("ELEVENLABS_API_KEY"),
        ),
        "vad": silero.VAD.load(),
        "allow_interruptions": True,
        "min_interruption_duration": 0.5,
        "min_endpointing_delay": 0.5,
        "max_endpointing_delay": 6.0,
        "turn_detection": EnglishTurnDetector(),
    }
    session = agents.AgentSession[SessionInfo](**agent_session_kwargs)

    setup_say_on_silence(ctx, session)
    @session.on("user_state_changed")
    def _on_user_state_changed(ev: agents.UserStateChangedEvent):
        logger.info(f"User state changed: {ev.old_state} -> {ev.new_state}")

    @session.on("agent_state_changed")
    def _on_agent_state_changed(ev: agents.AgentStateChangedEvent):
        logger.info(f"Agent state changed: {ev.old_state} -> {ev.new_state}")
    
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
        logger.info(f"Conversation item added from {event.item.role}: {event.item.text_content}")
        if event.item.role == 'assistant':
            n_user_messages = len([e for e in session._chat_ctx.items if (e.type == 'message' and e.role == 'user')])
            is_agent_message = event.item.type == 'message' and event.item.role == 'assistant'
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

    session_start_kwargs = {
        "room": ctx.room,
        "agent": FinesseTutor(userdata=userdata, mode=mode),
        "room_output_options": room_io.RoomOutputOptions(audio_sample_rate=44100),
        "room_input_options": room_io.RoomInputOptions(noise_cancellation=noise_cancellation.BVC()),
    }
    await session.start(**session_start_kwargs)


def run_livekit_worker(mode):
    assert mode in ["dev", "start", "console"]
    logger.info(f"Running livekit worker with mode={mode}")

    # mimic cli-run -> download_files
    try:
        logger.info(f"plugins: {Plugin.registered_plugins}")
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
