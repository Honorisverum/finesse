from __future__ import annotations

import asyncio
import json
import logging
import os
import random
from copy import deepcopy
from typing import TYPE_CHECKING, Any, Literal, TypeVar, cast

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from livekit.agents import llm as lka_llm
from pydantic import BaseModel, Field, SecretStr

if TYPE_CHECKING:
    from fluently_agents.vendors import (
        LLMAPI,
        AsyncS3,
    )

logger = logging.getLogger(__name__)

# load_dotenv(override=True)


T = TypeVar("T", bound=BaseModel)


class FamilyDetails(BaseModel):
    """Structured facts about the user's family life."""

    marital_status: Literal['single', 'married', 'partnered'] | None = Field(default=None)
    has_children: bool | None = Field(default=None)
    children_details: list[str] = Field(default=[], description="e.g., 'has a 3-year-old son'")
    parents_details: list[str] = Field(default=[], description="e.g., 'wife named Maria'")
    relatives_mentioned: list[str] = Field(default=[], description="e.g., 'mom is a good cook'")


class LanguageGoal(BaseModel):
    """User's language learning objectives and challenges."""

    main_goal: str | None = Field(
        default=None, description="Primary goal: professional, exam prep, travel, general."
    )
    specific_exam: str | None = Field(default=None, description="Specific exam like IELTS or OET.")
    desired_skills: list[str] = Field(
        default=[],
        description="Skills to improve: e.g., pronunciation, grammar, vocabulary.",
    )
    challenges: list[str] = Field(
        default=[],
        description="Struggles: e.g., speaking anxiety, finding words, accent issues.",
    )
    learning_style: str | None = Field(
        default=None,
        description=(
            "Preferred way of learning mentioned (e.g., 'by doing', 'structured', 'game-based')."
        ),
    )


class ProfessionalProfile(BaseModel):
    """User's professional information."""

    status: (
        Literal['student', 'employed', 'unemployed', 'business_owner', 'homemaker', 'freelancer']
        | None
    ) = Field(default=None)
    industry: str | None = Field(
        default=None, description="Industry sector (e.g., IT, Healthcare, Marketing)."
    )
    role: str | None = Field(
        default=None, description="Job title (e.g., Software Engineer, Doctor, Pilot)."
    )
    responsibilities: list[str] = Field(default=[], description="Key job duties.")
    work_environment: Literal['office', 'remote', 'hybrid', 'on-site (non-office)'] | None = Field(
        default=None
    )


class PersonalInterests(BaseModel):
    """User's hobbies and personal life details."""

    hobbies: list[str] = Field(default=[], description="Hobbies like sports, music, cooking.")
    discussion_topics: list[str] = Field(default=[], description="Topics user enjoys discussing.")
    travel: list[str] = Field(default=[], description="Travel history or future plans.")


# --- The Final, Unified Top-Level Class ---


