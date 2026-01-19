"""
DocuMind Document Upload Handler
Demonstrates Skills, Subagents, and Hooks integration
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define allowed base directory for uploads
# In production, this should be configurable via environment variable
ALLOWED_BASE_DIR = Path(
    os.getenv("UPLOAD_BASE_DIR", "/workspaces/heroforge-documind/uploads")
).resolve()


def validate_file_path(file_path):
    """
    Validates that file path is safe and exists.

    Security checks:
    - Input sanitization (null bytes, malformed paths)
    - Path traversal prevention
    - Base directory validation
    - Symlink detection
    - File extension whitelist
    - File size limits
    """
    logger.info(f"Validating file path (hash: {hash(file_path)})")

    # Sanitize input - remove null bytes and strip whitespace
    if not file_path or not isinstance(file_path, str):
        logger.warning("Invalid file path type provided")
        raise ValueError("File path must be a non-empty string")

    file_path = str(file_path).replace("\0", "").strip()

    if not file_path:
        logger.warning("Empty file path after sanitization")
        raise ValueError("File path cannot be empty")

    # Convert to Path object for safer handling
    try:
        path = Path(file_path)
    except (ValueError, TypeError) as e:
        logger.warning(f"Invalid path format: {hash(file_path)}")
        raise ValueError("Invalid file path format") from e

    # Check for path traversal attempts
    if ".." in str(file_path):
        logger.warning(f"Path traversal attempt detected: {hash(file_path)}")
        raise ValueError("Path traversal detected in file path")

    # Resolve to absolute path
    try:
        resolved_path = path.resolve(strict=False)
    except (OSError, RuntimeError) as e:
        logger.error(f"Failed to resolve path: {hash(file_path)}")
        raise ValueError("Invalid file path") from e

    # Ensure resolved path is within allowed base directory
    try:
        # Create base directory if it doesn't exist
        ALLOWED_BASE_DIR.mkdir(parents=True, exist_ok=True)
        resolved_path.relative_to(ALLOWED_BASE_DIR)
    except ValueError:
        logger.warning(
            f"Path outside allowed directory: {hash(file_path)} "
            f"(base: {ALLOWED_BASE_DIR})"
        )
        raise ValueError("File path outside allowed directory")

    # Validate file exists
    if not resolved_path.exists():
        logger.info(f"File not found: {hash(file_path)}")
        raise FileNotFoundError("File not found")

    if not resolved_path.is_file():
        logger.warning(f"Path is not a file: {hash(file_path)}")
        raise ValueError("Path is not a file")

    # Check for symlinks (security risk)
    if resolved_path.is_symlink():
        logger.warning(f"Symlink detected: {hash(file_path)}")
        raise ValueError("Symbolic links are not allowed")

    # Validate file extension
    allowed_extensions = {".txt", ".md", ".pdf"}
    if resolved_path.suffix.lower() not in allowed_extensions:
        logger.warning(
            f"Unsupported file extension: {resolved_path.suffix} "
            f"for path {hash(file_path)}"
        )
        raise ValueError(
            f"Unsupported file extension. "
            f"Allowed extensions: {', '.join(allowed_extensions)}"
        )

    # Check file size (limit to 10MB)
    max_size = 10 * 1024 * 1024  # 10MB in bytes
    file_size = resolved_path.stat().st_size
    if file_size > max_size:
        logger.warning(f"File too large: {file_size} bytes for path {hash(file_path)}")
        raise ValueError(
            f"File too large. Maximum allowed: {max_size // (1024*1024)}MB"
        )

    logger.info(f"File path validation successful: {hash(file_path)}")
    return str(resolved_path)


def read_document(file_path):
    """
    Reads document contents safely.

    Security: Only accepts UTF-8 encoded text files.
    Binary files and other encodings are rejected to prevent:
    - Reading of binary executables
    - Exposure of compiled code
    - Embedded secrets in binary formats
    """
    logger.info(f"Reading document: {hash(file_path)}")

    try:
        # Only support UTF-8 encoding for security
        with open(file_path, "r", encoding="utf-8") as f:
            contents = f.read()

        logger.info(
            f"Successfully read document: {hash(file_path)} "
            f"({len(contents)} characters)"
        )
        return contents

    except UnicodeDecodeError as e:
        logger.warning(f"Invalid UTF-8 encoding in file: {hash(file_path)}")
        raise ValueError("File must be valid UTF-8 encoded text") from e
    except Exception as e:
        logger.error(f"Failed to read file: {hash(file_path)} - {type(e).__name__}")
        raise IOError("Failed to read file") from e


def extract_metadata(file_path, contents):
    """
    Extracts metadata from document.

    TODO: Extract:
    - File name
    - File size
    - Created date
    - Modified date
    - Number of lines/words
    """
    path = Path(file_path)
    stats = path.stat()

    # Count lines and words
    lines = contents.split("\n")
    line_count = len(lines)
    word_count = sum(len(line.split()) for line in lines)

    # Extract metadata
    metadata = {
        "file_name": path.name,
        "file_size": stats.st_size,
        "file_size_readable": f"{stats.st_size / 1024:.2f} KB",
        "created_date": datetime.fromtimestamp(stats.st_ctime).isoformat(),
        "modified_date": datetime.fromtimestamp(stats.st_mtime).isoformat(),
        "line_count": line_count,
        "word_count": word_count,
        "character_count": len(contents),
        "file_extension": path.suffix,
    }

    return metadata


def analyze_document(file_path):
    """
    Main function: orchestrates document analysis.

    This function should:
    1. Validate the file path (security)
    2. Read the document
    3. Extract metadata
    4. Return structured analysis

    Security: Error messages are sanitized to prevent information disclosure.
    """
    try:
        logger.info(f"Starting document analysis: {hash(file_path)}")

        # Step 1: Validate the file path for security
        validated_path = validate_file_path(file_path)

        # Step 2: Read the document contents
        contents = read_document(validated_path)

        # Step 3: Extract metadata
        metadata = extract_metadata(validated_path, contents)

        # Step 4: Return structured analysis
        analysis = {
            "status": "success",
            "metadata": metadata,
            "timestamp": datetime.now().isoformat(),
        }

        logger.info(f"Document analysis completed successfully: {hash(file_path)}")
        return analysis

    except (ValueError, FileNotFoundError, IOError) as e:
        # Log full error details internally for debugging
        logger.error(
            f"Document analysis failed: {hash(file_path)} - "
            f"{type(e).__name__}: {str(e)}"
        )

        # Return sanitized error message to prevent information disclosure
        # Map specific errors to generic user-friendly messages
        error_messages = {
            "ValueError": "Invalid file or unsupported format",
            "FileNotFoundError": "File not found or inaccessible",
            "IOError": "Unable to read file",
        }

        return {
            "status": "error",
            "error_message": error_messages.get(
                type(e).__name__, "Document processing failed"
            ),
            "timestamp": datetime.now().isoformat(),
        }


# Test the function
if __name__ == "__main__":
    # Create uploads directory if it doesn't exist
    ALLOWED_BASE_DIR.mkdir(parents=True, exist_ok=True)

    # Create a sample document for testing in the uploads directory
    test_doc = ALLOWED_BASE_DIR / "test_document.txt"
    with open(test_doc, "w") as f:
        f.write("Sample document for DocuMind testing.\nThis is line 2.")

    # Analyze it
    result = analyze_document(str(test_doc))
    print(json.dumps(result, indent=2))

    # Clean up test file
    test_doc.unlink()
