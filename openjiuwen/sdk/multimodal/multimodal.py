"""SDK Multimodal façade — vision and audio inputs for agents.

Attach image or audio files to an agent ``run()`` call so the underlying
multimodal model (e.g. GPT-4o) can reason about them.

Quick start::

    from openjiuwen.sdk.multimodal import ImageInput, VisionModelConfig

    agent = await Agent.create(
        "vision-agent",
        model=ModelConfig.from_env(),
        vision_config=VisionModelConfig(model="gpt-4o"),
    )
    result = await agent.run(
        "What is in this image?",
        images=[ImageInput.from_file("/path/to/image.png")],
    )
"""

from __future__ import annotations

import base64
import mimetypes
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from openjiuwen.sdk.core.errors import SdkError

# Supported MIME types
_SUPPORTED_IMAGE_MIMES = frozenset(
    ["image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp"]
)
_SUPPORTED_AUDIO_MIMES = frozenset(
    ["audio/mpeg", "audio/mp3", "audio/wav", "audio/ogg", "audio/m4a", "audio/flac"]
)


# ---------------------------------------------------------------------------
# Model configuration types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VisionModelConfig:
    """Configuration for vision model calls.

    Attributes:
        model:      Vision model identifier (e.g. ``"gpt-4o"``).
        max_tokens: Cap on tokens for the vision response.
    """

    model: str = "gpt-4o"
    max_tokens: int | None = None


@dataclass(frozen=True)
class AudioModelConfig:
    """Configuration for audio transcription calls.

    Attributes:
        model:    Audio model identifier (e.g. ``"whisper-1"``).
        language: ISO-639-1 language code hint (e.g. ``"en"``).
    """

    model: str = "whisper-1"
    language: str | None = None


# ---------------------------------------------------------------------------
# Attachment base — generic typed attachment
# ---------------------------------------------------------------------------


@dataclass
class Attachment:
    """A typed binary attachment (image, audio, or document).

    Use :meth:`from_file` to construct from a local path.  The MIME type is
    inferred from the file extension.

    Example::

        att = Attachment.from_file("/tmp/chart.png")
        # att.mime_type == "image/png"
    """

    data: bytes
    mime_type: str
    filename: str = ""

    _SUPPORTED_MIMES = _SUPPORTED_IMAGE_MIMES | _SUPPORTED_AUDIO_MIMES | frozenset(
        ["application/pdf", "text/plain"]
    )

    @classmethod
    def from_file(cls, path: str | Path) -> "Attachment":
        """Load an attachment from a local file path.

        Args:
            path: Absolute or relative path to the file.

        Returns:
            :class:`Attachment` with ``data`` and ``mime_type`` set.

        Raises:
            :class:`~openjiuwen.sdk.core.errors.SdkError`: If the MIME type is not supported.
        """
        p = Path(path)
        mime, _ = mimetypes.guess_type(str(p))
        if mime is None:
            mime = "application/octet-stream"
        if mime not in cls._SUPPORTED_MIMES:
            raise SdkError(
                f"Unsupported MIME type '{mime}' for file '{p.name}'. "
                f"Supported types: {sorted(cls._SUPPORTED_MIMES)}"
            )
        data = p.read_bytes()
        return cls(data=data, mime_type=mime, filename=p.name)

    def to_base64(self) -> str:
        """Return the attachment data as a base64-encoded string."""
        return base64.b64encode(self.data).decode("ascii")

    def __repr__(self) -> str:
        return f"Attachment(filename={self.filename!r}, mime_type={self.mime_type!r}, size={len(self.data)})"


# ---------------------------------------------------------------------------
# ImageInput
# ---------------------------------------------------------------------------


@dataclass
class ImageInput:
    """An image attachment for multimodal agent calls.

    Example::

        img = ImageInput.from_file("/path/to/screenshot.png")
        img_url = ImageInput.from_url("https://example.com/chart.png")
    """

    data: bytes | None = None
    url: str | None = None
    mime_type: str = "image/png"
    filename: str = ""

    @classmethod
    def from_file(cls, path: str | Path) -> "ImageInput":
        """Create an :class:`ImageInput` from a local image file.

        Args:
            path: Path to the image file.

        Raises:
            :class:`~openjiuwen.sdk.core.errors.SdkError`: If the MIME type is not a supported image type.
        """
        p = Path(path)
        mime, _ = mimetypes.guess_type(str(p))
        if mime is None:
            mime = "image/png"
        if mime not in _SUPPORTED_IMAGE_MIMES:
            raise SdkError(
                f"Unsupported image MIME type '{mime}'. "
                f"Supported: {sorted(_SUPPORTED_IMAGE_MIMES)}"
            )
        data = p.read_bytes()
        return cls(data=data, mime_type=mime, filename=p.name)

    @classmethod
    def from_url(cls, url: str) -> "ImageInput":
        """Create an :class:`ImageInput` from a remote URL.

        The image is not fetched eagerly — the URL is passed directly to the
        model's vision API.

        Args:
            url: HTTP(S) URL of the image.
        """
        mime, _ = mimetypes.guess_type(url)
        if mime is None or mime not in _SUPPORTED_IMAGE_MIMES:
            mime = "image/jpeg"
        return cls(url=url, mime_type=mime, filename=url.split("/")[-1][:64])

    def to_base64(self) -> str | None:
        """Return the image as a base64 string, or ``None`` if URL-based."""
        if self.data is None:
            return None
        return base64.b64encode(self.data).decode("ascii")

    def __repr__(self) -> str:
        if self.url:
            return f"ImageInput(url={self.url!r})"
        return f"ImageInput(filename={self.filename!r}, size={len(self.data or b'')})"


