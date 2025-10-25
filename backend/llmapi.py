import abc
import asyncio
import copy
import json
import logging
import random
import re
import time
import traceback
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal, cast

import aiohttp
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolCall,
    ToolMessage,
)
from langchain_core.runnables import ConfigurableField, RunnableLambda
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from livekit.agents import NOT_GIVEN, NotGivenOr, utils
from livekit.agents import llm as lka_llm
from livekit.agents.llm.tool_context import (
    get_function_info,
    get_raw_function_info,
    is_function_tool,
    is_raw_function_tool,
)
from pydantic import BaseModel

logger = logging.getLogger(__name__)


@dataclass
class APIResponseToolCall:
    name: str
    args: dict[str, Any] | str
    id: str

    @property
    def args_as_str(self) -> str:
        if isinstance(self.args, str):
            return self.args
        return json.dumps(self.args)

    @property
    def args_as_dict(self) -> dict[str, Any]:
        if isinstance(self.args, str):
            return json.loads(self.args)
        return self.args


class SessionIsClosedError(BaseException):
    pass


@dataclass
class APIResponse:
    payload: str | APIResponseToolCall | BaseModel
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    usage: dict = field(default_factory=dict)
    attempt: int = field(default=1)
    model: str = field(default="unknown")
    provider_time: float = field(default=0.0)

    @property
    def type(self) -> Literal["text", "tool_call", "structured", "unknown", "error"]:
        if self.model == 'error':
            return "error"
        if isinstance(self.payload, APIResponseToolCall):
            return "tool_call"
        if isinstance(self.payload, BaseModel):
            return "structured"
        if isinstance(self.payload, str):
            return "text"

        return "unknown"

    @classmethod
    def fallback(
        cls,
        value: str
        | Literal['say_sorry_repeat', 'goodbye_end_session']
        | BaseModel
        | "APIResponse",
    ) -> 'APIResponse':
        if isinstance(value, APIResponse):
            return value
        if isinstance(value, BaseModel):
            return cls(payload=value, model='error')
        if value == 'say_sorry_repeat':
            content = random.choice(
                [
                    "I'm sorry, i didn't quite catch that. Can you please repeat?",
                    "Could you say that again? I didn't understand you clearly.",
                    "I'm having trouble understanding. Can you rephrase that for me?",
                ]
            )
        if value == 'goodbye_end_session':
            content = random.choice(
                [
                    "Have a nice day!",
                    "Thank you for your time. Goodbye!",
                    "Goodbye. It was nice talking to you.",
                ]
            )
        return cls(payload=content, model='error')

    def as_chatchunk(self) -> lka_llm.ChatChunk:
        if self.type == "tool_call":
            assert isinstance(self.payload, APIResponseToolCall), (
                "payload must be a APIResponseToolCall if type is tool_call"
            )
            return lka_llm.ChatChunk(
                id=self.id,
                delta=lka_llm.ChoiceDelta(
                    role="assistant",
                    content=None,
                    tool_calls=[
                        lka_llm.FunctionToolCall(
                            type="function",
                            name=self.payload.name,
                            arguments=self.payload.args_as_str,
                            call_id=self.payload.id,
                        )
                    ],
                ),
                usage=None,
            )
        else:
            assert isinstance(self.payload, str), (
                f"payload must be a string if no tool call, payload={self.payload}"
            )
            return lka_llm.ChatChunk(
                id=self.id,
                delta=lka_llm.ChoiceDelta(
                    role="assistant",
                    content=self.payload,
                    tool_calls=[],
                ),
            )


class RetryAttemptTracker(BaseCallbackHandler):
    def __init__(self):
        self.attempt = 1
        self.retry_pattern = re.compile(r'retry:attempt:(\d+)')

    def on_chain_start(self, serialized, inputs, **kwargs):
        # Ищем тег в retry:attempt:N в kwargs
        tags = kwargs.get('tags', [])
        for tag in tags or []:
            match = self.retry_pattern.search(tag)
            if match:
                self.attempt = int(match.group(1))
                break


def _get_tool_info(t: lka_llm.FunctionTool | lka_llm.RawFunctionTool):
    if is_raw_function_tool(t):
        return get_raw_function_info(t)
    elif is_function_tool(t):
        return get_function_info(t)
    else:
        raise ValueError(f"unknown tool type: {type(t)}")