class UserProfile(BaseModel):
    """
    A complete, unified profile of a user based on all available dialogue information.
    """

    # --- Basic Info ---
    name: str | None = Field(default=None)
    country_of_origin: str | None = Field(default=None)
    current_location: str | None = Field(default=None)

    # --- Key Profiles ---
    language_goal: LanguageGoal = Field(default=LanguageGoal())
    professional_profile: ProfessionalProfile = Field(default=ProfessionalProfile())
    personal_interests: PersonalInterests = Field(default=PersonalInterests())
    family: FamilyDetails = Field(default=FamilyDetails())

    # --- Other ---
    current_emotional_state: str | None = Field(
        default=None,
        description=(
            "User's emotional state explicitly stated by him (e.g., tired, frustrated, happy)."
        ),
    )
    general_notes: list[str] = Field(
        default=[],
        description=(
            "A place for specific, miscellaneous short facts about the user. "
            "e.g., 'Has a colleague named Ryan', 'Pet dog's name is Coco'."
        ),
    )

    def dump(self, **kwargs: Any) -> dict[str, Any]:
        return self.model_dump(
            exclude_none=True, exclude_defaults=True, exclude_unset=True, **kwargs
        )

    def dump_json(self, **kwargs: Any) -> str:
        return self.model_dump_json(
            exclude_none=True, exclude_defaults=True, exclude_unset=True, **kwargs
        )

    def filter(
        self,
        min_value_length: int | None = None,
        max_value_length: int | None = None,
        k_last_list_elements: int | None = None,
    ) -> UserProfile:
        out = deepcopy(self)
        min_value_length = min_value_length or -1
        max_value_length = max_value_length or 1_000_000

        def _filter_value(value: Any) -> Any:
            if isinstance(value, list):
                value = [v for v in value if min_value_length <= len(str(v)) <= max_value_length]
                if k_last_list_elements:
                    value = value[-k_last_list_elements:]
                return value
            else:
                if min_value_length <= len(str(value)) <= max_value_length:
                    return value
                else:
                    return None

        def _filter(x: T) -> T:
            for field in x.model_fields:
                value = getattr(x, field)
                if isinstance(value, BaseModel):
                    setattr(x, field, _filter(value))
                else:
                    setattr(x, field, _filter_value(value))
            return x

        return _filter(out)

    def flatten_format(self) -> dict[str, str]:
        def _format(key: str) -> str:
            return " ".join([word.capitalize() for word in key.split("_")])

        def _flatten(element: BaseModel) -> dict[str, str]:
            out = {}
            for field in element.model_fields:
                value = getattr(element, field)
                if not value:
                    continue
                if isinstance(value, BaseModel):
                    out.update(_flatten(value))
                    continue
                if isinstance(value, list):
                    if value:
                        value = random.choice(value)
                        out[_format(field)] = str(value)
                    else:
                        continue
                else:
                    # default case: int, str, float, ...
                    if value:
                        out[_format(field)] = str(value)
                    else:
                        continue
            return out

        return _flatten(self)

    def update_w_repair_and_calc_diff(self: T, update: T) -> T:
        def compare_pydantic_schemas_to_update_and_diff(old: T, new: T) -> tuple[T, T]:
            updated = deepcopy(old)
            diff = type(new).model_validate({}, strict=False)
            for key in new.model_fields:
                old_value, new_value = (
                    getattr(old, key, None),
                    getattr(new, key, None),
                )
                if new_value is None:
                    continue
                if isinstance(new_value, list) and len(new_value) == 0:
                    setattr(updated, key, old_value or [])
                    continue
                if isinstance(old_value, BaseModel) and isinstance(new_value, BaseModel):
                    _updated, _diff = compare_pydantic_schemas_to_update_and_diff(
                        cast(T, old_value), cast(T, new_value)
                    )
                    setattr(updated, key, _updated)
                    setattr(diff, key, _diff)
                    continue
                if isinstance(old_value, list) and isinstance(new_value, list):
                    new_value_unique = list(set(new_value))  # we don't care about order here
                    old_value_unique = [
                        ov for ov in old_value if (ov not in new_value)
                    ]  # same order
                    _updated = old_value_unique + new_value_unique  # type: ignore
                    _diff = list(set(new_value) - set(old_value))  # type: ignore
                    setattr(updated, key, _updated)
                    setattr(diff, key, _diff)
                    continue
                # default: str, int, float, bool, ...
                setattr(updated, key, new_value)
                setattr(diff, key, new_value if (new_value != old_value) else None)
            return updated, diff

        _, diff = compare_pydantic_schemas_to_update_and_diff(self, update)
        return diff

    def is_empty(self) -> bool:
        return len(self.dump()) == 0


# async def _update_memory_task_and_send_fact_extract():
#     utterances = self.get_utterances_w_timestamps()
#     n_user_utterances = len([u for u in utterances if u["role"] == "user"])
#     if (
#         (os.environ['ENV'] in ['production', 'staging'])
#         and (n_user_utterances % 10 != 0)
#         and (n_user_utterances > 0)
#     ):
#         return
#     if n_user_utterances in self.memory.n_user_utterances_updates:
#         logger.debug(
#             "skipping `update_memory`"
#             " | we already updated memory for this number of user utterances"
#         )
#         return
#     self.memory.n_user_utterances_updates.add(n_user_utterances)
#     diff = await self.memory.update_memory(
#         conversation=self.memory.prepare_utterances(utterances[-10:]),
#         context=self.memory.prepare_utterances(utterances[-(10 + 40) : -10]),
#     )
#     if (not diff) or diff.is_empty():
#         return
#     factdict = diff.flatten_format()
#     if not factdict:
#         return
#     factname, factvalue = random.choice(list(factdict.items()))
#     await self.make_rpc_call(
#         "memory_fact_extract",
#         f"{factname} → {factvalue}",
#         max_attempts=3,
#         delay=1,
#     )


MEMORY_INIT_TEMPLATE = """
Extract the information into `UserProfile` from the following conversation, if any is present:

<convo>
{conversation}
</convo>

# How to do it:
- ✅ Write facts as concise as possible, no more than 10 words each
- ✅ If you see a similar fact that is already in the memory, don't duplicate it
- ✅ If you unsure about the fact reasoning or semantics, don't add it
- ✅ Each fact must be self-contained and independent, \
without placeholders or references to external entities
- ✅ Don't duplicate facts belonging to different categories and fields
- ✅ If field is list-type, then only add substanstialy new items if present in the convo, \
don't rewrite the whole list
- ✅ If field is value-type, then only update it if present in the convo, \
don't rewrite the whole field for no reason
""".strip()

