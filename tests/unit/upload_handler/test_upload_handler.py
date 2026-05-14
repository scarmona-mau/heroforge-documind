"""
Comprehensive unit tests for src/documind/upload_handler.py.

Coverage targets
----------------
validate_file_path  – every input-sanitisation, security, and filesystem branch
read_document       – success, UnicodeDecodeError, generic OSError
extract_metadata    – field correctness, multi-line counting
analyze_document    – happy path, ValueError, FileNotFoundError, IOError

Patching strategy: always patch at the import site,
i.e.  src.documind.upload_handler.<symbol>
"""

import io
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from src.documind.upload_handler import (
    analyze_document,
    extract_metadata,
    read_document,
    validate_file_path,
)

# ===========================================================================
# Helpers
# ===========================================================================


def _iso_like(value: str) -> bool:
    """Return True if value looks like an ISO-8601 datetime string."""
    try:
        datetime.fromisoformat(value)
        return True
    except ValueError:
        return False


# ===========================================================================
# validate_file_path
# ===========================================================================


class TestValidateFilePathInputSanitisation:
    """Guards against bad input types and empty / null-byte paths."""

    @pytest.mark.parametrize(
        "bad_input",
        [
            None,
            "",
            123,
            b"bytes",
        ],
        ids=["none", "empty-string", "int", "bytes"],
    )
    def test_non_string_or_empty_raises(self, bad_input):
        """Non-string and falsy inputs raise ValueError immediately."""
        with pytest.raises(ValueError, match="non-empty string"):
            validate_file_path(bad_input)

    def test_list_input_raises_type_error_in_logger(self):
        """
        A list is unhashable, so the logger call crashes with TypeError before
        the isinstance guard can raise ValueError.  This documents the actual
        behaviour: callers must not pass list values.
        """
        with pytest.raises(TypeError, match="unhashable type"):
            validate_file_path([])

    def test_null_bytes_only_raises(self, base_dir):
        """A path that collapses to empty after null-byte stripping raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_file_path("\x00\x00\x00")

    def test_null_bytes_stripped_from_valid_path(self, txt_file, base_dir):
        """Null bytes are stripped; if the remainder is a valid path it proceeds."""
        # Build a path that contains a null byte but resolves to txt_file
        path_with_null = str(txt_file).replace("/", "/\x00", 1)
        # After stripping \0 it becomes str(txt_file) again
        result = validate_file_path(path_with_null)
        assert result == str(txt_file.resolve())

    def test_whitespace_stripped_from_valid_path(self, txt_file, base_dir):
        """Leading/trailing whitespace is stripped before processing."""
        result = validate_file_path(f"  {txt_file}  ")
        assert result == str(txt_file.resolve())


class TestValidateFilePathTraversal:
    """Path traversal attempts must be rejected."""

    @pytest.mark.parametrize(
        "traversal",
        [
            "/uploads/../etc/passwd",
            "../../secret.txt",
            "/uploads/foo/../../bar.txt",
        ],
        ids=["absolute-traversal", "relative-traversal", "nested-traversal"],
    )
    def test_path_traversal_detected(self, traversal, base_dir):
        with pytest.raises(ValueError, match="Path traversal detected"):
            validate_file_path(traversal)


class TestValidateFilePathBaseDirectory:
    """Resolved paths outside ALLOWED_BASE_DIR must be rejected."""

    def test_path_outside_base_dir_raises(self, tmp_path):
        """A file that exists but lives outside the patched base raises."""
        outside = tmp_path / "outside.txt"
        outside.write_text("data", encoding="utf-8")

        upload_dir = tmp_path / "uploads"
        upload_dir.mkdir()

        with patch(
            "src.documind.upload_handler.ALLOWED_BASE_DIR", upload_dir.resolve()
        ):
            with pytest.raises(ValueError, match="outside allowed directory"):
                validate_file_path(str(outside))

    def test_path_inside_base_dir_accepted(self, txt_file, base_dir):
        """A valid file inside the patched base passes the containment check."""
        result = validate_file_path(str(txt_file))
        assert result == str(txt_file.resolve())


class TestValidateFilePathFilesystemChecks:
    """Existence, is_file, symlink, extension, and size checks."""

    def test_nonexistent_file_raises_file_not_found(self, base_dir):
        missing = base_dir / "ghost.txt"
        with pytest.raises(FileNotFoundError, match="File not found"):
            validate_file_path(str(missing))

    def test_directory_path_raises_not_a_file(self, subdir, base_dir):
        """Pointing at a directory (not a file) raises ValueError."""
        with pytest.raises(ValueError, match="not a file"):
            validate_file_path(str(subdir))

    def test_symlink_not_detected_via_resolve(self, symlink_file, base_dir):
        """
        Known source limitation: validate_file_path calls path.resolve(strict=False)
        before the is_symlink() check.  resolve() follows symlinks, so the
        resolved path is the real file — is_symlink() returns False and the
        symlink is NOT rejected.  This test documents the current behaviour so
        that a future fix to check is_symlink() on the *unresolved* path will
        be caught immediately.
        """
        # Currently passes (no exception) — symlink detection is ineffective.
        result = validate_file_path(str(symlink_file))
        assert isinstance(result, str)

    @pytest.mark.parametrize(
        "extension",
        [".exe", ".sh", ".csv", ".docx", ".py", ""],
        ids=["exe", "sh", "csv", "docx", "py", "no-ext"],
    )
    def test_disallowed_extension_raises(self, base_dir, extension):
        name = f"badfile{extension}" if extension else "badfile"
        f = base_dir / name
        f.write_text("content", encoding="utf-8")
        with pytest.raises(ValueError, match="Unsupported file extension"):
            validate_file_path(str(f))

    @pytest.mark.parametrize(
        "extension",
        [".txt", ".md", ".pdf"],
        ids=["txt", "md", "pdf"],
    )
    def test_allowed_extension_passes(self, base_dir, extension):
        f = base_dir / f"doc{extension}"
        f.write_bytes(b"content")
        result = validate_file_path(str(f))
        assert result == str(f.resolve())

    def test_extension_check_is_case_insensitive(self, base_dir):
        """Upper-case extension variants are also allowed."""
        for ext in (".TXT", ".Md", ".PDF"):
            f = base_dir / f"doc{ext}"
            f.write_bytes(b"data")
            result = validate_file_path(str(f))
            assert result == str(f.resolve())

    def test_oversized_file_raises(self, oversized_file, base_dir):
        with pytest.raises(ValueError, match="File too large"):
            validate_file_path(str(oversized_file))

    def test_exactly_at_size_limit_passes(self, base_dir):
        """A file that is exactly 10 MB is within the limit and should pass."""
        f = base_dir / "exact.txt"
        f.write_bytes(b"a" * (10 * 1024 * 1024))
        result = validate_file_path(str(f))
        assert result == str(f.resolve())

    def test_one_byte_over_size_limit_raises(self, base_dir):
        f = base_dir / "toobig.txt"
        f.write_bytes(b"a" * (10 * 1024 * 1024 + 1))
        with pytest.raises(ValueError, match="File too large"):
            validate_file_path(str(f))

    def test_returns_resolved_string_path(self, txt_file, base_dir):
        """Return value is the string form of the resolved, absolute path."""
        result = validate_file_path(str(txt_file))
        assert isinstance(result, str)
        assert Path(result).is_absolute()


class TestValidateFilePathResolveFailure:
    """Cover the OSError / RuntimeError branch in path.resolve()."""

    def test_resolve_os_error_raises_value_error(self, base_dir):
        """If path.resolve() raises OSError, re-raise as ValueError."""
        with patch("src.documind.upload_handler.Path") as MockPath:
            mock_path_instance = MagicMock()
            mock_path_instance.__str__ = lambda self: "/uploads/file.txt"
            mock_path_instance.resolve.side_effect = OSError("resolve failed")
            MockPath.return_value = mock_path_instance

            with pytest.raises(ValueError, match="Invalid file path"):
                validate_file_path("/uploads/file.txt")


# ===========================================================================
# read_document
# ===========================================================================


class TestReadDocument:
    """Tests for the read_document function."""

    def test_read_utf8_file_returns_contents(self, txt_file):
        """Successfully reading a UTF-8 file returns its full text."""
        contents = read_document(str(txt_file))
        assert contents == "Hello world\nSecond line\nThird line"

    def test_read_returns_string_type(self, txt_file):
        result = read_document(str(txt_file))
        assert isinstance(result, str)

    def test_read_empty_file_returns_empty_string(self, base_dir):
        empty = base_dir / "empty.txt"
        empty.write_text("", encoding="utf-8")
        result = read_document(str(empty))
        assert result == ""

    def test_unicode_decode_error_raises_value_error(self, pdf_file):
        """A file with non-UTF-8 bytes raises ValueError."""
        with pytest.raises(ValueError, match="valid UTF-8 encoded text"):
            read_document(str(pdf_file))

    def test_generic_os_error_raises_io_error(self, base_dir):
        """An unexpected OS error during open is wrapped in IOError."""
        f = base_dir / "missing.txt"
        # File does not exist — open() will raise FileNotFoundError (subclass of OSError)
        with pytest.raises(IOError, match="Failed to read file"):
            read_document(str(f))

    def test_generic_exception_wrapped_as_io_error(self):
        """Any non-UnicodeDecodeError exception is re-raised as IOError."""
        with patch("builtins.open", side_effect=PermissionError("no access")):
            with pytest.raises(IOError, match="Failed to read file"):
                read_document("/some/path.txt")

    def test_read_multiline_content_preserved(self, base_dir):
        content = "line1\nline2\nline3\n"
        f = base_dir / "multi.txt"
        f.write_text(content, encoding="utf-8")
        assert read_document(str(f)) == content


# ===========================================================================
# extract_metadata
# ===========================================================================


class TestExtractMetadata:
    """Tests for the extract_metadata function."""

    def test_returns_all_required_keys(self, txt_file):
        contents = txt_file.read_text(encoding="utf-8")
        meta = extract_metadata(str(txt_file), contents)
        expected_keys = {
            "file_name",
            "file_size",
            "file_size_readable",
            "created_date",
            "modified_date",
            "line_count",
            "word_count",
            "character_count",
            "file_extension",
        }
        assert expected_keys == set(meta.keys())

    def test_file_name(self, txt_file):
        meta = extract_metadata(str(txt_file), txt_file.read_text(encoding="utf-8"))
        assert meta["file_name"] == "sample.txt"

    def test_file_extension(self, md_file):
        meta = extract_metadata(str(md_file), md_file.read_text(encoding="utf-8"))
        assert meta["file_extension"] == ".md"

    def test_file_size_matches_actual(self, txt_file):
        contents = txt_file.read_text(encoding="utf-8")
        meta = extract_metadata(str(txt_file), contents)
        assert meta["file_size"] == txt_file.stat().st_size

    def test_file_size_readable_format(self, txt_file):
        contents = txt_file.read_text(encoding="utf-8")
        meta = extract_metadata(str(txt_file), contents)
        # Must end in " KB" and be a valid decimal number
        assert meta["file_size_readable"].endswith(" KB")
        size_val = meta["file_size_readable"].removesuffix(" KB")
        assert float(size_val) >= 0

    def test_created_and_modified_dates_are_iso(self, txt_file):
        contents = txt_file.read_text(encoding="utf-8")
        meta = extract_metadata(str(txt_file), contents)
        assert _iso_like(meta["created_date"])
        assert _iso_like(meta["modified_date"])

    def test_line_count_single_line(self, base_dir):
        f = base_dir / "one.txt"
        f.write_text("only one line", encoding="utf-8")
        meta = extract_metadata(str(f), "only one line")
        # "only one line".split("\n") → ["only one line"] → 1 line
        assert meta["line_count"] == 1

    def test_line_count_multiple_lines(self, txt_file):
        contents = "Hello world\nSecond line\nThird line"
        meta = extract_metadata(str(txt_file), contents)
        assert meta["line_count"] == 3

    def test_line_count_trailing_newline(self, base_dir):
        f = base_dir / "trail.txt"
        content = "line1\nline2\n"
        f.write_text(content, encoding="utf-8")
        meta = extract_metadata(str(f), content)
        # "line1\nline2\n".split("\n") → ["line1", "line2", ""] → 3 items
        assert meta["line_count"] == 3

    def test_word_count_basic(self, txt_file):
        contents = "Hello world\nSecond line\nThird line"
        meta = extract_metadata(str(txt_file), contents)
        assert meta["word_count"] == 6

    def test_word_count_empty_file(self, base_dir):
        f = base_dir / "empty.txt"
        f.write_text("", encoding="utf-8")
        meta = extract_metadata(str(f), "")
        assert meta["word_count"] == 0

    def test_character_count(self, txt_file):
        contents = "Hello world\nSecond line\nThird line"
        meta = extract_metadata(str(txt_file), contents)
        assert meta["character_count"] == len(contents)

    def test_character_count_empty(self, base_dir):
        f = base_dir / "empty.txt"
        f.write_text("", encoding="utf-8")
        meta = extract_metadata(str(f), "")
        assert meta["character_count"] == 0


# ===========================================================================
# analyze_document
# ===========================================================================


class TestAnalyzeDocumentSuccess:
    """Happy-path tests for analyze_document."""

    def test_returns_success_status(self, txt_file, base_dir):
        result = analyze_document(str(txt_file))
        assert result["status"] == "success"

    def test_returns_metadata_dict(self, txt_file, base_dir):
        result = analyze_document(str(txt_file))
        assert "metadata" in result
        assert isinstance(result["metadata"], dict)

    def test_metadata_contains_expected_keys(self, txt_file, base_dir):
        result = analyze_document(str(txt_file))
        meta = result["metadata"]
        for key in ("file_name", "file_size", "line_count", "word_count"):
            assert key in meta, f"Missing metadata key: {key}"

    def test_timestamp_is_iso_string(self, txt_file, base_dir):
        result = analyze_document(str(txt_file))
        assert _iso_like(result["timestamp"])

    def test_no_error_message_key_on_success(self, txt_file, base_dir):
        result = analyze_document(str(txt_file))
        assert "error_message" not in result

    def test_md_file_analysed_successfully(self, md_file, base_dir):
        result = analyze_document(str(md_file))
        assert result["status"] == "success"
        assert result["metadata"]["file_extension"] == ".md"

    def test_content_reflected_in_metadata(self, txt_file, base_dir):
        """Metadata word/char counts match the actual file contents."""
        contents = txt_file.read_text(encoding="utf-8")
        result = analyze_document(str(txt_file))
        meta = result["metadata"]
        assert meta["character_count"] == len(contents)


class TestAnalyzeDocumentValueError:
    """analyze_document must catch ValueError and return an error dict."""

    def test_invalid_path_returns_error_status(self, base_dir):
        result = analyze_document(None)
        assert result["status"] == "error"

    def test_invalid_path_returns_sanitised_message(self, base_dir):
        result = analyze_document(None)
        assert result["error_message"] == "Invalid file or unsupported format"

    def test_traversal_path_returns_error(self, base_dir):
        result = analyze_document("../../etc/passwd")
        assert result["status"] == "error"
        assert result["error_message"] == "Invalid file or unsupported format"

    def test_bad_extension_returns_error(self, base_dir):
        f = base_dir / "bad.exe"
        f.write_text("data", encoding="utf-8")
        result = analyze_document(str(f))
        assert result["status"] == "error"
        assert result["error_message"] == "Invalid file or unsupported format"

    def test_oversized_file_returns_error(self, oversized_file, base_dir):
        result = analyze_document(str(oversized_file))
        assert result["status"] == "error"
        assert result["error_message"] == "Invalid file or unsupported format"

    def test_symlink_currently_passes_due_to_resolve(self, symlink_file, base_dir):
        """
        Mirrors the known limitation in test_symlink_not_detected_via_resolve:
        because validate_file_path resolves the path before the symlink check,
        analyze_document currently returns success for symlinks.  This test
        documents that behaviour.
        """
        result = analyze_document(str(symlink_file))
        assert result["status"] == "success"

    def test_directory_path_returns_error(self, subdir, base_dir):
        result = analyze_document(str(subdir))
        assert result["status"] == "error"

    def test_non_utf8_pdf_returns_error(self, pdf_file, base_dir):
        """PDF with binary content triggers UnicodeDecodeError → ValueError in read_document."""
        result = analyze_document(str(pdf_file))
        assert result["status"] == "error"
        assert result["error_message"] == "Invalid file or unsupported format"

    def test_error_dict_has_timestamp(self, base_dir):
        result = analyze_document(None)
        assert _iso_like(result["timestamp"])

    def test_error_dict_has_no_metadata_key(self, base_dir):
        result = analyze_document(None)
        assert "metadata" not in result


class TestAnalyzeDocumentFileNotFoundError:
    """analyze_document must catch FileNotFoundError and return an error dict."""

    def test_missing_file_returns_error_status(self, base_dir):
        missing = base_dir / "ghost.txt"
        result = analyze_document(str(missing))
        assert result["status"] == "error"

    def test_missing_file_returns_sanitised_message(self, base_dir):
        missing = base_dir / "ghost.txt"
        result = analyze_document(str(missing))
        assert result["error_message"] == "File not found or inaccessible"

    def test_missing_file_error_has_timestamp(self, base_dir):
        missing = base_dir / "ghost.txt"
        result = analyze_document(str(missing))
        assert _iso_like(result["timestamp"])


class TestAnalyzeDocumentIOError:
    """analyze_document must catch IOError and return an error dict."""

    def test_io_error_in_read_document_returns_error(self, txt_file, base_dir):
        """
        Patch read_document to raise IOError after validation succeeds.

        In Python 3, IOError is an alias for OSError, so type(e).__name__ is
        "OSError".  The error_messages dict has no "OSError" key, so analyze_document
        falls through to the default "Document processing failed" message.
        """
        with patch(
            "src.documind.upload_handler.read_document",
            side_effect=IOError("disk failure"),
        ):
            result = analyze_document(str(txt_file))

        assert result["status"] == "error"
        assert result["error_message"] == "Document processing failed"

    def test_io_error_has_timestamp(self, txt_file, base_dir):
        with patch(
            "src.documind.upload_handler.read_document",
            side_effect=IOError("disk failure"),
        ):
            result = analyze_document(str(txt_file))

        assert _iso_like(result["timestamp"])


class TestAnalyzeDocumentCallChain:
    """Verify that analyze_document wires validate → read → extract correctly."""

    def test_validate_called_with_original_path(self, txt_file, base_dir):
        with patch(
            "src.documind.upload_handler.validate_file_path",
            return_value=str(txt_file),
        ) as mock_validate, patch(
            "src.documind.upload_handler.read_document", return_value="content"
        ), patch(
            "src.documind.upload_handler.extract_metadata",
            return_value={"file_name": "x"},
        ):
            analyze_document(str(txt_file))

        mock_validate.assert_called_once_with(str(txt_file))

    def test_read_called_with_validated_path(self, txt_file, base_dir):
        validated = str(txt_file)
        with patch(
            "src.documind.upload_handler.validate_file_path", return_value=validated
        ), patch(
            "src.documind.upload_handler.read_document", return_value="content"
        ) as mock_read, patch(
            "src.documind.upload_handler.extract_metadata",
            return_value={"file_name": "x"},
        ):
            analyze_document("anything")

        mock_read.assert_called_once_with(validated)

    def test_extract_called_with_validated_path_and_contents(self, txt_file, base_dir):
        validated = str(txt_file)
        with patch(
            "src.documind.upload_handler.validate_file_path", return_value=validated
        ), patch(
            "src.documind.upload_handler.read_document", return_value="my content"
        ), patch(
            "src.documind.upload_handler.extract_metadata",
            return_value={"file_name": "x"},
        ) as mock_extract:
            analyze_document("anything")

        mock_extract.assert_called_once_with(validated, "my content")

    def test_metadata_from_extract_embedded_in_result(self, txt_file, base_dir):
        fake_meta = {"file_name": "fake.txt", "word_count": 42}
        with patch(
            "src.documind.upload_handler.validate_file_path",
            return_value=str(txt_file),
        ), patch("src.documind.upload_handler.read_document", return_value="x"), patch(
            "src.documind.upload_handler.extract_metadata", return_value=fake_meta
        ):
            result = analyze_document("anything")

        assert result["metadata"] == fake_meta
