import hashlib
import pytest

from rightsflow.generate import MissingCredentialsError, generate_track, load_manifest, save_manifest


class FakeMusic:
    def __init__(self, payload=b"audio-data"):
        self.payload = payload
        self.calls = []

    def compose(self, **kwargs):
        self.calls.append(kwargs)
        return iter([self.payload[:5], self.payload[5:]])


class FakeClient:
    def __init__(self, payload=b"audio-data"):
        self.music = FakeMusic(payload)


def test_api_mode_fails_closed_without_key(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    with pytest.raises(MissingCredentialsError, match="--mock"):
        generate_track("test music")


def test_mock_is_explicit_and_unique():
    first = generate_track("test music", mock=True)
    second = generate_track("test music", mock=True)
    assert first.mock and second.mock
    assert first.track_id != second.track_id
    assert first.attribution_source == "none"


def test_fake_api_writes_atomic_audio_and_provenance(tmp_path):
    client = FakeClient()
    track = generate_track("test music", client=client, out_dir=str(tmp_path))
    assert not track.mock
    assert track.model_id == "music_v2"
    assert track.audio_bytes == len(b"audio-data")
    assert track.sha256 == hashlib.sha256(b"audio-data").hexdigest()
    assert client.music.calls[0]["model_id"] == "music_v2"
    assert not list(tmp_path.glob("*.tmp"))

    manifest_path = save_manifest([track], str(tmp_path / "manifest.json"))
    manifest = load_manifest(manifest_path)
    assert manifest["schema"] == "rightsflow.manifest/1"
    assert manifest["tracks"][0]["track_id"] == track.track_id
    assert "not supplied" in manifest["attribution_notice"]
    assert not list(tmp_path.glob("*.tmp"))


def test_empty_api_response_leaves_no_file(tmp_path):
    with pytest.raises(RuntimeError, match="empty audio"):
        generate_track("test music", client=FakeClient(b""), out_dir=str(tmp_path))
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("length", [2999, 600001])
def test_duration_is_validated(length):
    with pytest.raises(ValueError, match="length_ms"):
        generate_track("test music", length_ms=length, mock=True)


def test_legacy_manifest_is_loaded_with_explicit_schema(tmp_path):
    path = tmp_path / "legacy.json"
    path.write_text('[{"track_id":"old-1"}]', encoding="utf-8")
    manifest = load_manifest(str(path))
    assert manifest["schema"] == "rightsflow.manifest/0"
    assert manifest["tracks"][0]["track_id"] == "old-1"