MEMORY_UPDATE_TEMPLATE = """
Update the `UserProfile` memory (JSON doc) based only on\
 new information from the conversation below.
Use context for reference, but extract updates only from new turns from convo.
You goal is to update `current_profile` with substantially new information, \
so be accurate in your reasoning.

<current_profile>
{current_profile}
</current_profile>

<context>
{context}
</context>

<convo>
{conversation}
</convo>

# How to do it:
- ✅ Write facts as concise as possible, no more than 10 words each
- ✅ If you see a similar fact that is already in the `current_profile`, don't duplicate it
- ✅ If you unsure about the fact reasoning or semantics, don't add it
- ✅ Each fact must be self-contained and independent, \
without placeholders or references to external entities
- ✅ Don't duplicate facts belonging to different categories and fields
- ✅ If field is list-type, then only add substanstialy new items if present in the convo, \
don't rewrite the whole list
- ✅ If field is value-type, then only update it if present in the convo, \
don't rewrite the whole field for no reason
""".strip()


conversation1 = """
Tutor: Hi there! To start, could you tell me a little about yourself?
User: Hi, I'm Alex. I'm originally from Spain.
Tutor: Welcome, Alex! What do you do for work?
User: I'm a software engineer. My main responsibility is developing new features for our app.
Tutor: That sounds interesting. What brings you here? What are your language learning goals?
User: I want to improve my professional communication. I find I learn best by doing.
Tutor: What do you enjoy talking about outside of work?
User: I love playing the guitar. I also enjoy travelling.
Tutor: It helps me to know a bit about your personal life to tailor our conversations.
User: Sure. I'm married. We have a 3-year-old son.
Tutor: How are you feeling today?
User: A bit tired, to be honest.
""".strip()

conversation1_update = """
Tutor: That's a fun detail about Ryan and Coco! It's the small, random things
 that make conversations interesting. You also mentioned you were feeling tired.
 I hope you got some rest over the weekend?
User: Idid, thank you. We celebrated my wife Maria's promotion at her graphic design firm,
 which was lovely. Speaking of work, my own week is going to be intense.
 I'm now leading a new project to integrate AI into our app, and I have to give the main
 presentation in two weeks. This is why I really need to work on my speaking confidence.
 Also, I've been trying to eat healthier, so I've started cooking more. I made a pretty
 decent paella, which reminds me of my family in Spain. My father taught me the basics.
 And about my son, his name is Leo. He's three and obsessed with LEGOs. Oh, and one more
 thing - I'm thinking of getting a cat, but Maria is allergic, so we are considering a
 hypoallergenic breed like a Siberian.
Tutor: A hypoallergenic cat sounds like a clever solution! The Siberian breed is beautiful.
 It's a classic dilemma. Shifting back to your work, you mentioned the big presentation
 about AI. What's the most challenging part about it for you?
User: The biggest challenge is structuring the talk to be clear for a non-technical audience,
 like our marketing team. That's where my anxiety about finding the right words really
 kicks in. My company is offering to sponsor professional development courses, and I was
 thinking about a public speaking workshop.
Tutor: That's a fantastic idea. We can practice structuring that very presentation right here.
 Let's make that a concrete goal. You also mentioned you started cooking. What other
 dishes do you enjoy making?
User: I'm trying to learn more Italian dishes, mainly pasta. My wife Maria is half-Italian,
 so it's a way to connect with her heritage. I'm not very good yet, but it's fun.
 I also recently picked up cycling on the weekends as a way to clear my head.
""".strip()

conversation2 = """
Tutor: Hi there, welcome! Can you tell me your name and why you're learning English?
User: Hello, I'm Priya. I'm from India.
 I need to take the IELTS exam soon for university applications.
Tutor: That's a great goal, Priya. Which part of the exam are you most worried about?
User: Definitely the writing and speaking parts. I need to be more formal and academic.
Tutor: We can certainly work on that. What are you planning to study?
User: I want to do my Master's in Computer Science.
Tutor: Excellent. And what do you do for fun, when you're not studying?
User: I don't have much free time, but I enjoy watching movies.
 My family is very supportive of my studies.
Tutor: It's wonderful to have a supportive family.
 How are you feeling about our session today?
User: I'm a little nervous, but excited to start.
""".strip()

