import datetime as dt
import logging
from typing import Literal

from mem0 import AsyncMemoryClient
from pydantic import BaseModel, TypeAdapter

from fluently_agents.utils import humanize_time_since

logger = logging.getLogger(__name__)

ORG_ID = 'org_BD6ulFRTb7Ucv8wfoLICY7T77AUWHDtbbvf6QzS9'
# PROJECT_ID = 'proj_RoVOv8jOWEpcWCarVj6WvCKNkvRtikOQ1UzId8WK'
PROJECT_ID = 'proj_fNNVq8Rx1Eq0zbLzM0fD8LQSizyTTy3nmX0gg2V3'
PROMPT = '''
Role: Extract durable tutoring and engagement memories for an English AI tutor.

Only capture short, atomic facts that remain useful across sessions (≥2 weeks) and improve: \
lesson selection, correction behavior, practice planning, and casual conversation quality \
(fun, personal, but safe).

STRICT ATTRIBUTION (required):
- Extract only facts that explicitly describe the user or the tutor agent.
- Ignore generic statements, general truths, advice, or anything not attributed to a person.
- Require an explicit subject via third-person by name or role label.
- Ignore stuff that is only usefull in the moment (like "Stacy greets user"). Memories should be \
somewhat long-term and useful in terms of enriching dialogue context.

Capture (tutoring):
- Proficiency signals (CEFR, self-report, IELTS/TOEFL bands)
- Goals and timelines (exam targets, interviews, relocation, travel)
- Native/other languages (transfer/interference)
- Target dialect/accent and pronunciation goals
- Topic interests (include entertainment tastes, sports teams, books/games)
- Work/industry context (role, domain, communication needs; no employer names)
- Availability/timezone/recurring schedule
- Learning preferences (modality, pace, L1 usage)
- Correction preferences (inline vs end, strictness, format)
- Pain points and error patterns (grammar, vocab, pronunciation)
- Vocabulary domains to build; worthwhile review lists
- Confidence/anxiety/motivation cues
- Achievements and progress milestones
- Constraints and accessibility needs

Capture (engagement & social context; non-identifying only):
- Family and pets (structure, age ranges; no names/ages/dates): e.g., "has 2 kids (school age)", \
"has a dog"
- Hobbies and lifestyle anchors (cooking, running, gaming, coffee, hiking)
- Entertainment tastes (genres, creators without unique identifiers)
- Conversation style and tone (casual/formal, humor, emojis, small talk preference)
- Boundaries and sensitivities (topics to avoid; preferred framing)
- Cultural/holiday observance relevant to tone/schedule (no exact dates)

Exclude:
- PII: names (people/pets), emails, phones, addresses, exact employers/schools, exact dates of \
birth/events, financial data, IDs/tokens/secrets
- One-off logistics that won\'t matter later (e.g., “running late today”)
- Full transcripts or exact grades

Normalization:
- One fact per memory; present tense; ≤120 chars; non-identifying and specific.
- Prefer durable over ephemeral; include time windows only if they change tutoring behavior \
(e.g., "studies M/W evenings").
- Use age ranges ("school age", "teen") instead of exact ages; never store names.
- Deduplicate; update if newer evidence is stronger; avoid contradictions.
- Do not invent facts; use cautious wording if evidence is weak.

Examples:
{"memories":[
  {"category":"family_and_pets","memory":"Has two kids (school age)"},
  {"category":"conversation_style","memory":"Prefers casual tone and light humor"},
  {"category":"topic_interests","memory":"Enjoys football; supports a Premier League team"},
  {"category":"boundaries_and_sensitivities","memory":"Avoid politics; prefers neutral topics"},
  {"category":"goals","memory":"Target IELTS band 7 in 3 months"}
]}
'''
CATEGORIES = [
    {'proficiency_level': 'CEFR level, test bands, and placement signals'},
    {'native_languages': 'User\'s L1 and other languages affecting transfer/interference'},
    {'goals': 'Desired outcomes and timelines (IELTS/TOEFL, interviews, relocation, travel)'},
    {'exam_prep': 'Exam-specific plans, target bands/scores, and test date windows'},
    {'dialect_and_accent': 'Target dialect and accent/pronunciation goals'},
    {
        'topic_interests': (
            'Interests including entertainment, sports, books/games for personalization'
        )
    },
    {
        'work_and_industry': (
            'Professional domain/role and job communication needs (no employer names)'
        )
    },
    {'availability_schedule': 'Timezone, recurring practice times, and preferred session length'},
    {'learning_preferences': 'Modality/style; speaking vs drills; pace; L1 usage'},
    {'correction_preferences': 'When/how to correct; strictness; format'},
    {'pain_points': 'Grammar/vocab/pronunciation weaknesses and recurring error patterns'},
    {'vocabulary_needs': 'Domains/word families to prioritize; review lists to revisit'},
    {'confidence_and_motivation': 'Confidence, anxiety, motivation triggers and blockers'},
    {'achievements_and_progress': 'Milestones, completed units, streaks, breakthroughs'},
    {'constraints': 'Time/device/environment/connectivity and other practical limits'},
    {'accessibility_needs': 'Visual/hearing/cognitive accommodations; font/audio needs'},
    {'social_background': 'Non-identifying life context and culture relevant to rapport'},
    {'family_and_pets': 'Family structure and pets; no names or exact ages/dates'},
    {'hobbies_and_lifestyle': 'Hobbies and lifestyle anchors (running, cooking, travel, gaming)'},
    {'conversation_style': 'Tone, humor, emojis, small talk preference, directness'},
    {'boundaries_and_sensitivities': 'Topics to avoid or handle carefully'},
]


