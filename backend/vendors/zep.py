import asyncio
import datetime as dt
import logging
from typing import Literal

from zep_cloud.client import AsyncZep
from zep_cloud.types import EntityEdge, EntityNode, Message

CONTEXT_STRING_TEMPLATE = """
FACTS and ENTITIES represent relevant context to the current conversation.
# These are the most relevant facts and their valid date ranges
# format: FACT (Date range: from - to)
<FACTS>
{facts}
</FACTS>

# These are the most relevant entities
# ENTITY_NAME: entity summary
<ENTITIES>
{entities}
</ENTITIES>
"""

logger = logging.getLogger(__name__)


def compose_context_block(nodes: list[EntityNode], edges: list[EntityEdge]) -> str:
    def format_fact(edge: EntityEdge) -> str:
        valid_at = edge.valid_at if edge.valid_at is not None else "date unknown"
        invalid_at = edge.invalid_at if edge.invalid_at is not None else "present"
        formatted_fact = f"  - {edge.fact} (Date range: {valid_at} - {invalid_at})"
        return formatted_fact

    def format_entity(node: EntityNode) -> str:
        formatted_entity = f"  - {node.name}: {node.summary}"
        return formatted_entity

    facts = [format_fact(edge) for edge in edges]
    entities = [format_entity(node) for node in nodes]
    return CONTEXT_STRING_TEMPLATE.format(facts='\n'.join(facts), entities='\n'.join(entities))


class ZepMemory:
    def __init__(self, user_id: str, thread_id: str, first_name: str | None, api_key: str) -> None:
        self._client = AsyncZep(api_key=api_key)
        self._user_id = user_id
        self._thread_id = thread_id
        self._first_name = first_name

    async def init(self) -> None:
        try:
            await self._client.user.add(user_id=self._user_id, first_name=self._first_name)
        except Exception:
            pass  # already exists
        try:
            await self._client.thread.create(thread_id=self._thread_id, user_id=self._user_id)
        except Exception:
            pass  # already exists

    async def add_message(
        self,
        role: Literal['user', 'assistant'],
        content: str,
        name: str | None,
        created_at: dt.datetime | None,
    ) -> None:
        message = Message(
            role=role,
            content=content,
            name=name,
            created_at=created_at.isoformat() if created_at else None,
        )
        await self._client.thread.add_messages(thread_id=self._thread_id, messages=[message])

    async def retrieve_context(self) -> str | None:
        memory = await self._client.thread.get_user_context(thread_id=self._thread_id)
        return memory.context

    async def construct_system_prompt(self, prompt: str) -> str | None:
        # 1. init user and thread
        await self.init()
        # # 2. add system message for query context
        # await self._client.thread.add_messages(
        #     thread_id=self._thread_id,
        #     messages=[
        #         Message(
        #             role='system',
        #             content=prompt,
        #             created_at=dt.datetime.now(dt.timezone.utc).isoformat(),
        #         )
        #     ],
        # )
        # # 3. retrieve context
        # context = await self.retrieve_context()
        result_nodes, result_edges = await asyncio.gather(
            self._client.graph.search(
                query=prompt[:400],
                user_id=self._user_id,
                scope='nodes',
                reranker='cross_encoder',
                limit=10,
            ),
            self._client.graph.search(
                query=prompt[:400],
                user_id=self._user_id,
                scope='edges',
                reranker='cross_encoder',
                limit=10,
            ),
        )
        nodes, edges = result_nodes.nodes or [], result_edges.edges or []
        if not (nodes or edges):
            return None
        context = compose_context_block(nodes, edges)
        return f'Here is the relevant context to the current conversation:\n{context}'