def _to_raw_schema(tool: lka_llm.FunctionTool | lka_llm.RawFunctionTool) -> dict[str, Any]:
    if is_raw_function_tool(tool):
        return {
            "type": "function",
            "function": get_raw_function_info(tool).raw_schema,
        }
    elif is_function_tool(tool):
        return lka_llm.utils.build_strict_openai_schema(tool)
    else:
        raise ValueError(f"unknown tool type: {type(tool)}")


class BaseProvider(abc.ABC):
    def __init__(self):
        self.init_params()

    def init_params(self) -> None:
        self.model: NotGivenOr[str] = NOT_GIVEN
        self.temperature: NotGivenOr[float] = NOT_GIVEN
        self.max_tokens: NotGivenOr[int] = NOT_GIVEN
        self.tools: NotGivenOr[list[lka_llm.FunctionTool | lka_llm.RawFunctionTool]] = NOT_GIVEN
        self.tool_choice: NotGivenOr[lka_llm.ToolChoice] = NOT_GIVEN
        self.structured_output: NotGivenOr[type[BaseModel]] = NOT_GIVEN
        self.reasoning_effort: NotGivenOr[Literal['low', 'medium', 'high']] = NOT_GIVEN
        self.timeout: NotGivenOr[float] = NOT_GIVEN
        self.n_retries: NotGivenOr[int] = NOT_GIVEN
        self.retry_delay: NotGivenOr[float] = NOT_GIVEN
        self.fallbackvalue: NotGivenOr[APIResponse | str | BaseModel] = NOT_GIVEN

    @abc.abstractmethod
    async def acall(self, *args, **kwargs) -> APIResponse:
        pass

    def with_params(self, **kwargs) -> 'BaseProvider':
        def _copy_if_mutable(obj: Any) -> Any:
            return copy.deepcopy(obj) if isinstance(obj, dict | list | set) else obj

        out = copy.copy(self)  # shallow copy
        out.__dict__ = {k: _copy_if_mutable(v) for k, v in self.__dict__.items()}
        out.__dict__.update(kwargs)
        return out

    @abc.abstractmethod
    async def aclose(self):
        pass


class Strategy(abc.ABC):
    def __init__(
        self,
        providers: list[BaseProvider],
        fallbackvalue: NotGivenOr[APIResponse | str | BaseModel] = NOT_GIVEN,
    ):
        assert providers, "providers must be a non-empty list"
        self.providers = providers
        self.fallbackvalue = fallbackvalue

    @abc.abstractmethod
    async def acall(self, *args, **kwargs) -> APIResponse:
        pass