conversation2_update = """
Tutor: Last time you mentioned you were nervous.
 I hope you're feeling more comfortable now. Any news on the university applications?
User: Yes, great news! I got accepted into the University of Toronto!
 So my goal is shifting a bit. I still need good English, but now it’s less about
 the exam and more about daily life in Canada.
Tutor: Congratulations, that's fantastic! That's a big change.
 So, we should focus on conversational skills?
User: Exactly! Like, how to talk to professors, or what to say at a coffee shop.
 I'm also worried about understanding different accents. My brother lives in Vancouver
 and he said it was tricky at first.
Tutor: That's a very practical goal. We can practice lots of real-life scenarios.
 It's great you have a brother there, that will make settling in easier.
User: Yes, his name is Rohan. He's been a great help. On another note, I've picked up
 a new hobby to relax a bit before the big move - photography. I just bought a used
 camera and I'm trying to capture street life in my city. It helps me see things differently.
Tutor: Photography is a wonderful hobby! It's a great way to document your journey.
 Maybe you can even start a photo blog about your new life in Canada.
User: I love that idea! It would be a great way to practice writing in a more creative way.
 Thanks for the suggestion!
""".strip()

conversation3 = """
Tutor: Good morning! Please, tell me a bit about yourself to start.
User: Good morning. My name is Kenji, and I'm from Japan.
Tutor: Welcome, Kenji. What is your profession?
User: I am a business owner. I have a small brewery that makes craft sake.
Tutor: That's very unique! Why are you focusing on English now?
User: I want to expand my business to the United States.
 I need to be better at negotiations and marketing presentations.
Tutor: A very clear and important goal.
 How do you find the time to study with your own business?
User: It is difficult. I work long hours.
 So I need our lessons to be very focused and efficient.
Tutor: Understood. Outside of your work, what are your interests?
User: To be honest, I don't have much time for interests. My work is my life right now.
""".strip()

conversation3_update = """
Tutor: Last time, you mentioned how demanding your work is. I was wondering if you'd had
 any interesting developments with your US expansion plan?
User: Yes, I just came back from a trip to California.
 I met with some potential distributors. It was challenging.
 The way they do business is very direct, very different from Japan.
Tutor: That's a very common experience.
 Cultural differences in communication can be a big hurdle.
 What was the biggest challenge for you?
User: They use a lot of slang and idioms I didn't understand.
 And they expect you to be very assertive.
 I need to learn to be more confident in that environment.
Tutor: We can definitely role-play those kinds of negotiations.
 On a more personal note, did you get any time to relax on your trip?
User: A little. My wife, Yumi, insisted I take a weekend off. We went hiking in Yosemite.
 It was beautiful and cleared my head. It made me realize I need better work-life balance.
Tutor: I'm glad to hear that. It's important to recharge. Is your wife also learning English?
User: Yes, she and my daughter, Hana, are both taking lessons.
 Hana is 10 and she is learning much faster than me!
 We want to be prepared if we decide to move for a few years for the business.
""".strip()

conversation4 = """
Tutor: Hello, it's a pleasure to meet you. Could you introduce yourself?
User: Hello. I am Sophie, from France. I am retired.
Tutor: Welcome, Sophie. What are your reasons for learning English?
User: I am learning for travel. I want to visit my grandchildren in Australia.
Tutor: How wonderful! How old are your grandchildren?
User: I have a grandson, Leo, who is 8, and a granddaughter, Chloe, who is 5.
Tutor: They must be very excited for you to visit. What do you enjoy doing in your retirement?
User: I love gardening. I have a small vegetable garden. I also enjoy reading novels.
Tutor: That sounds very peaceful. Are you excited about your trip?
User: Yes, but also a bit apprehensive. It's a very long flight.
""".strip()

conversation4_update = """
Tutor: Last time, you mentioned you were feeling a bit apprehensive about the long flight
 to Australia. How are the travel plans coming along?
User: Ah, well, the plans have changed! My daughter's family is now moving to New Zealand
 instead. Her husband got a new job in Wellington. So, I will be going there instead.
Tutor: New Zealand is beautiful! A wonderful surprise.
 Does this change what you'd like to focus on with your English?
User: Not really, the goal is the same: to speak with my family.
 But I have been thinking a lot about my late husband, Pierre.
 He was a history professor and we always dreamed of visiting New Zealand together.
 He would have loved the landscapes.
Tutor: I'm sorry for your loss, Sophie. It sounds like this trip will be very meaningful
 for you, carrying on that shared dream.
User: Thank you. It is bittersweet. To keep my mind busy and practice my English,
 I have joined an online book club. We are reading a book by a New Zealand author,
 which is a nice coincidence.
Tutor: That's a fantastic idea! A book club is a perfect way to practice comprehension
 and conversation. What is the name of the book?
User: It is called "The Luminaries". It is very long and the vocabulary is quite
 advanced for me, so it's a real challenge, but an interesting one.
 It makes me feel productive.
""".strip()

