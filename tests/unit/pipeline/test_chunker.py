"""
Unit tests for Chunker Agent
"""

import pytest

from src.agents.pipeline.chunker import ChunkerAgent, chunk_text


class TestChunkerAgent:
    """Test suite for ChunkerAgent."""

    @pytest.fixture
    def agent(self):
        """Create a ChunkerAgent instance with default settings."""
        return ChunkerAgent(chunk_size=50, overlap=10)

    @pytest.fixture
    def small_agent(self):
        """Create a ChunkerAgent with small chunk size for testing."""
        return ChunkerAgent(chunk_size=20, overlap=5)

    def test_chunk_simple_text(self, agent):
        """Test chunking of simple text."""
        text = "This is a test. " * 100  # Create text with 300 words

        result = agent.chunk(text)

        assert result['success'] is True
        assert result['total_chunks'] > 1
        assert len(result['chunks']) == result['total_chunks']

        # Verify chunk structure
        for chunk in result['chunks']:
            assert 'index' in chunk
            assert 'content' in chunk
            assert 'word_count' in chunk
            assert chunk['word_count'] > 0

    def test_chunk_empty_text(self, agent):
        """Test chunking of empty text."""
        result = agent.chunk("")

        assert result['success'] is False
        assert 'error' in result
        assert result['total_chunks'] == 0

    def test_chunk_whitespace_only(self, agent):
        """Test chunking of whitespace-only text."""
        result = agent.chunk("   \n\n   \t   ")

        assert result['success'] is False
        assert 'error' in result

    def test_chunk_single_sentence(self, small_agent):
        """Test chunking of text shorter than chunk size."""
        text = "This is a short sentence."

        result = small_agent.chunk(text)

        assert result['success'] is True
        assert result['total_chunks'] == 1
        assert result['chunks'][0]['content'] == text

    def test_chunk_overlap(self, small_agent):
        """Test that chunks have proper overlap."""
        # Create text with clear sentences
        text = "First sentence here. Second sentence here. Third sentence here. Fourth sentence here. Fifth sentence here."

        result = small_agent.chunk(text)

        if result['total_chunks'] > 1:
            # Check that consecutive chunks share some content (overlap)
            for i in range(len(result['chunks']) - 1):
                current_chunk = result['chunks'][i]['content']
                next_chunk = result['chunks'][i + 1]['content']

                # There should be some overlapping words
                current_words = set(current_chunk.split())
                next_words = set(next_chunk.split())
                overlap_words = current_words & next_words

                assert len(overlap_words) > 0, "Chunks should have overlapping content"

    def test_chunk_size_limits(self, agent):
        """Test that chunks respect size limits."""
        text = "Word. " * 200  # Create text with many short sentences

        result = agent.chunk(text)

        assert result['success'] is True

        for chunk in result['chunks']:
            # Chunks should be approximately within chunk_size
            # Allow some flexibility for sentence boundaries
            assert chunk['word_count'] <= agent.chunk_size * 1.5

    def test_chunk_indices(self, agent):
        """Test that chunk indices are sequential."""
        text = "This is a test sentence. " * 100

        result = agent.chunk(text)

        assert result['success'] is True

        for i, chunk in enumerate(result['chunks']):
            assert chunk['index'] == i

    def test_sentence_splitting(self, small_agent):
        """Test that text is split on sentence boundaries."""
        text = "First sentence. Second sentence! Third sentence? Fourth sentence."

        result = small_agent.chunk(text)

        assert result['success'] is True

        # All sentences should be preserved in chunks
        all_content = ' '.join(chunk['content'] for chunk in result['chunks'])
        assert "First sentence." in all_content
        assert "Second sentence!" in all_content
        assert "Third sentence?" in all_content

    def test_convenience_function(self):
        """Test the chunk_text convenience function."""
        text = "This is a test. " * 100

        result = chunk_text(text, chunk_size=50, overlap=10)

        assert result['success'] is True
        assert result['total_chunks'] > 0

    def test_long_text_chunking(self, agent):
        """Test chunking of long text."""
        # Create a long text document
        text = " ".join([f"Sentence number {i} with some additional words here." for i in range(500)])

        result = agent.chunk(text)

        assert result['success'] is True
        assert result['total_chunks'] > 5

        # Verify all chunks together contain the original content
        all_content = ' '.join(chunk['content'] for chunk in result['chunks'])
        assert "Sentence number 0" in all_content
        assert "Sentence number 499" in all_content

    def test_special_characters(self, agent):
        """Test chunking with special characters."""
        text = "Hello! How are you? I'm fine. It's a nice day. Don't worry, be happy."

        result = agent.chunk(text)

        assert result['success'] is True
        # Content should be preserved
        all_content = ' '.join(chunk['content'] for chunk in result['chunks'])
        assert "I'm fine" in all_content or "I'm fine" in all_content
        assert "Don't worry" in all_content or "Don't worry" in all_content

    def test_multiline_text(self, agent):
        """Test chunking of text with newlines."""
        text = """First paragraph here.
        With multiple lines.

        Second paragraph here.
        Also with multiple lines."""

        result = agent.chunk(text)

        assert result['success'] is True
        assert result['total_chunks'] > 0