class Memory(BaseModel):
    id: str
    memory: str
    categories: list[str] | None
    created_at: dt.datetime

    def to_content(self, now_at: dt.datetime) -> str:
        return (
            f'content: {self.memory}\n'
            f'categories: {self.categories}\n'
            f'created_at: {humanize_time_since(self.created_at, now_at)}'
        )


class Mem0Memory:
    def __init__(self, user_id: str, agent_id: str, run_id: str, api_key: str) -> None:
        self._client = AsyncMemoryClient(
            org_id=ORG_ID,
            project_id=PROJECT_ID,
            api_key=api_key,
        )
        self._user_id = user_id
        self._agent_id = agent_id
        self._run_id = run_id

    async def add_message(
        self,
        role: Literal['user', 'assistant'],
        content: str,
        name: str | None,
        created_at: dt.datetime | None,
    ) -> None:
        # with self.grafana.gauge_time_seconds('memory_add_time', log=True, logger=logger):
        await self._client.add(
            messages=[{'role': role, 'content': content, 'name': name}],
            user_id=self._user_id,
            agent_id=self._agent_id,
            # run_id=self._run_id,
            metadata={'agent_id': self._agent_id},
            timestamp=int(created_at.timestamp()) if created_at else None,
            custom_instructions=PROMPT,
            custom_categories=CATEGORIES,
        )

    @staticmethod
    def memories_to_content(memories: list[Memory]) -> str:
        now_at = dt.datetime.now(dt.timezone.utc)
        all_memory_content = '\n\n'.join([m.to_content(now_at) for m in memories])
        return f'This is a set of relevant memories:\n\n{all_memory_content}'

    async def search_for_turn(self, content: str, *, top_k: int = 5) -> list[Memory]:
        filters = {
            'AND': [
                {'user_id': self._user_id},
                {'metadata': {'agent_id': self._agent_id}},
            ],
        }
        raw_results = await self._client.search(
            query=content,
            filters=filters,
            top_k=top_k,
        )
        return TypeAdapter(list[Memory]).validate_python(raw_results['results'])

    async def search_for_system(self, prompt: str, *, top_k: int = 15) -> list[Memory]:
        filters = {
            'AND': [
                {'user_id': self._user_id},
                {'metadata': {'agent_id': self._agent_id}},
            ],
        }
        raw_results = await self._client.search(
            query=prompt,
            filters=filters,
            top_k=top_k,
            # https://docs.mem0.ai/platform/features/advanced-retrieval
            rerank=True,
        )
        return TypeAdapter(list[Memory]).validate_python(raw_results['results'])

    async def construct_system_prompt_safe(self, prompt: str) -> str | None:
        try:
            memories = await self.search_for_system(prompt)
        except Exception:
            logger.exception('failed to get memories')
            return None
        if not memories:
            return None
        return Mem0Memory.memories_to_content(memories)


# if self.use_memory_each_turn and new_message.text_content:
#     memories, outcome, search_timeout = [], 'error', 0.5
#     try:
#         with self.grafana.gauge_time_seconds('memory_search_duration'):
#             memories = await asyncio.wait_for(
#                 fut=self.memory.search_for_turn(new_message.text_content),
#                 timeout=search_timeout,
#             )
#             outcome = 'success'
#     except TimeoutError:
#         logger.warning('memory search timed out')
#         outcome = 'timeout'
#     except Exception:
#         logger.exception('error in memory search')
#         outcome = 'error'
#     finally:
#         self.grafana.add('memory_search_outcome', 'enum', outcome)
#     if memories:
#         content = self.memory.memories_to_content(memories)
#         turn_ctx.add_message(role='assistant', content=content)
#         await self.update_chat_ctx(turn_ctx)


# async def main():
#     from dotenv import load_dotenv
#     from fluently_agents.types import Config
#     load_dotenv('.env.development')
#     config = Config.from_environ()
#     memory = Mem0Memory(
#         user_id='0149329c-a7ad-4638-b9ee-353a112c4b8f',
#         agent_id='Stacy',
#         run_id='',
#         api_key=config.MEM0_API_KEY.get_secret_value(),
#     )
#     memories = await memory.search_for_system('Tell me about the user\'s name.')
#     print(Mem0Memory.memories_to_content(memories))
# if __name__ == "__main__":
#     asyncio.run(main())
