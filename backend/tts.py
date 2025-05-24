import asyncio
import logging
import os
import weakref
from typing import AsyncIterable

import aiohttp

from livekit import rtc
from livekit.agents import Agent, APITimeoutError, APIStatusError, APIConnectionError, tts, utils, tokenize
from livekit.agents.voice import ModelSettings
from livekit.plugins.elevenlabs.tts import (
    API_BASE_URL_V1, DEFAULT_VOICE_ID, DEFAULT_API_CONNECT_OPTIONS, NOT_GIVEN,
    APIConnectOptions, ChunkedStream, SynthesizeStream, TTS, TTSEncoding,
    TTSModels, VoiceSettings, WS_INACTIVITY_TIMEOUT, NotGivenOr, _DefaultEncoding,
    _TTSOptions, _sample_rate_from_format, _strip_nones, _synthesize_url,
    dataclasses, is_given
)


logger = logging.getLogger("livekit.agents")


class AdapterStreamingFalseNextTextTTS:
    async def tts_node(
        self,
        text: AsyncIterable[str],
        model_settings: ModelSettings
    ) -> AsyncIterable[rtc.AudioFrame]:
        if isinstance(self.tts, StreamingFalseNextTextTTS):
            async for frame in Agent.default.tts_node(self, text, model_settings):
                yield frame
        else:
            # wrapped tts w SingleSentenceTokenizer
            activity = self._get_activity_or_raise()
            assert activity.tts is not None, "tts_node called but no TTS node is available"
            wrapped_tts = activity.tts
            if not activity.tts.capabilities.streaming:
                wrapped_tts = tts.StreamAdapter(
                    tts=wrapped_tts, sentence_tokenizer=SingleSentenceTokenizer()
                )
            async with wrapped_tts.stream() as stream:
                async def _forward_input():
                    async for chunk in text:
                        stream.push_text(chunk)
                    stream.end_input()
                forward_task = asyncio.create_task(_forward_input())
                try:
                    async for ev in stream:
                        yield ev.frame
                finally:
                    await utils.aio.cancel_and_wait(forward_task)


class SingleSentenceTokenizer(tokenize.tokenizer.SentenceTokenizer):
    def __init__(
        self,
        *,
        language: str = "english",
    ) -> None:
        self._language = language

    def tokenize(self, text: str, *, language: str | None = None) -> list[str]:
        return [text]

    def stream(self, *, language: str | None = None) -> "tokenize.tokenizer.SentenceStream":
        return tokenize.token_stream.BufferedSentenceStream(
            tokenizer=lambda text: [(text, 0, len(text))],
            min_token_len=1,
            min_ctx_len=1,
        )


class ExtendedChunkedStream(ChunkedStream):
    async def _run(self) -> None:
        """We added next_text to the data dictionary"""
        request_id = utils.shortuuid()
        voice_settings = (
            _strip_nones(dataclasses.asdict(self._opts.voice_settings))
            if is_given(self._opts.voice_settings)
            else None
        )
        
        data = {
            "text": self._input_text,
            "model_id": self._opts.model,
            "voice_settings": voice_settings,
        }
        
        next_text = getattr(self._tts, '_next_text', NOT_GIVEN)
        if is_given(next_text):
            data["text"] = f"\"{data['text']}\""
            data["next_text"] = next_text
            logger.info(f"data: {data}")
            
        decoder = utils.codecs.AudioStreamDecoder(
            sample_rate=self._opts.sample_rate,
            num_channels=1,
        )

        decode_task = None
        try:
            async with self._session.post(
                _synthesize_url(self._opts),
                headers={"xi-api-key": self._opts.api_key},
                json=data,
                timeout=aiohttp.ClientTimeout(
                    total=30,
                    sock_connect=self._conn_options.timeout,
                ),
            ) as resp:
                if not resp.content_type.startswith("audio/"):
                    content = await resp.text()
                    print(f"11labs returned non-audio data: {content}")
                    return

                async def _decode_loop():
                    try:
                        async for bytes_data, _ in resp.content.iter_chunks():
                            decoder.push(bytes_data)
                    finally:
                        decoder.end_input()

                decode_task = asyncio.create_task(_decode_loop())
                emitter = tts.SynthesizedAudioEmitter(
                    event_ch=self._event_ch,
                    request_id=request_id,
                )
                async for frame in decoder:
                    emitter.push(frame)
                emitter.flush()
        except asyncio.TimeoutError as e:
            raise APITimeoutError() from e
        except aiohttp.ClientResponseError as e:
            raise APIStatusError(
                message=e.message,
                status_code=e.status,
                request_id=None,
                body=None,
            ) from e
        except Exception as e:
            raise APIConnectionError() from e
        finally:
            if decode_task:
                await utils.aio.gracefully_cancel(decode_task)
            await decoder.aclose()