# TODO delete
# if utils.is_given(with_memory) and with_memory and (not self.memory.is_empty()):
#     out.append(
#         f"You are free to extensively use this User Profile information in your replies "
#         f"that extracted from previous conversations and previous messages:\n "
#         f"```\n{self.memory.sysprompt}\n```\n"
#         "You can both mention it and appeal to it in your replies, "
#         "use it to make tutoring more shaped and personalized, "
#         "make new topics more relevant to the user "
#         "(for example, not repeating discussed topics or expanding deeper on them), "
#         "show you are a real person who knows the user and their interests."
#     )


# TODO delete
# memory = UpdatableMemoryJSON(
#     user_id=str(metadata.user_id),
#     s3_client=AsyncS3(
#         access_key_id=os.environ["S3_ACCESS_KEY_ID"],
#         secret_access_key=os.environ["S3_SECRET_ACCESS_KEY"],
#         region_name=os.environ["S3_REGION"],
#         bucket_name=os.environ["S3_BUCKET"],
#     ),
#     llmapi=llmapi,
#     n_retries=3,
# )
# if expconfig.exp_memory_json2 is True:
#     memory.load_memory_task()


# class UpdatableMemoryJSON:
#     EXCLUDE_ARGS = {
#         "exclude_none": True,
#         "exclude_defaults": True,
#         "exclude_unset": True,
#     }

#     def __init__(
#         self,
#         user_id: str,
#         s3_client: AsyncS3,
#         llmapi: LLMAPI,
#         n_retries: int = 3,
#     ):
#         self.user_id = user_id
#         self.s3_client = s3_client
#         self.llmapi = llmapi
#         self._memory: UserProfile | None = None
#         self.n_retries = n_retries
#         self.n_user_utterances_updates: set[int] = set()

#     def is_empty(self) -> bool:
#         return (self._memory is None) or self._memory.is_empty()

#     @property
#     def sysprompt(self) -> str:
#         if self.is_empty():
#             logger.warning("`memory` is empty, no point in using it in system prompt")
#             return "{}"
#         assert self._memory is not None
#         return self._memory.dump_json(indent=2)

#     def load_memory_task(self) -> asyncio.Task:
#         if not hasattr(self, "_load_memory_task"):
#             self._load_memory_task = asyncio.create_task(self.load_memory())
#         return self._load_memory_task

#     def save_memory_task(self) -> asyncio.Task:
#         if not hasattr(self, "_save_memory_task"):
#             self._save_memory_task = asyncio.create_task(self.save_memory())
#         return self._save_memory_task

#     async def load_memory(self):
#         _memory = await self.s3_client.load_file(f"memory/{self.user_id}.json")
#         if not _memory:
#             self._memory = None
#             return
#         try:
#             self._memory = UserProfile.model_validate(_memory).filter(
#                 min_value_length=1,
#                 max_value_length=100,
#                 k_last_list_elements=5,
#             )
#         except Exception as e:
#             logger.warning(f"❌ VALIDATION `load_memory` | {e}")
#             self._memory = None
#         else:
#             logger.info(f"✅ DONE `load_memory` | memory={self._memory.dump()}")

#     async def save_memory(self):
#         if self.is_empty():
#             return
#         self._memory = self._memory.filter(
#             min_value_length=1,
#             max_value_length=100,
#             k_last_list_elements=5,
#         )
#         await self.s3_client.save_file(f"memory/{self.user_id}.json", self._memory.dump())
#         logger.info(f"✅ DONE `save_memory` | memory={self._memory.dump()}")

