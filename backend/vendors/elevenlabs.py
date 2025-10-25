from dataclasses import dataclass

from livekit.agents.types import NOT_GIVEN, NotGivenOr
from livekit.plugins import elevenlabs
from livekit.plugins.elevenlabs import TTSModels


@dataclass
class ElevenLabsVoice:
    description: str
    voice_id: str
    model: TTSModels
    stability: float  # [0.0 - 1.0]
    similarity_boost: float  # [0.0 - 1.0]
    use_speaker_boost: NotGivenOr[bool] = NOT_GIVEN
    speed: NotGivenOr[float] = NOT_GIVEN  # [0.5 - 2.0]

    @property
    def voice_settings(self) -> elevenlabs.VoiceSettings:
        return elevenlabs.VoiceSettings(
            speed=self.speed,
            stability=self.stability,
            similarity_boost=self.similarity_boost,
            style=NOT_GIVEN,
            use_speaker_boost=self.use_speaker_boost,
        )


class ElevenLabsVoices:
    # Female American
    FemaleAmericanNaturalV1 = ElevenLabsVoice(
        description="Female natural young voice",
        voice_id="vCtsjVgYIHzgI7B7Us9U",
        model="eleven_turbo_v2",
        stability=0.3,
        similarity_boost=0.9,
        use_speaker_boost=True,
    )
    FemaleAmericanSoftV1 = ElevenLabsVoice(
        description="Female soft young voice",
        voice_id="uYXf8XasLslADfZ2MB4u",
        model="eleven_turbo_v2",
        stability=0.5,
        similarity_boost=0.9,
        use_speaker_boost=True,
    )
    FemaleAmericanClearV1 = ElevenLabsVoice(
        description="Female clear young german-rooted voice",
        voice_id="aMSt68OGf4xUZAnLpTU8",
        model="eleven_turbo_v2",
        stability=0.5,
        similarity_boost=0.9,
        use_speaker_boost=True,
    )
    FemaleAmericanEnergeticV1 = ElevenLabsVoice(
        description="Female energetic young voice",
        voice_id="K5WpC1IyXDDHtfm0szAh",
        model="eleven_turbo_v2",
        stability=0.4,
        similarity_boost=0.8,
        use_speaker_boost=True,
    )
    # Male American
    MaleAmericanNaturalV1 = ElevenLabsVoice(
        description="Male natural young voice",
        voice_id="248nvfaZe8BXhKntjmpp",
        model="eleven_turbo_v2",
        stability=0.3,
        similarity_boost=0.9,
        use_speaker_boost=True,
    )
    MaleAmericanSoftV1 = ElevenLabsVoice(
        description="Male soft young voice",
        voice_id="CY0l809fcTjyjw2zBhUZ",
        model="eleven_turbo_v2",
        stability=0.3,
        similarity_boost=0.9,
        use_speaker_boost=True,
    )
    MaleAmericanClearV1 = ElevenLabsVoice(
        description="Male clear young voice",
        voice_id="1SM7GgM6IMuvQlz2BwM3",
        model="eleven_turbo_v2",
        stability=0.3,
        similarity_boost=0.8,
        use_speaker_boost=True,
    )
    MaleAmericanEnergeticV1 = ElevenLabsVoice(
        description="Male energetic young voice",
        voice_id="UgBBYS2sOqTuMpoF3BR0",
        model="eleven_turbo_v2",
        stability=0.3,
        similarity_boost=0.8,
        use_speaker_boost=True,
    )
    # Other female voices
    Halley = ElevenLabsVoice(
        description="Best by call durrations | intonation delay at the end of a sentence",
        voice_id="eBvoGh8YGJn1xokno71w",
        model="eleven_turbo_v2",
        stability=0.3,
        similarity_boost=0.9,
        use_speaker_boost=True,
    )
    Chloe = ElevenLabsVoice(
        description="Best by CR | retell chloe(stacy) but a lot worse intonations",
        voice_id="EiBGPYZfqYqvAxnb3Ohu",
        model="eleven_turbo_v2",
        stability=0.3,
        similarity_boost=0.9,
        use_speaker_boost=True,
    )
    HopePodcaster = ElevenLabsVoice(
        description="Energetic and good intonations",
        voice_id="zGjIP4SZlMnY9m93k97r",
        model="eleven_turbo_v2_5",
        stability=0.5,
        similarity_boost=1.0,
        use_speaker_boost=True,
    )
    Alexandra = ElevenLabsVoice(
        description="Female young voice",
        voice_id="kdmDKE6EkgrWrrykO9Qt",
        model="eleven_turbo_v2_5",
        stability=0.6,
        similarity_boost=0.8,
        use_speaker_boost=True,
    )
