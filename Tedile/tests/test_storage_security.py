import io
import os
from types import SimpleNamespace

import pytest

from app.services.storage_service import StorageService


def make_upload(filename):
    stream = io.BytesIO(b"content")
    return SimpleNamespace(
        filename=filename,
        content_type="text/plain",
        seek=stream.seek,
        read=stream.read,
    )


@pytest.mark.parametrize(
    "filename,record_id",
    [
        ("report.txt", "record-1"),
        ("nested-report.txt", "nested-record"),
        ("../outside.txt", "record-2"),
        ("/absolute.txt", "record-3"),
        ("safe.txt", "../record-4"),
        ("../../outside.txt", "record-5"),
    ],
)
def test_local_upload_stays_inside_storage_root(tmp_path, monkeypatch, filename, record_id):
    monkeypatch.chdir(tmp_path)
    service = StorageService()

    service.upload_file(make_upload(filename), "documents", record_id, filename)

    upload_root = (tmp_path / "instance" / "uploads").resolve()
    files = [path for path in upload_root.rglob("*") if path.is_file()]
    assert files
    assert all(os.path.commonpath([str(upload_root), str(path.resolve())]) == str(upload_root) for path in files)


def test_local_upload_rejects_symlink_record_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    upload_root = tmp_path / "instance" / "uploads"
    upload_root.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (upload_root / "record-1").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="Invalid file path"):
        StorageService().upload_file(make_upload("safe.txt"), "documents", "record-1", "safe.txt")

    assert not (outside / "safe.txt").exists()
