"""
Unit tests for Extractor Agent
"""

import pytest
import tempfile
from pathlib import Path

from src.agents.pipeline.extractor import ExtractorAgent, extract_document


class TestExtractorAgent:
    """Test suite for ExtractorAgent."""

    @pytest.fixture
    def agent(self):
        """Create an ExtractorAgent instance."""
        return ExtractorAgent()

    @pytest.fixture
    def temp_txt_file(self):
        """Create a temporary TXT file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("This is a test document.\nIt has multiple lines.\nAnd some content.")
            temp_path = f.name
        yield temp_path
        Path(temp_path).unlink()

    @pytest.fixture
    def temp_md_file(self):
        """Create a temporary MD file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write("# Test Markdown\n\nThis is a test markdown document.\n\n## Section\n\nWith some content.")
            temp_path = f.name
        yield temp_path
        Path(temp_path).unlink()

    def test_extract_txt_success(self, agent, temp_txt_file):
        """Test successful extraction of TXT file."""
        result = agent.extract(temp_txt_file)

        assert result['success'] is True
        assert result['format'] == 'txt'
        assert 'This is a test document' in result['text']
        assert result['metadata']['word_count'] > 0
        assert result['metadata']['char_count'] > 0
        assert 'filename' in result['metadata']

    def test_extract_md_success(self, agent, temp_md_file):
        """Test successful extraction of MD file."""
        result = agent.extract(temp_md_file)

        assert result['success'] is True
        assert result['format'] == 'md'
        assert '# Test Markdown' in result['text']
        assert result['metadata']['word_count'] > 0

    def test_extract_nonexistent_file(self, agent):
        """Test extraction of non-existent file."""
        result = agent.extract('/path/to/nonexistent/file.txt')

        assert result['success'] is False
        assert 'error' in result
        assert 'not found' in result['error'].lower()

    def test_extract_unsupported_format(self, agent):
        """Test extraction of unsupported file format."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            temp_path = f.name

        try:
            result = agent.extract(temp_path)

            assert result['success'] is False
            assert 'error' in result
            assert 'unsupported' in result['error'].lower()
        finally:
            Path(temp_path).unlink()

    def test_metadata_extraction(self, agent, temp_txt_file):
        """Test that metadata is properly extracted."""
        result = agent.extract(temp_txt_file)

        assert result['success'] is True
        metadata = result['metadata']

        assert 'filename' in metadata
        assert 'file_size_bytes' in metadata
        assert 'word_count' in metadata
        assert 'char_count' in metadata
        assert 'created_at' in metadata
        assert 'modified_at' in metadata

        assert metadata['file_size_bytes'] > 0
        assert metadata['word_count'] > 0
        assert metadata['char_count'] > 0

    def test_convenience_function(self, temp_txt_file):
        """Test the extract_document convenience function."""
        result = extract_document(temp_txt_file)

        assert result['success'] is True
        assert result['format'] == 'txt'

    def test_empty_file(self, agent):
        """Test extraction of empty file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            temp_path = f.name

        try:
            result = agent.extract(temp_path)

            # Empty files should still succeed but have zero content
            assert result['success'] is True
            assert result['text'] == ''
            assert result['metadata']['word_count'] == 0
        finally:
            Path(temp_path).unlink()

    def test_unicode_content(self, agent):
        """Test extraction of file with Unicode content."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("Hello 世界! Привет мир! مرحبا بالعالم!")
            temp_path = f.name

        try:
            result = agent.extract(temp_path)

            assert result['success'] is True
            assert '世界' in result['text']
            assert 'Привет' in result['text']
            assert 'مرحبا' in result['text']
        finally:
            Path(temp_path).unlink()
