"""
Extractor Agent - Document text extraction
Session 3: Basic TXT/MD support
Future: PDF, DOCX, XLSX (Session 7+)
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class ExtractorAgent:
    """
    Extracts text content from documents.

    Session 3 scope: TXT and MD files
    Future: PDF, DOCX, XLSX formats
    """

    # Supported formats for Session 3
    SUPPORTED_FORMATS = {'.txt', '.md'}

    def extract(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text content from a file.

        Args:
            file_path: Path to the document file

        Returns:
            Dict with keys:
                - success (bool): Whether extraction succeeded
                - text (str): Extracted text content
                - metadata (dict): File metadata
                - format (str): File format (txt, md, etc.)
                - error (str, optional): Error message if failed
        """
        try:
            # Validate file exists
            path = Path(file_path)
            if not path.exists():
                return {
                    'success': False,
                    'text': '',
                    'metadata': {},
                    'format': '',
                    'error': f'File not found: {file_path}'
                }

            # Check file format
            file_ext = path.suffix.lower()
            if file_ext not in self.SUPPORTED_FORMATS:
                return {
                    'success': False,
                    'text': '',
                    'metadata': {},
                    'format': file_ext.lstrip('.'),
                    'error': f'Unsupported format: {file_ext}. Supported: {self.SUPPORTED_FORMATS}'
                }

            # Extract text based on format
            text = self._extract_text(path, file_ext)

            # Extract metadata
            metadata = self._extract_metadata(path, text)

            return {
                'success': True,
                'text': text,
                'metadata': metadata,
                'format': file_ext.lstrip('.'),
            }

        except Exception as e:
            return {
                'success': False,
                'text': '',
                'metadata': {},
                'format': '',
                'error': f'Extraction failed: {str(e)}'
            }

    def _extract_text(self, path: Path, file_ext: str) -> str:
        """
        Extract text based on file format.

        Args:
            path: Path object for the file
            file_ext: File extension

        Returns:
            Extracted text content
        """
        # For Session 3, TXT and MD are both plain text
        with open(path, 'r', encoding='utf-8') as f:
            text = f.read()

        return text

    def _extract_metadata(self, path: Path, text: str) -> Dict[str, Any]:
        """
        Extract file metadata.

        Args:
            path: Path object for the file
            text: Extracted text content

        Returns:
            Metadata dictionary
        """
        stat = path.stat()

        # Count words (simple space-based splitting)
        word_count = len(text.split())

        return {
            'filename': path.name,
            'file_size_bytes': stat.st_size,
            'word_count': word_count,
            'char_count': len(text),
            'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
            'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }


def extract_document(file_path: str) -> Dict[str, Any]:
    """
    Convenience function to extract a document.

    Args:
        file_path: Path to the document

    Returns:
        Extraction result dictionary
    """
    agent = ExtractorAgent()
    return agent.extract(file_path)


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python extractor.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]
    result = extract_document(file_path)

    if result['success']:
        print(f"✓ Extracted {result['format'].upper()} file")
        print(f"  Words: {result['metadata']['word_count']}")
        print(f"  Chars: {result['metadata']['char_count']}")
        print(f"\nText preview (first 200 chars):")
        print(result['text'][:200] + '...' if len(result['text']) > 200 else result['text'])
    else:
        print(f"✗ Extraction failed: {result['error']}")
        sys.exit(1)