#     async def update_memory(self, conversation: str, context: str = "") -> UserProfile | None:
#         logger.debug("🕒 starting `update_memory` in `UpdatableMemoryJSON`")
#         try:
#             if self._memory is not None:
#                 update_response = await self.llmapi.langchain.openai.acall(
#                     chat_ctx=MEMORY_UPDATE_TEMPLATE.format(
#                         context=context,
#                         conversation=conversation,
#                         current_profile=self._memory.dump_json(indent=2),
#                     ),
#                     model="gpt-4.1",
#                     structured_output=UserProfile,
#                     n_retries=self.n_retries,
#                 )
#                 update = cast(UserProfile, update_response.payload)
#                 diff = self._memory.update_w_repair_and_calc_diff(update=update)
#                 diff = diff.filter(
#                     min_value_length=1,
#                     max_value_length=100,
#                     k_last_list_elements=5,
#                 )
#                 self._memory = self._memory.filter(
#                     min_value_length=1,
#                     max_value_length=100,
#                     k_last_list_elements=5,
#                 )
#                 logger.debug(f"🟢 DONE `update_memory` | diff={diff.dump()}")
#                 return diff
#             else:
#                 _memory = await self.llmapi.langchain.openai.acall(
#                     chat_ctx=MEMORY_INIT_TEMPLATE.format(conversation=conversation),
#                     model="gpt-4.1",
#                     structured_output=UserProfile,
#                     n_retries=self.n_retries,
#                 )
#                 self._memory = cast(UserProfile, _memory).filter(
#                     min_value_length=1,
#                     max_value_length=100,
#                     k_last_list_elements=5,
#                 )
#                 logger.debug("🟢 DONE `update_memory` (init)")
#                 return None
#         except Exception as e:
#             import traceback

#             traceback.print_exc()
#             logger.warning(f"❌ FAILED `update_memory` | {e}")
#             return None

#     def update_memory_task(self, conversation: str, context: str = "") -> asyncio.Task:
#         self._update_memory_task = asyncio.create_task(self.update_memory(conversation, context))
#         return self._update_memory_task

#     @staticmethod
#     def prepare_chat_ctx(chat_ctx: lka_llm.ChatContext) -> str:
#         out = []
#         for message in chat_ctx.items:
#             if isinstance(message, lka_llm.ChatMessage):
#                 if message.role == "user":
#                     out.append(f"User: {message.text_content}")
#                 elif message.role == "assistant":
#                     out.append(f"Tutor: {message.text_content}")
#         return "\n".join(out).strip()

#     @staticmethod
#     def prepare_utterances(utterances: list[dict[str, Any]]) -> str:
#         out = []
#         for utterance in utterances:
#             if utterance["role"] == "user":
#                 out.append(f"User: {utterance['text']}")
#             elif utterance["role"] == "assistant":
#                 out.append(f"Tutor: {utterance['text']}")
#         return "\n".join(out).strip()


