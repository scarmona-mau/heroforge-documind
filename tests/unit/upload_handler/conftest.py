"""
Shared fixtures for upload_handler unit tests.

All file/directory operations use pytest's `tmp_path` fixture so that every
test gets an isolated, temporary directory that is cleaned up automatically.
UPLOAD_BASE_DIR is monkey-patched to point at that tmp_path so that the
path-containment check inside validate_file_path exercises real Path logic
without touching the workspace's real uploads/ folder.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Base-directory fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def base_dir(tmp_path):
    """
    A temporary uploads base directory.

    Patches the module-level ALLOWED_BASE_DIR constant used by validate_file_path
    so that every test works against an isolated, real directory tree.
    """
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    with patch("src.documind.upload_handler.ALLOWED_BASE_DIR", upload_dir.resolve()):
        yield upload_dir


# ---------------------------------------------------------------------------
# Convenience file fixtures (all located inside base_dir)
# ---------------------------------------------------------------------------


@pytest.fixture()
def txt_file(base_dir):
    """A valid UTF-8 .txt file inside the allowed base directory."""
    f = base_dir / "sample.txt"
    f.write_text("Hello world\nSecond line\nThird line", encoding="utf-8")
    return f


@pytest.fixture()
def md_file(base_dir):
    """A valid UTF-8 .md file inside the allowed base directory."""
    f = base_dir / "sample.md"
    f.write_text("# Heading\n\nSome content here.", encoding="utf-8")
    return f


@pytest.fixture()
def pdf_file(base_dir):
    """
    A stub .pdf file (binary bytes that are not valid UTF-8).

    validate_file_path allows .pdf by extension; read_document will reject it
    with UnicodeDecodeError, which is the behaviour being tested.
    """
    f = base_dir / "sample.pdf"
    # Write raw bytes: not valid UTF-8 so read_document raises UnicodeDecodeError
    f.write_bytes(b"%PDF-1.4 \xff\xfe binary garbage")
    return f


@pytest.fixture()
def oversized_file(base_dir):
    """A .txt file whose size exceeds the 10 MB limit."""
    f = base_dir / "big.txt"
    # 10 MB + 1 byte
    f.write_bytes(b"x" * (10 * 1024 * 1024 + 1))
    return f


@pytest.fixture()
def symlink_file(base_dir, txt_file):
    """A symbolic link pointing at txt_file, located inside the allowed dir."""
    link = base_dir / "link.txt"
    link.symlink_to(txt_file)
    return link


@pytest.fixture()
def subdir(base_dir):
    """A real subdirectory inside the allowed base directory."""
    d = base_dir / "subdir"
    d.mkdir()
    return d
