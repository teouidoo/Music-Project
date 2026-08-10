"""Eleven Music API wrapper.

Real mode uses the official `elevenlabs` SDK and the ELEVENLABS_API_KEY
environment variable (never a stored key, never a hardcoded key).
Mock mode fabricates track metadata so the economics pipeline runs
end-to-end without credentials — every mock record is labeled as such.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class Track:
    track_id: str
    prompt: str
    length_ms: int
    mock: bool
    audio_path: str | None = None
    note: str = ""


def _mock_track(prompt: str, length_ms: int, index: int) -> Track:
    return Track(
        track_id=f"mock-{index:03d}",
        prompt=prompt,
        length_ms=length_ms,
        mock=True,
        note="mock generation - run with ELEVENLABS_API_KEY set for real output",
    )


def generate_track(
    prompt: str,
    length_ms: int = 30_000,
    mock: bool = False,
    out_dir: str = "examples/generated",
    index: int = 1,
) -> Track:
    """Generate one track via the Eleven Music API, or a labeled mock."""
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if mock or not api_key:
        return _mock_track(prompt, length_ms, index)

    try:
        from elevenlabs.client import ElevenLabs
    except ImportError as e:
        raise RuntimeError(
            "The 'elevenlabs' package is required for real generation: pip install elevenlabs"
        ) from e

    client = ElevenLabs(api_key=api_key)
    audio = client.music.compose(prompt=prompt, music_length_ms=length_ms)

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    track_id = f"eleven-{int(time.time())}-{index:03d}"
    audio_path = out / f"{track_id}.mp3"
    with open(audio_path, "wb") as f:
        if isinstance(audio, (bytes, bytearray)):
            f.write(audio)
        else:  # SDK returns an iterator of chunks
            for chunk in audio:
                f.write(chunk)

    return Track(
        track_id=track_id,
        prompt=prompt,
        length_ms=length_ms,
        mock=False,
        audio_path=str(audio_path),
        note="generated via Eleven Music API",
    )


def save_manifest(tracks: list[Track], path: str = "examples/generated/manifest.json"):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump([asdict(t) for t in tracks], f, indent=2)
    return str(p)