class OpenAIProvider(BaseProvider):
    URL = "https://api.openai.com/v1/chat/completions"
    MODELS = ['gpt-4.1', 'gpt-4.1-mini', 'gpt-4o', 'gpt-4o-mini']

    def __init__(self, api_key: str, url: NotGivenOr[str] = NOT_GIVEN):
        super().__init__()
        self.api_key = api_key
        self.url = url or self.URL
        self.client = aiohttp.ClientSession()

    async def acall(
        self,
        chat_ctx: lka_llm.ChatContext | str,
        model: NotGivenOr[str] = NOT_GIVEN,
        temperature: NotGivenOr[float] = 0.5,
        max_tokens: NotGivenOr[int] = 512,
        tools: list[lka_llm.FunctionTool | lka_llm.RawFunctionTool] = [],
        tool_choice: NotGivenOr[lka_llm.ToolChoice] = NOT_GIVEN,
        structured_output: NotGivenOr[type[BaseModel]] = NOT_GIVEN,
        reasoning_effort: NotGivenOr[Literal['low', 'medium', 'high']] = NOT_GIVEN,
        timeout: NotGivenOr[float] = 5.0,
        n_retries: NotGivenOr[int] = 1,
        retry_delay: NotGivenOr[float] = 1.0,
        fallbackvalue: NotGivenOr[APIResponse | str | BaseModel] = NOT_GIVEN,
    ) -> APIResponse:
        model = self.model or model
        temperature = self.temperature or temperature
        max_tokens = self.max_tokens or max_tokens
        tools = self.tools or tools
        tool_choice = self.tool_choice or tool_choice
        reasoning_effort = self.reasoning_effort or reasoning_effort
        timeout = self.timeout or timeout or 5.0
        n_retries = self.n_retries or n_retries or 1
        retry_delay = self.retry_delay or retry_delay or 1.0
        fallbackvalue = self.fallbackvalue or fallbackvalue
        assert model in self.MODELS, f"invalid {model=}"
        logger.debug(f"🏎 `{model}` start acall")

        if isinstance(chat_ctx, str):
            messages, _ = lka_llm.ChatContext(
                [lka_llm.ChatMessage(role="user", content=[chat_ctx])]
            ).to_provider_format("openai")
        elif isinstance(chat_ctx, lka_llm.ChatContext):
            messages, _ = chat_ctx.to_provider_format("openai")

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
        }
        if utils.is_given(max_tokens):
            payload["max_tokens"] = max_tokens
        if utils.is_given(temperature):
            payload["temperature"] = temperature
        if utils.is_given(tools) and len(tools) > 0 and (tool_choice != "none"):
            payload["tools"] = [_to_raw_schema(tool) for tool in tools]
            payload["tool_choice"] = tool_choice if utils.is_given(tool_choice) else "auto"
        if utils.is_given(structured_output):
            raise NotImplementedError(
                f"structured_output is not supported for {self.__class__.__name__}"
            )

        def _is_tool_call(response_json: dict) -> bool:
            if not (("choices" in response_json) and response_json["choices"]):
                return False
            return (response_json["choices"][0]['finish_reason'] == 'tool_calls') or (
                ('tool_calls' in response_json["choices"][0]['message'])
                and response_json["choices"][0]['message']['tool_calls']
            )

        def _unpack_content(response_json: dict) -> str:
            msg = response_json["choices"][0]["message"]
            return msg["content"]

        def _unpack_tool_call(response_json: dict) -> APIResponseToolCall:
            msg = response_json["choices"][0]["message"]
            tool_choice = payload.get("tool_choice", "auto")
            call_id = msg["tool_calls"][0]["id"]
            name = msg["tool_calls"][0]["function"]["name"]
            args = msg["tool_calls"][0]["function"]["arguments"]
            ptools = {_get_tool_info(t).name: t for t in tools}
            if ('tools' not in payload) or (not payload["tools"]):
                raise ValueError(f"tools are not provided but tool={name}")
            if tool_choice == "none":
                raise ValueError(f"tool_choice is 'none' but tool={name} | possible={ptools}")
            elif tool_choice in ["auto", "required"]:
                if name not in ptools:
                    raise ValueError(f"Wrong tool call name={name} | possible={ptools}")
            else:
                raise NotImplementedError(f"not supported yet tool_choice={tool_choice}")
            try:
                lka_llm.utils.prepare_function_arguments(
                    fnc=ptools[name],
                    json_arguments=args,
                    call_ctx="fake_call_ctx",  # type: ignore
                )
            except Exception:
                raise ValueError(f"tool={name} but failed to parse arguments={args}")
            return APIResponseToolCall(name=name, args=args, id=call_id)

        response_json = None
        start_ts = time.time()
        # self.client = self.client or aiohttp.ClientSession()
        for attempt in range(1, n_retries + 1):
            try:
                if self.client.closed:
                    raise SessionIsClosedError("Session is closed")

                async with self.client.post(
                    url=self.url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as response:
                    response_json = await response.json()
                    return APIResponse(
                        payload=_unpack_tool_call(response_json)
                        if _is_tool_call(response_json)
                        else _unpack_content(response_json),
                        id=response_json.get("id", None),
                        model=payload["model"],
                        provider_time=time.time() - start_ts,
                        attempt=attempt,
                    )
            except SessionIsClosedError:
                return APIResponse.fallback("goodbye_end_session")
            except Exception as e:
                """known errors:
                - RuntimeError (w 'Session is closed' in it)
                - asyncio.TimeoutError
                - aiohttp.client_exceptions.ClientOSError
                - aiohttp.client_exceptions.ServerDisconnectedError
                """
                msg = (
                    f"{e.__class__.__name__} in OpenAIProvider.acall"
                    f" | {attempt}/{n_retries} | {traceback.format_exc()}"
                    f" | {response_json=}"
                )
                if attempt < n_retries:
                    logger.debug(msg)
                    await asyncio.sleep(retry_delay)
                else:
                    logger.warning(msg)
                    if utils.is_given(fallbackvalue):
                        return APIResponse.fallback(fallbackvalue)  # type: ignore
                    raise e

        # This should never be reached, but mypy requires a return statement
        raise RuntimeError("All retry attempts failed")

    async def aclose(self):
        if self.client:
            await self.client.close()


class OpenRouterProvider(OpenAIProvider):
    URL = "https://openrouter.ai/api/v1/chat/completions"
    MODELS = []


class GroqProvider(OpenAIProvider):
    URL = "https://api.groq.com/openai/v1/chat/completions"
    MODELS = ['openai/gpt-oss-120b', 'openai/gpt-oss-20b']

    async def acall(
        self,
        chat_ctx: lka_llm.ChatContext | str,
        model: NotGivenOr[str] = NOT_GIVEN,
        temperature: NotGivenOr[float] = 0.5,
        max_tokens: NotGivenOr[int] = 1024,
        tools: list[lka_llm.FunctionTool | lka_llm.RawFunctionTool] = [],
        tool_choice: NotGivenOr[lka_llm.ToolChoice] = NOT_GIVEN,
        structured_output: NotGivenOr[type[BaseModel]] = NOT_GIVEN,
        reasoning_effort: NotGivenOr[Literal['low', 'medium', 'high']] = NOT_GIVEN,
        timeout: NotGivenOr[float] = 5.0,
        n_retries: NotGivenOr[int] = 3,
        retry_delay: NotGivenOr[float] = 1.0,
        fallbackvalue: NotGivenOr[APIResponse | str | BaseModel] = NOT_GIVEN,
    ) -> APIResponse:
        model = self.model or model
        temperature = self.temperature or temperature
        max_tokens = self.max_tokens or max_tokens
        tools = self.tools or tools
        tool_choice = self.tool_choice or tool_choice
        reasoning_effort = self.reasoning_effort or reasoning_effort
        timeout = self.timeout or timeout or 5.0
        n_retries = self.n_retries or n_retries or 1
        retry_delay = self.retry_delay or retry_delay or 1.0
        fallbackvalue = self.fallbackvalue or fallbackvalue
        assert model in self.MODELS, f"invalid {model=}"
        logger.debug(f"🏎 `{model}` start acall")

        if isinstance(chat_ctx, lka_llm.ChatContext):
            messages, _ = chat_ctx.to_provider_format("openai")
        elif isinstance(chat_ctx, str):
            messages, _ = lka_llm.ChatContext(
                [lka_llm.ChatMessage(role="user", content=[chat_ctx])]
            ).to_provider_format("openai")

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if tools:
            tools = [] if (tool_choice == "none") else tools
            payload["tools"] = [_to_raw_schema(tool) for tool in tools]
            payload["tool_choice"] = tool_choice if utils.is_given(tool_choice) else "auto"
        if utils.is_given(structured_output):
            raise NotImplementedError(
                f"structured_output is not supported for {self.__class__.__name__}"
            )
        if utils.is_given(reasoning_effort):
            payload["reasoning_effort"] = reasoning_effort

        def _is_tool_call(response_json: dict) -> bool:
            return (
                ("choices" in response_json)
                and (response_json["choices"])
                and (response_json["choices"][0]['finish_reason'] == 'tool_calls')
            )

        def _unpack_tool_call(response_json: dict) -> APIResponseToolCall:
            msg = response_json["choices"][0]["message"]
            tool_choice = payload.get("tool_choice", "auto")
            call_id = msg["tool_calls"][0]["id"]
            name = msg["tool_calls"][0]["function"]["name"]
            args = msg["tool_calls"][0]["function"]["arguments"]
            ptools = {_get_tool_info(t).name: t for t in tools}
            if ('tools' not in payload) or (not payload["tools"]):
                raise ValueError(f"tools are not provided but tool={name}")
            if tool_choice == "none":
                raise ValueError(f"tool_choice is 'none' but tool={name} | possible={ptools}")
            elif tool_choice in ["auto", "required"]:
                if name not in ptools:
                    raise ValueError(f"Wrong tool call name={name} | possible={ptools}")
            else:
                raise NotImplementedError(f"not supported yet tool_choice={tool_choice}")
            try:
                lka_llm.utils.prepare_function_arguments(
                    fnc=ptools[name],
                    json_arguments=args,
                    call_ctx="fake_call_ctx",  # type: ignore
                )
            except Exception:
                raise ValueError(f"tool={name} but failed to parse arguments={args}")
            return APIResponseToolCall(name=name, args=args, id=call_id)

        def _unpack_content(response_json: dict) -> str:
            msg = response_json["choices"][0]["message"]
            content = msg.get("content", "")
            return content

        def _is_error_w_tool_calls(response_json: dict) -> bool:
            return (
                ("error" in response_json)
                and ("failed_generation" in response_json["error"])
                and (payload.get("tools", []))
            )

        def _try_unpack_tool_calls_w_error(response_json: dict) -> APIResponseToolCall:
            content = json.loads(response_json["error"]["failed_generation"])
            tool_choice = payload.get("tool_choice", "auto")
            call_id = str(uuid.uuid4())
            name = content["name"]
            args = json.dumps(content["arguments"])
            ptools = {_get_tool_info(t).name: t for t in tools}
            if ('tools' not in payload) or (not payload["tools"]):
                raise ValueError(f"tools are not provided but tool={name}")
            if tool_choice == "none":
                raise ValueError(f"tool_choice is 'none' but tool={name} | possible={ptools}")
            elif tool_choice in ["auto", "required"]:
                if name not in ptools:
                    raise ValueError(f"Wrong tool call name={name} | possible={ptools}")
            else:
                raise NotImplementedError(f"not supported yet tool_choice={tool_choice}")
            try:
                lka_llm.utils.prepare_function_arguments(
                    fnc=ptools[name],
                    json_arguments=args,
                    call_ctx="fake_call_ctx",  # type: ignore
                )
            except Exception:
                raise ValueError(f"tool={name} but failed to parse arguments={args}")
            return APIResponseToolCall(name=name, args=args, id=call_id)

        response_json = None
        start_ts = time.time()
        # self.client = self.client or aiohttp.ClientSession()
        for attempt in range(1, n_retries + 1):
            try:
                if self.client.closed:
                    raise SessionIsClosedError("Session is closed")

                async with self.client.post(
                    url=self.url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as response:
                    response_json = await response.json()

                    if _is_error_w_tool_calls(response_json):
                        logger.debug(
                            "`GroqProvider` error with tools",
                            extra={"response_json": response_json},
                        )
                        return APIResponse(
                            payload=_try_unpack_tool_calls_w_error(response_json),
                            id=str(uuid.uuid4()),
                            attempt=attempt,
                            model=payload["model"],
                            provider_time=time.time() - start_ts,
                        )

                    return APIResponse(
                        payload=_unpack_tool_call(response_json)
                        if _is_tool_call(response_json)
                        else _unpack_content(response_json),
                        id=response_json.get("id", None),
                        attempt=attempt,
                        model=payload["model"],
                        provider_time=time.time() - start_ts,
                    )
            except SessionIsClosedError:
                return APIResponse.fallback("goodbye_end_session")
            except Exception as e:
                msg = (
                    f"{e.__class__.__name__} in GroqProvider.acall"
                    f" | {attempt}/{n_retries} | {traceback.format_exc()}"
                    f" | {response_json=}"
                )
                if attempt < n_retries:
                    logger.debug(msg)
                    await asyncio.sleep(retry_delay)
                else:
                    logger.warning(msg)
                    if utils.is_given(fallbackvalue):
                        return APIResponse.fallback(fallbackvalue)  # type: ignore
                    raise e

        # This should never be reached, but mypy requires a return statement
        raise RuntimeError("All retry attempts failed")


class LangChainProvider(BaseProvider):
    MODELS: list[str] = []
    TYPE: str = ""
    CONFIGURABLE_FIELDS: dict[str, ConfigurableField] = {}

    def __init__(self, basechatmodel: BaseChatModel):
        self.basechatmodel = basechatmodel.configurable_fields(**self.CONFIGURABLE_FIELDS)
        self.init_params()

    async def acall(
        self,
        chat_ctx: lka_llm.ChatContext | list[BaseMessage] | str,
        model: NotGivenOr[str] = NOT_GIVEN,
        temperature: NotGivenOr[float] = 0.5,
        max_tokens: NotGivenOr[int] = 512,
        structured_output: NotGivenOr[type[BaseModel]] = NOT_GIVEN,
        n_retries: NotGivenOr[int] = 1,
        timeout: NotGivenOr[float] = 5.0,
        retry_delay: NotGivenOr[float] = 1.0,
        tools: list[lka_llm.FunctionTool | lka_llm.RawFunctionTool] = [],
        tool_choice: NotGivenOr[lka_llm.ToolChoice] = NOT_GIVEN,
        reasoning_effort: NotGivenOr[Literal['low', 'medium', 'high']] = NOT_GIVEN,
        fallbackvalue: NotGivenOr[APIResponse | str | BaseModel] = NOT_GIVEN,
    ) -> APIResponse:
        model = self.model or model or "unknown"
        temperature = self.temperature or temperature
        max_tokens = self.max_tokens or max_tokens
        structured_output = self.structured_output or structured_output
        tools = self.tools or tools
        tool_choice = self.tool_choice or tool_choice
        reasoning_effort = self.reasoning_effort or reasoning_effort
        timeout = self.timeout or timeout
        n_retries = self.n_retries or n_retries
        retry_delay = self.retry_delay or retry_delay
        fallbackvalue = self.fallbackvalue or fallbackvalue
        logger.debug(f"🏎 `{model}` start acall")

        if isinstance(chat_ctx, str):
            messages: list[BaseMessage] = [HumanMessage(content=chat_ctx)]
        elif isinstance(chat_ctx, lka_llm.ChatContext):
            messages = self.chat_ctx_to_langchain_messages(chat_ctx)
        else:
            messages = chat_ctx
        lgmodel = cast(BaseChatModel, self.basechatmodel)
        _to_thinking_budget = {'low': 1024, 'medium': 8192, 'high': 32768}
        config: dict[str, Any] = {}
        if utils.is_given(model):
            config['model' if (self.TYPE == "gemini") else 'model_name'] = model
        if utils.is_given(temperature):
            config['temperature'] = temperature
        if utils.is_given(max_tokens):
            config['max_output_tokens' if (self.TYPE == "gemini") else 'max_tokens'] = max_tokens
        if utils.is_given(timeout):
            config['timeout' if (self.TYPE == "gemini") else 'request_timeout'] = timeout
        if utils.is_given(reasoning_effort):
            if self.TYPE == "gemini":
                config['thinking_budget'] = _to_thinking_budget[reasoning_effort]
            else:
                config['reasoning_effort'] = reasoning_effort
        elif self.TYPE == "gemini":
            config['thinking_budget'] = 0
        if utils.is_given(n_retries) and (n_retries > 1) and (self.TYPE == "gemini"):
            config['max_retries'] = n_retries
        attempt_clb = RetryAttemptTracker()
        lgmodel: BaseChatModel = lgmodel.with_config(  # type: ignore
            {"configurable": config, "callbacks": [attempt_clb]}
        )
        if utils.is_given(tools) and len(tools) > 0 and (tool_choice != "none"):
            lgmodel = lgmodel.bind_tools(  # type: ignore
                tools=[_to_raw_schema(tool) for tool in tools],
                tool_choice=tool_choice if utils.is_given(tool_choice) else "auto",  # type: ignore
            )
        if utils.is_given(structured_output):
            lgmodel = lgmodel.with_structured_output(structured_output)  # type: ignore
        if utils.is_given(n_retries) and (n_retries > 1) and (self.TYPE != "gemini"):
            lgmodel = lgmodel.with_retry(stop_after_attempt=n_retries)  # type: ignore
        if utils.is_given(fallbackvalue):
            lgmodel = lgmodel.with_fallbacks(
                [
                    RunnableLambda(lambda x: APIResponse.fallback(fallbackvalue))  # type: ignore
                ]
            )

        start_ts = time.time()
        output = await lgmodel.ainvoke(messages)

        if isinstance(output, APIResponse):
            return output  # fallback

        if utils.is_given(structured_output):
            assert isinstance(output, BaseModel), f"output must be a BaseModel | {output=}"
            return APIResponse(
                payload=cast(BaseModel, output),
                model=model,
                provider_time=time.time() - start_ts,
                attempt=attempt_clb.attempt,
            )

        assert isinstance(output, AIMessage), f"output must be a AIMessage | {output=}"

        if output.tool_calls:
            tool_call: ToolCall = output.tool_calls[0]
            assert isinstance(tool_call['id'], str), f"tool_call must have an id | {tool_call=}"
            return APIResponse(
                payload=APIResponseToolCall(
                    name=tool_call['name'],
                    args=tool_call['args'],
                    id=tool_call['id'],
                ),
                model=model,
                provider_time=time.time() - start_ts,
                attempt=attempt_clb.attempt,
            )
        return APIResponse(
            payload=cast(str, output.content),
            model=model,
            provider_time=time.time() - start_ts,
            attempt=attempt_clb.attempt,
        )

    def chat_ctx_to_langchain_messages(self, chat_ctx: lka_llm.ChatContext) -> list[BaseMessage]:
        """Convert chat context to langgraph input"""

        messages: list[BaseMessage] = []
        for item in chat_ctx.items:
            if isinstance(item, lka_llm.ChatMessage):
                content = item.text_content
                if content:
                    if item.role == "assistant":
                        messages.append(AIMessage(content=content, id=item.id))
                    elif item.role == "user":
                        messages.append(HumanMessage(content=content, id=item.id))
                    elif item.role in ["system", "developer"]:
                        messages.append(SystemMessage(content=content, id=item.id))
            elif isinstance(item, lka_llm.FunctionCall):
                messages.append(
                    AIMessage(
                        content="",
                        tool_calls=[
                            ToolCall(
                                name=item.name,
                                args=json.loads(item.arguments),
                                id=item.call_id,
                            )
                        ],
                        id=item.id,
                    )
                )
            elif isinstance(item, lka_llm.FunctionCallOutput):
                messages.append(
                    ToolMessage(
                        content=item.output,
                        tool_call_id=item.call_id,
                        status='error' if item.is_error else 'success',
                        id=item.id,
                    )
                )

        return messages

    async def aclose(self):
        pass


class LangChainOpenAIProvider(LangChainProvider):
    MODELS = ['gpt-4.1', 'gpt-4.1-mini', 'gpt-4o', 'gpt-4o-mini']
    TYPE = "openai"
    CONFIGURABLE_FIELDS = {
        'model_name': ConfigurableField(id="model_name", name="LLM Model"),
        'temperature': ConfigurableField(id="temperature", name="LLM Temperature"),
        'max_tokens': ConfigurableField(id="max_tokens", name="Max Tokens"),
        'request_timeout': ConfigurableField(id="request_timeout", name="Request Timeout"),
        'reasoning_effort': ConfigurableField(id="reasoning_effort", name="Reasoning Effort"),
    }


class LangChainGroqProvider(LangChainProvider):
    MODELS = ['openai/gpt-oss-120b', 'openai/gpt-oss-20b']
    TYPE = "groq"
    CONFIGURABLE_FIELDS = {
        'model_name': ConfigurableField(id="model_name", name="LLM Model"),
        'temperature': ConfigurableField(id="temperature", name="LLM Temperature"),
        'max_tokens': ConfigurableField(id="max_tokens", name="Max Tokens"),
        'request_timeout': ConfigurableField(id="request_timeout", name="Request Timeout"),
        'reasoning_effort': ConfigurableField(id="reasoning_effort", name="Reasoning Effort"),
    }


class LangChainGeminiProvider(LangChainProvider):
    MODELS = ['gemini-2.5-flash', 'gemini-2.5-flash-lite', 'gemini-2.5-pro']
    TYPE = "gemini"
    CONFIGURABLE_FIELDS = {
        'model': ConfigurableField(id="model", name="LLM Model"),
        'temperature': ConfigurableField(id="temperature", name="LLM Temperature"),
        'max_output_tokens': ConfigurableField(id="max_output_tokens", name="Max Tokens"),
        'timeout': ConfigurableField(id="timeout", name="Request Timeout"),
        'thinking_budget': ConfigurableField(id="thinking_budget", name="Thinking Budget"),
        'max_retries': ConfigurableField(id="max_retries", name="Max Retries"),
    }


class LangChainAdapter(BaseProvider):
    def __init__(self, **models: BaseChatModel):
        def _to_provider(model: BaseChatModel) -> LangChainProvider:
            if isinstance(model, ChatGoogleGenerativeAI):
                return LangChainGeminiProvider(model)
            elif isinstance(model, ChatOpenAI):
                return LangChainOpenAIProvider(model)
            elif isinstance(model, ChatGroq):
                return LangChainGroqProvider(model)
            else:
                raise ValueError(f"Unsupported model: {model.__class__.__name__}")

        self.models = {mname: _to_provider(model) for mname, model in models.items()}

    @property
    def openai(self) -> LangChainOpenAIProvider:
        assert 'openai' in self.models, "OpenAI model not found for LangChainAdapter"
        return cast(LangChainOpenAIProvider, self.models['openai'])

    @property
    def groq(self) -> LangChainGroqProvider:
        assert 'groq' in self.models, "Groq model not found for LangChainAdapter"
        return cast(LangChainGroqProvider, self.models['groq'])

    @property
    def gemini(self) -> LangChainGeminiProvider:
        assert 'gemini' in self.models, "Gemini model not found for LangChainAdapter"
        return cast(LangChainGeminiProvider, self.models['gemini'])

    async def acall(self, *args, **kwargs):
        raise NotImplementedError(
            "acall is not implemented for LangChainAdapter, use the underlying model directly"
        )

    async def aclose(self):
        for provider in self.models.values():
            await provider.aclose()


class RaceStrategy(Strategy):
    async def acall(self, *args, **kwargs) -> APIResponse:
        tasks = [
            asyncio.create_task(provider.acall(*args, **kwargs)) for provider in self.providers
        ]
        try:
            for coro in asyncio.as_completed(tasks):
                try:
                    result = await coro
                    return result  # fist success → finally
                except Exception:
                    # this task fall → next task
                    continue
            # all tasks are fall
            if utils.is_given(self.fallbackvalue):
                self.fallbackvalue: APIResponse | str | BaseModel
                return APIResponse.fallback(self.fallbackvalue)
            raise RuntimeError("All providers failed")
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()


class TimeoutFallbackStrategy(Strategy):
    def __init__(
        self,
        providers: list[BaseProvider],
        delays: list[float],
        fallbackvalue: NotGivenOr[APIResponse | str | BaseModel] = NOT_GIVEN,
    ):
        super().__init__(providers, fallbackvalue)
        self.delays = delays

    async def acall(self, *args, **kwargs) -> APIResponse:
        async def _delayed_call(provider: BaseProvider, delay: float):
            if delay > 0:
                await asyncio.sleep(delay)
            return await provider.acall(*args, **kwargs)

        tasks = [
            asyncio.create_task(_delayed_call(provider, delay))
            for provider, delay in zip(self.providers, self.delays)
        ]
        try:
            for coro in asyncio.as_completed(tasks):
                try:
                    result = await coro
                    return result  # fist success → finally
                except Exception:
                    # this task fall → next task
                    continue
            # all tasks are fall
            if utils.is_given(self.fallbackvalue):
                self.fallbackvalue: APIResponse | str | BaseModel
                return APIResponse.fallback(self.fallbackvalue)
            raise RuntimeError("All providers failed")
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()


class FallbackStrategy(Strategy):
    async def acall(self, *args, **kwargs) -> APIResponse:
        for provider in self.providers:
            try:
                return await provider.acall(*args, **kwargs)
            except Exception:
                # this provider failed → go next
                continue
        if utils.is_given(self.fallbackvalue):
            self.fallbackvalue: APIResponse | str | BaseModel
            return APIResponse.fallback(self.fallbackvalue)
        raise RuntimeError("All providers failed")


class LLMAPI:
    def __init__(self, **providers: BaseProvider):
        self.providers = providers

    @property
    def openai(self) -> OpenAIProvider:
        if 'openai' in self.providers:
            return cast(OpenAIProvider, self.providers['openai'])
        raise ValueError("OpenAIProvider not found")

    @property
    def openrouter(self) -> OpenRouterProvider:
        if 'openrouter' in self.providers:
            return cast(OpenRouterProvider, self.providers['openrouter'])
        raise ValueError("OpenRouterProvider not found")

    @property
    def groq(self) -> GroqProvider:
        if 'groq' in self.providers:
            return cast(GroqProvider, self.providers['groq'])
        raise ValueError("GroqProvider not found")

    @property
    def langchain(self) -> LangChainAdapter:
        if 'langchain' in self.providers:
            return cast(LangChainAdapter, self.providers['langchain'])
        raise ValueError("LangChainAdapter not found")

    def race(
        self,
        providers: list[BaseProvider],
        fallbackvalue: NotGivenOr[str | BaseModel | APIResponse] = NOT_GIVEN,
    ) -> RaceStrategy:
        return RaceStrategy(providers, fallbackvalue)

    def timeoutfallback(
        self,
        providers: list[BaseProvider],
        delays: list[float],
        fallbackvalue: NotGivenOr[str | BaseModel | APIResponse] = NOT_GIVEN,
    ) -> TimeoutFallbackStrategy:
        return TimeoutFallbackStrategy(providers, delays, fallbackvalue)

    def fallback(
        self,
        providers: list[BaseProvider],
        fallbackvalue: NotGivenOr[str | BaseModel | APIResponse] = NOT_GIVEN,
    ) -> FallbackStrategy:
        return FallbackStrategy(providers, fallbackvalue)

    async def aclose(self):
        for provider in self.providers.values():
            try:
                await provider.aclose()
            except Exception as e:
                logger.error(
                    f"Error while closing provider={provider.__class__.__name__}"
                    f" | {e} | {traceback.format_exc()}"
                )
        logger.info(f"🫡️️️️️️ `{self.__class__.__name__}` closed")


if __name__ == "__main__":
    pass