# ---------------------------------------------------------------------------
# AudioInput
# ---------------------------------------------------------------------------


@dataclass
class AudioInput:
    """An audio attachment for multimodal agent calls.

    Example::

        audio = AudioInput.from_file("/path/to/meeting.mp3")
    """

    data: bytes | None = None
    url: str | None = None
    mime_type: str = "audio/mpeg"
    filename: str = ""

    @classmethod
    def from_file(cls, path: str | Path) -> "AudioInput":
        """Create an :class:`AudioInput` from a local audio file.

        Args:
            path: Path to the audio file.

        Raises:
            :class:`~openjiuwen.sdk.core.errors.SdkError`: If the MIME type is not a supported audio type.
        """
        p = Path(path)
        mime, _ = mimetypes.guess_type(str(p))
        if mime is None:
            mime = "audio/mpeg"
        if mime not in _SUPPORTED_AUDIO_MIMES:
            raise SdkError(
                f"Unsupported audio MIME type '{mime}'. "
                f"Supported: {sorted(_SUPPORTED_AUDIO_MIMES)}"
            )
        data = p.read_bytes()
        return cls(data=data, mime_type=mime, filename=p.name)

    @classmethod
    def from_url(cls, url: str) -> "AudioInput":
        """Create an :class:`AudioInput` from a remote URL."""
        mime, _ = mimetypes.guess_type(url)
        if mime is None or mime not in _SUPPORTED_AUDIO_MIMES:
            mime = "audio/mpeg"
        return cls(url=url, mime_type=mime, filename=url.split("/")[-1][:64])

    def to_base64(self) -> str | None:
        if self.data is None:
            return None
        return base64.b64encode(self.data).decode("ascii")

    def __repr__(self) -> str:
        if self.url:
            return f"AudioInput(url={self.url!r})"
        return f"AudioInput(filename={self.filename!r}, size={len(self.data or b'')})"


# ---------------------------------------------------------------------------
# MultimodalAgent façade
# ---------------------------------------------------------------------------


class MultimodalAgent:
    """An agent configured for multimodal (vision / audio) inputs.

    Use :meth:`create` to construct.  Then call :meth:`run` with
    ``attachments=[...]``.

    Note:
        :class:`MultimodalAgent` wraps a standard
        :class:`~openjiuwen.sdk.core.agent.Agent` with multimodal configuration.
        Import it from here when you need explicit multimodal typing; otherwise
        ``Agent.create`` already accepts ``images=`` and ``audio=``.
    """

    def __init__(self, _agent: Any, *, vision_config: VisionModelConfig | None = None,
                 audio_config: AudioModelConfig | None = None) -> None:
        self._agent = _agent
        self._vision_config = vision_config
        self._audio_config = audio_config

    @classmethod
    async def create(
        cls,
        name: str,
        *,
        model: Any = None,
        vision_config: VisionModelConfig | None = None,
        audio_config: AudioModelConfig | None = None,
        tools: list[Any] | None = None,
        hooks: Any = None,
    ) -> "MultimodalAgent":
        """Create a multimodal agent.

        Args:
            name:          Agent name.
            model:         :class:`~openjiuwen.sdk.core.config.ModelConfig` (default from env).
            vision_config: Vision model configuration.
            audio_config:  Audio model configuration.
            tools:         Tool list.
            hooks:         Lifecycle hooks.

        Returns:
            A :class:`MultimodalAgent` ready for multimodal ``run()`` calls.
        """
        from openjiuwen.sdk.core.agent import Agent
        from openjiuwen.sdk.core.config import ModelConfig

        if model is None:
            model = ModelConfig.from_env()

        agent = await Agent.create(
            name,
            model=model,
            tools=tools or [],
            hooks=hooks,
        )
        return cls(agent, vision_config=vision_config, audio_config=audio_config)

    async def run(
        self,
        prompt: str,
        *,
        attachments: list[Attachment] | None = None,
        images: list[ImageInput] | None = None,
        audio: list[AudioInput] | None = None,
        session_id: str | None = None,
    ) -> Any:
        """Run the multimodal agent.

        Args:
            prompt:      The text prompt.
            attachments: Generic :class:`Attachment` objects.
            images:      Image inputs.
            audio:       Audio inputs.
            session_id:  Existing session to continue.

        Returns:
            :class:`~openjiuwen.sdk.core.agent.AgentResult`.
        """
        # Build augmented prompt with attachment context
        augmented = prompt
        if images:
            augmented += f"\n[{len(images)} image(s) attached]"
        if audio:
            augmented += f"\n[{len(audio)} audio file(s) attached]"
        if attachments:
            augmented += f"\n[{len(attachments)} attachment(s)]"

        return await self._agent.run(augmented, session_id=session_id)

    def __repr__(self) -> str:
        return f"MultimodalAgent(vision={self._vision_config}, audio={self._audio_config})"
