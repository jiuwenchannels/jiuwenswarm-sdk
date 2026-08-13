"""Unit tests for openjiuwen.sdk.multimodal — multimodal input types."""

from __future__ import annotations

import pytest

from openjiuwen.sdk.errors import SdkError
from openjiuwen.sdk.multimodal import (
    Attachment,
    AudioInput,
    AudioModelConfig,
    ImageInput,
    VisionModelConfig,
)


# ---------------------------------------------------------------------------
# ImageInput tests
# ---------------------------------------------------------------------------


def test_image_input_from_url():
    img = ImageInput.from_url("https://example.com/chart.png")
    assert img.url == "https://example.com/chart.png"
    assert img.data is None
    assert "png" in img.mime_type


def test_image_input_from_file_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        ImageInput.from_file(tmp_path / "nonexistent.png")


def test_image_input_from_file(tmp_path):
    img_path = tmp_path / "test.png"
    img_path.write_bytes(b"\x89PNG fake png data")
    img = ImageInput.from_file(img_path)
    assert img.data is not None
    assert img.mime_type == "image/png"
    assert img.filename == "test.png"


def test_image_input_from_file_unsupported_mime(tmp_path):
    doc_path = tmp_path / "document.docx"
    doc_path.write_bytes(b"PK fake docx")
    with pytest.raises(SdkError, match="Unsupported image MIME"):
        ImageInput.from_file(doc_path)


def test_image_input_to_base64(tmp_path):
    img_path = tmp_path / "pixel.png"
    img_path.write_bytes(b"fake png")
    img = ImageInput.from_file(img_path)
    b64 = img.to_base64()
    assert isinstance(b64, str)
    assert len(b64) > 0


def test_image_input_url_to_base64_returns_none():
    img = ImageInput.from_url("https://example.com/img.jpg")
    assert img.to_base64() is None


# ---------------------------------------------------------------------------
# AudioInput tests
# ---------------------------------------------------------------------------


def test_audio_input_from_file(tmp_path):
    audio_path = tmp_path / "clip.mp3"
    audio_path.write_bytes(b"fake mp3 data")
    audio = AudioInput.from_file(audio_path)
    assert audio.data is not None
    assert audio.mime_type == "audio/mpeg"


def test_audio_input_unsupported_mime(tmp_path):
    path = tmp_path / "video.mp4"
    path.write_bytes(b"fake mp4")
    with pytest.raises(SdkError, match="Unsupported audio MIME"):
        AudioInput.from_file(path)


def test_audio_input_from_url():
    audio = AudioInput.from_url("https://example.com/meeting.mp3")
    assert audio.url == "https://example.com/meeting.mp3"


# ---------------------------------------------------------------------------
# Attachment tests
# ---------------------------------------------------------------------------


def test_attachment_from_file_image(tmp_path):
    p = tmp_path / "img.png"
    p.write_bytes(b"fake png")
    att = Attachment.from_file(p)
    assert att.mime_type == "image/png"
    assert att.filename == "img.png"


def test_attachment_from_file_unsupported(tmp_path):
    p = tmp_path / "exe.exe"
    p.write_bytes(b"fake exe")
    with pytest.raises(SdkError, match="Unsupported MIME"):
        Attachment.from_file(p)


def test_attachment_to_base64(tmp_path):
    p = tmp_path / "doc.txt"
    p.write_bytes(b"hello world")
    att = Attachment.from_file(p)
    b64 = att.to_base64()
    import base64
    assert base64.b64decode(b64) == b"hello world"


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------


def test_vision_model_config_defaults():
    cfg = VisionModelConfig()
    assert cfg.model == "gpt-4o"


def test_audio_model_config_defaults():
    cfg = AudioModelConfig()
    assert cfg.model == "whisper-1"
