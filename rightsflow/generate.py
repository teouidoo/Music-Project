"""Eleven Music API wrapper with explicit mock mode and auditable manifests."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from . import __version__


class MissingCredentialsError(RuntimeError):
    """Raised when API generation is requested without credentials."""


@dataclass
class Track:
    track_id: str
    prompt: str
    length_ms: int
    mock: bool
    model_id: str = "music_v2"
    created_at: str = ""
    output_format: str = "mp3_48000_192"
    audio_path: str | None = None
    sha256: str | None = None
    audio_bytes: int = 0
    attribution_source: str = "none"
    note: str = ""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_request(prompt: str, length_ms: int, model_id: str) -> None:
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt must not be empty")
    if len(prompt) > 4100:
        raise ValueError("prompt must be 4,100 characters or fewer")
    if isinstance(length_ms, bool) or not isinstance(length_ms, int) or not 3_000 <= length_ms <= 600_000:
        raise ValueError("length_ms must be between 3,000 and 600,000")
    if model_id not in {"music_v1", "music_v2"}:
        raise ValueError("model_id must be music_v1 or music_v2")


def _mock_track(prompt: str, length_ms: int, index: int, model_id: str) -> Track:
    return Track(
        track_id=f"mock-{index:03d}-{uuid4().hex[:8]}",
        prompt=prompt,
        length_ms=length_ms,
        mock=True,
        model_id=model_id,
        created_at=_utc_now(),
        attribution_source="none",
        note="mock generation; no audio or attribution was produced",
    )


def generate_track(
    prompt: str,
    length_ms: int = 30_000,
    mock: bool = False,
    out_dir: str = "examples/generated",
    index: int = 1,
    model_id: str = "music_v2",
    client=None,
    output_format: str = "mp3_48000_192",
) -> Track:
    """Generate one track, or return a clearly labeled mock.

    Real mode fails closed when credentials are absent. ``client`` exists for
    offline contract tests and does not weaken credential handling in normal use.
    """
    _validate_request(prompt, length_ms, model_id)
    if mock:
        return _mock_track(prompt, length_ms, index, model_id)

    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if client is None and not api_key:
        raise MissingCredentialsError(
            "ELEVENLABS_API_KEY is not set; pass --mock for an explicit offline run"
        )
    if client is None:
        try:
            from elevenlabs.client import ElevenLabs
        except ImportError as exc:
            raise RuntimeError(
                "The 'elevenlabs' package is required: pip install 'rightsflow[eleven]'"
            ) from exc
        client = ElevenLabs(api_key=api_key)

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    track_id = f"eleven-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid4().hex[:8]}"
    audio_path = out / f"{track_id}.mp3"
    fd, temporary = tempfile.mkstemp(prefix=f".{track_id}-", suffix=".tmp", dir=out)
    hasher = hashlib.sha256()
    byte_count = 0
    try:
        audio = client.music.compose(
            prompt=prompt,
            music_length_ms=length_ms,
            model_id=model_id,
            output_format=output_format,
        )
        chunks = (bytes(audio),) if isinstance(audio, (bytes, bytearray)) else audio
        with os.fdopen(fd, "wb") as handle:
            fd = -1
            for chunk in chunks:
                if not isinstance(chunk, (bytes, bytearray)):
                    raise RuntimeError("Eleven Music API returned a non-bytes audio chunk")
                data = bytes(chunk)
                handle.write(data)
                hasher.update(data)
                byte_count += len(data)
            if byte_count == 0:
                raise RuntimeError("Eleven Music API returned empty audio")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, audio_path)
    except Exception:
        if fd >= 0:
            os.close(fd)
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise

    return Track(
        track_id=track_id,
        prompt=prompt,
        length_ms=length_ms,
        mock=False,
        model_id=model_id,
        created_at=_utc_now(),
        output_format=output_format,
        audio_path=str(audio_path),
        sha256=hasher.hexdigest(),
        audio_bytes=byte_count,
        attribution_source="none",
        note="generated via Eleven Music API; API does not supply rights-holder attribution",
    )


def save_manifest(tracks: list[Track], path: str = "examples/generated/manifest.json") -> str:
    """Atomically save a versioned generation manifest."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        sdk_version = importlib.metadata.version("elevenlabs")
    except importlib.metadata.PackageNotFoundError:
        sdk_version = None
    document = {
        "schema": "rightsflow.manifest/1",
        "generated_at": _utc_now(),
        "rightsflow_version": __version__,
        "elevenlabs_sdk_version": sdk_version,
        "attribution_notice": "Per-output rights-holder attribution is not supplied by this integration.",
        "tracks": [asdict(track) for track in tracks],
    }
    fd, temporary = tempfile.mkstemp(prefix=f".{p.name}-", suffix=".tmp", dir=p.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(document, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, p)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
    return str(p)


def load_manifest(path: str) -> dict:
    with open(path, encoding="utf-8") as handle:
        document = json.load(handle)
    if isinstance(document, list):
        return {
            "schema": "rightsflow.manifest/0",
            "generated_at": None,
            "rightsflow_version": "0.1.x",
            "attribution_notice": "Legacy manifest; no attribution metadata is available.",
            "tracks": document,
        }
    if document.get("schema") != "rightsflow.manifest/1":
        raise ValueError("unsupported manifest schema")
    return document