class UpdatableMemoryJSON:
    EXCLUDE_ARGS = {
        "exclude_none": True,
        "exclude_defaults": True,
        "exclude_unset": True,
    }

    def __init__(
        self,
        user_id: str,
        s3_client: AsyncS3,
        llmapi: LLMAPI,
        n_retries: int = 3,
    ):
        self.user_id = user_id
        self.s3_client = s3_client
        self.llmapi = llmapi
        self._memory: UserProfile | None = None
        self.n_retries = n_retries
        self.n_user_utterances_updates: set[int] = set()

    def is_empty(self) -> bool:
        return (self._memory is None) or self._memory.is_empty()

    @property
    def sysprompt(self) -> str:
        if self.is_empty():
            logger.warning("`memory` is empty, no point in using it in system prompt")
            return "{}"
        assert self._memory is not None
        return self._memory.dump_json(indent=2)

    def load_memory_task(self) -> asyncio.Task:
        if not hasattr(self, "_load_memory_task"):
            self._load_memory_task = asyncio.create_task(self.load_memory())
        return self._load_memory_task

    def save_memory_task(self) -> asyncio.Task:
        if not hasattr(self, "_save_memory_task"):
            self._save_memory_task = asyncio.create_task(self.save_memory())
        return self._save_memory_task

    async def load_memory(self):
        _memory = await self.s3_client.load_file(f"memory/{self.user_id}.json")
        if not _memory:
            self._memory = None
            return
        try:
            self._memory = UserProfile.model_validate(_memory).filter(
                min_value_length=1,
                max_value_length=100,
                k_last_list_elements=5,
            )
        except Exception as e:
            logger.warning(f"❌ VALIDATION `load_memory` | {e}")
            self._memory = None
        else:
            logger.info(f"✅ DONE `load_memory` | memory={self._memory.dump()}")

    async def save_memory(self):
        if self.is_empty():
            return
        assert self._memory is not None
        self._memory = self._memory.filter(
            min_value_length=1,
            max_value_length=100,
            k_last_list_elements=5,
        )
        await self.s3_client.save_file(f"memory/{self.user_id}.json", self._memory.dump())
        logger.info(f"✅ DONE `save_memory` | memory={self._memory.dump()}")

    async def update_memory(self, conversation: str, context: str = "") -> UserProfile | None:
        logger.debug("🕒 starting `update_memory` in `UpdatableMemoryJSON`")
        try:
            if self._memory is not None:
                # TODO delete
                # update = await (
                #     self.llmapi.langchain.openai.with_structured_output(UserProfile)
                #     .with_retry(stop_after_attempt=self.n_retries)
                #     .ainvoke(
                #         [
                #             HumanMessage(
                #                 content=MEMORY_UPDATE_TEMPLATE.format(
                #                     context=context,
                #                     conversation=conversation,
                #                     current_profile=self._memory.dump_json(indent=2),
                #                 )
                #             ),
                #         ]
                #     )
                # )
                update_response = await self.llmapi.langchain.openai.acall(
                    chat_ctx=MEMORY_UPDATE_TEMPLATE.format(
                        context=context,
                        conversation=conversation,
                        current_profile=self._memory.dump_json(indent=2),
                    ),
                    model="gpt-4.1",
                    structured_output=UserProfile,
                    n_retries=self.n_retries,
                )
                update = cast(UserProfile, update_response.payload)
                diff = self._memory.update_w_repair_and_calc_diff(update=update)
                diff = diff.filter(
                    min_value_length=1,
                    max_value_length=100,
                    k_last_list_elements=5,
                )
                self._memory = self._memory.filter(
                    min_value_length=1,
                    max_value_length=100,
                    k_last_list_elements=5,
                )
                logger.debug(f"🟢 DONE `update_memory` | diff={diff.dump()}")
                return diff
            else:
                # TODO delete
                # _memory = await (
                #     self.llmapi.langchain.openai.with_structured_output(UserProfile)
                #     .with_retry(stop_after_attempt=self.n_retries)
                #     .ainvoke(
                #         [
                #             HumanMessage(
                #                 content=MEMORY_INIT_TEMPLATE.format(conversation=conversation)
                #             )
                #         ]
                #     )
                # )
                _memory = await self.llmapi.langchain.openai.acall(
                    chat_ctx=MEMORY_INIT_TEMPLATE.format(conversation=conversation),
                    model="gpt-4.1",
                    structured_output=UserProfile,
                    n_retries=self.n_retries,
                )
                self._memory = cast(UserProfile, _memory).filter(
                    min_value_length=1,
                    max_value_length=100,
                    k_last_list_elements=5,
                )
                logger.debug("🟢 DONE `update_memory` (init)")
                return None
        except Exception as e:
            import traceback

            traceback.print_exc()
            logger.warning(f"❌ FAILED `update_memory` | {e}")
            return None

    def update_memory_task(self, conversation: str, context: str = "") -> asyncio.Task:
        self._update_memory_task = asyncio.create_task(self.update_memory(conversation, context))
        return self._update_memory_task

    @staticmethod
    def prepare_chat_ctx(chat_ctx: lka_llm.ChatContext) -> str:
        out = []
        for message in chat_ctx.items:
            if isinstance(message, lka_llm.ChatMessage):
                if message.role == "user":
                    out.append(f"User: {message.text_content}")
                elif message.role == "assistant":
                    out.append(f"Tutor: {message.text_content}")
        return "\n".join(out).strip()

    @staticmethod
    def prepare_utterances(utterances: list[dict[str, Any]]) -> str:
        out = []
        for utterance in utterances:
            if utterance["role"] == "user":
                out.append(f"User: {utterance['text']}")
            elif utterance["role"] == "assistant":
                out.append(f"Tutor: {utterance['text']}")
        return "\n".join(out).strip()