class StreamingFalseNextTextTTS(TTS):
    def __init__(
        self,
        *,
        voice_id: str = DEFAULT_VOICE_ID,
        voice_settings: NotGivenOr[VoiceSettings] = NOT_GIVEN,
        model: TTSModels | str = "eleven_turbo_v2_5",
        encoding: NotGivenOr[TTSEncoding] = NOT_GIVEN,
        api_key: NotGivenOr[str] = NOT_GIVEN,
        base_url: NotGivenOr[str] = NOT_GIVEN,
        streaming_latency: NotGivenOr[int] = NOT_GIVEN,
        inactivity_timeout: int = WS_INACTIVITY_TIMEOUT,
        word_tokenizer: NotGivenOr[tokenize.WordTokenizer] = NOT_GIVEN,
        enable_ssml_parsing: bool = False,
        chunk_length_schedule: NotGivenOr[list[int]] = NOT_GIVEN,  # range is [50, 500]
        http_session: aiohttp.ClientSession | None = None,
        language: NotGivenOr[str] = NOT_GIVEN,
        next_text: NotGivenOr[str] = NOT_GIVEN,
    ) -> None:
        """
        Create a new instance of ElevenLabs TTS.

        Args:
            voice_id (str): Voice ID. Defaults to `DEFAULT_VOICE_ID`.
            voice_settings (NotGivenOr[VoiceSettings]): Voice settings.
            model (TTSModels | str): TTS model to use. Defaults to "eleven_turbo_v2_5".
            api_key (NotGivenOr[str]): ElevenLabs API key. Can be set via argument or `ELEVEN_API_KEY` environment variable.
            base_url (NotGivenOr[str]): Custom base URL for the API. Optional.
            streaming_latency (NotGivenOr[int]): Optimize for streaming latency, defaults to 0 - disabled. 4 for max latency optimizations. deprecated
            inactivity_timeout (int): Inactivity timeout in seconds for the websocket connection. Defaults to 300.
            word_tokenizer (NotGivenOr[tokenize.WordTokenizer]): Tokenizer for processing text. Defaults to basic WordTokenizer.
            enable_ssml_parsing (bool): Enable SSML parsing for input text. Defaults to False.
            chunk_length_schedule (NotGivenOr[list[int]]): Schedule for chunk lengths, ranging from 50 to 500. Defaults are [120, 160, 250, 290].
            http_session (aiohttp.ClientSession | None): Custom HTTP session for API requests. Optional.
            language (NotGivenOr[str]): Language code for the TTS model, as of 10/24/24 only valid for "eleven_turbo_v2_5".
        """  # noqa: E501

        """streaming = False and add next_text"""

        if not is_given(encoding):
            encoding = _DefaultEncoding

        tts.TTS.__init__(
            self,
            capabilities=tts.TTSCapabilities(
                streaming=False,
            ),
            sample_rate=_sample_rate_from_format(encoding),
            num_channels=1,
        )

        elevenlabs_api_key = api_key if is_given(api_key) else os.environ.get("ELEVEN_API_KEY")
        if not elevenlabs_api_key:
            raise ValueError(
                "ElevenLabs API key is required, either as argument or set ELEVEN_API_KEY environmental variable"  # noqa: E501
            )

        if not is_given(word_tokenizer):
            word_tokenizer = tokenize.basic.WordTokenizer(
                ignore_punctuation=False  # punctuation can help for intonation
            )
        
        self._next_text = next_text
        self._opts = _TTSOptions(
            voice_id=voice_id,
            voice_settings=voice_settings,
            model=model,
            api_key=elevenlabs_api_key,
            base_url=base_url if is_given(base_url) else API_BASE_URL_V1,
            encoding=encoding,
            sample_rate=self.sample_rate,
            streaming_latency=streaming_latency,
            word_tokenizer=word_tokenizer,
            chunk_length_schedule=chunk_length_schedule,
            enable_ssml_parsing=enable_ssml_parsing,
            language=language,
            inactivity_timeout=inactivity_timeout,
        )
        self._session = http_session
        self._streams = weakref.WeakSet[SynthesizeStream]()
    
    def update_options(
        self,
        *,
        voice_id: NotGivenOr[str] = NOT_GIVEN,
        voice_settings: NotGivenOr[dict] = NOT_GIVEN,
        model: NotGivenOr[str] = NOT_GIVEN,
        language: NotGivenOr[str] = NOT_GIVEN,
        next_text: NotGivenOr[str] = NOT_GIVEN,
    ) -> None:
        super().update_options(
            voice_id=voice_id,
            voice_settings=voice_settings,
            model=model,
            language=language,
        )
        if is_given(next_text):
            self._next_text = next_text
    
    def synthesize(
        self,
        text: str,
        *,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> ExtendedChunkedStream:
        return ExtendedChunkedStream(
            tts=self,
            input_text=text,
            conn_options=conn_options,
            opts=self._opts,
            session=self._ensure_session(),
        )