if __name__ == "__main__":
    # asyncio.run(main())
    # exit(0)

    from dotenv import load_dotenv
    from langchain_openai import ChatOpenAI
    # from trustcall import create_extractor  # Noqa

    load_dotenv(override=True)

    llm = ChatOpenAI(
        model_name="gpt-4o",
        openai_api_key=SecretStr(api_key) if (api_key := os.getenv("OPENAI_API_KEY")) else None,
        temperature=0,
    )
    # trustllm = create_extractor(
    #     llm,
    #     tools=[UserProfile],
    #     tool_choice="UserProfile",
    #     enable_deletes=True,
    #     enable_updates=True,
    #     enable_inserts=True,
    # )

    # def naive_extractor(
    #     conversation: str, previous_profile: UserProfile | None = None
    # ) -> UserProfile:
    #     if previous_profile:
    #         return llm.with_structured_output(UserProfile).invoke(
    #             [
    #                 HumanMessage(content=json.dumps(previous_profile.model_dump())),
    #                 HumanMessage(content=TASK_UPDATE_TEMPLATE.format(conversation=conversation)),
    #             ]
    #         )
    #     else:
    #         return llm.with_structured_output(UserProfile).invoke(
    #             TASK_INIT_TEMPLATE.format(conversation=conversation)
    #         )

    # def trust_extractor(
    #     conversation: str, previous_profile: UserProfile | None = None
    # ) -> UserProfile:
    #     if previous_profile:
    #         return trustllm.invoke(
    #             {
    #                 "messages": [
    #                     {
    #                         "role": "user",
    #                         "content": TASK_UPDATE_TEMPLATE.format(conversation=conversation),
    #                     },
    #                 ],
    #                 "existing": {"UserProfile": previous_profile.model_dump()},
    #             }
    #         )["responses"][0]
    #     else:
    #         return trustllm.invoke(TASK_INIT_TEMPLATE.format(conversation=conversation))[
    #             "responses"
    #         ][0]

    def naive_extractor_2(
        conversation: str, context: str | None = None, previous_profile: UserProfile | None = None
    ) -> UserProfile:
        if previous_profile:
            return cast(
                UserProfile,
                llm.with_structured_output(UserProfile).invoke(
                    [
                        HumanMessage(
                            content=MEMORY_UPDATE_TEMPLATE.format(
                                conversation=conversation,
                                context=context,
                                previous_profile=json.dumps(previous_profile.model_dump()),
                            )
                        ),
                    ]
                ),
            )
        else:
            return cast(
                UserProfile,
                llm.with_structured_output(UserProfile).invoke(
                    [
                        HumanMessage(
                            content=MEMORY_INIT_TEMPLATE.format(
                                conversation=conversation,
                            )
                        ),
                    ]
                ),
            )

    def _update(profile: BaseModel, update: BaseModel) -> BaseModel:
        # Create a deep copy to avoid modifying the original object in-place.
        # This makes the function pure and the logic in `run_test` clearer.

        output = deepcopy(profile)

        for key in update.model_fields:
            old_value = getattr(profile, key, None)
            new_value = getattr(update, key, None)

            # Rule: If new value is None, keep the old value.
            if new_value is None:
                continue

            # Rule: If new value is an empty list => LLM found no new items. Keep the old list.
            if isinstance(new_value, list) and len(new_value) == 0:
                setattr(output, key, [])
                continue

            # Rule: Recursive update for nested Pydantic models
            if isinstance(old_value, BaseModel) and isinstance(new_value, BaseModel):
                setattr(output, key, _update(old_value, new_value))
                continue

            # Rule: Concatenate and deduplicate lists
            if isinstance(old_value, list) and isinstance(new_value, list):
                setattr(output, key, list(set(old_value + new_value)))
                continue

            # Default case: new value overwrites the old one for simple types (str, bool, int)
            # or when the old value was None.
            setattr(output, key, new_value)

        return output

    def run_test(conversation: str, conversation_update: str):
        # profile_naive = naive_extractor(conversation)
        # profile_trust = trust_extractor(conversation)
        profile_naive_2 = naive_extractor_2(conversation)
        # profile_naive_3 = naive_extractor_3(conversation)
        # print("=== I profile_naive ===")
        # print(profile_naive)
        # print("=== I profile_trust ===")
        # print(profile_trust)
        print("=== I profile_naive_2 ===")
        print(profile_naive_2)
        print("=== I profile_naive_2 enchanced ===")
        print(profile_naive_2)
        # profile_naive_update = naive_extractor(conversation_update, profile_naive)
        # profile_trust_update = trust_extractor(conversation_update, profile_trust)
        profile_naive_2_update = naive_extractor_2(
            conversation_update, context=conversation, previous_profile=profile_naive_2
        )
        # profile_naive_3_update = naive_extractor_3(
        #     conversation_update, context=conversation, previous_profile=profile_naive_3
        # )
        profile_naive_2_update_enhanced = _update(profile_naive_2, profile_naive_2_update)
        # print("=== II profile_naive_update ===")
        # print(profile_naive_update)
        # print("=== II profile_trust_update ===")
        # print(profile_trust_update)
        print("=== II profile_naive_2_update ===")
        print(profile_naive_2_update)
        # print("=== II profile_naive_3_update ===")
        # print(profile_naive_3_update)
        print("=== II profile_naive_2_update_enhanced ===")
        print(profile_naive_2_update_enhanced)

    run_test(conversation1, conversation1_update)
    print("\n\n\n")
    run_test(conversation2, conversation2_update)
    print("\n\n\n")
    run_test(conversation3, conversation3_update)
    print("\n\n\n")
    run_test(conversation4, conversation4_update)
