"""
Chunker Agent - Text chunking with overlap
Session 3: Fixed-size chunking with sentence boundaries
Future: Advanced semantic chunking (Session 5+)
"""

import re
from typing import Dict, Any, List


class ChunkerAgent:
    """
    Splits text into fixed-size chunks with overlap.

    Session 3 scope: Simple word-based chunking with sentence boundaries
    Future: Semantic chunking, paragraph-aware splitting
    """

    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        """
        Initialize chunker with size and overlap settings.

        Args:
            chunk_size: Target chunk size in words
            overlap: Overlap size in words
        """
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> Dict[str, Any]:
        """
        Split text into chunks.

        Args:
            text: Text content to chunk

        Returns:
            Dict with keys:
                - success (bool): Whether chunking succeeded
                - chunks (list): List of chunk dicts with content, index, word_count
                - total_chunks (int): Number of chunks created
                - error (str, optional): Error message if failed
        """
        try:
            if not text or not text.strip():
                return {
                    'success': False,
                    'chunks': [],
                    'total_chunks': 0,
                    'error': 'Empty text provided'
                }

            # Split text into sentences
            sentences = self._split_sentences(text)

            # Create chunks from sentences
            chunks = self._create_chunks(sentences)

            return {
                'success': True,
                'chunks': chunks,
                'total_chunks': len(chunks),
            }

        except Exception as e:
            return {
                'success': False,
                'chunks': [],
                'total_chunks': 0,
                'error': f'Chunking failed: {str(e)}'
            }

    def _split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.

        Uses simple heuristics:
        - Split on '. ' (period + space)
        - Split on double newlines (paragraph breaks)
        - Keep sentence-ending punctuation

        Args:
            text: Text to split

        Returns:
            List of sentences
        """
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)

        # Split on sentence boundaries
        # Pattern: period/exclamation/question followed by space or newline
        sentences = re.split(r'(?<=[.!?])\s+', text)

        # Filter empty sentences
        sentences = [s.strip() for s in sentences if s.strip()]

        return sentences

    def _create_chunks(self, sentences: List[str]) -> List[Dict[str, Any]]:
        """
        Create chunks from sentences with overlap.

        Args:
            sentences: List of sentences

        Returns:
            List of chunk dictionaries
        """
        chunks = []
        current_chunk = []
        current_word_count = 0
        chunk_index = 0

        for sentence in sentences:
            sentence_words = len(sentence.split())

            # If adding this sentence exceeds chunk size, finalize current chunk
            if current_word_count + sentence_words > self.chunk_size and current_chunk:
                # Create chunk
                chunk_text = ' '.join(current_chunk)
                chunks.append({
                    'index': chunk_index,
                    'content': chunk_text,
                    'word_count': current_word_count,
                })
                chunk_index += 1

                # Start new chunk with overlap
                overlap_words = self._get_overlap_words(current_chunk)
                current_chunk = overlap_words + [sentence]
                current_word_count = len(' '.join(current_chunk).split())
            else:
                # Add sentence to current chunk
                current_chunk.append(sentence)
                current_word_count += sentence_words

        # Add final chunk if not empty
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append({
                'index': chunk_index,
                'content': chunk_text,
                'word_count': len(chunk_text.split()),
            })

        return chunks

    def _get_overlap_words(self, sentences: List[str]) -> List[str]:
        """
        Get sentences for overlap from end of current chunk.

        Args:
            sentences: List of sentences in current chunk

        Returns:
            List of sentences to overlap into next chunk
        """
        # Calculate how many words we want to overlap
        overlap_target = self.overlap

        overlap_sentences = []
        overlap_word_count = 0

        # Work backwards through sentences until we reach overlap target
        for sentence in reversed(sentences):
            sentence_words = len(sentence.split())
            if overlap_word_count + sentence_words <= overlap_target:
                overlap_sentences.insert(0, sentence)
                overlap_word_count += sentence_words
            else:
                break

        return overlap_sentences


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> Dict[str, Any]:
    """
    Convenience function to chunk text.

    Args:
        text: Text to chunk
        chunk_size: Target chunk size in words
        overlap: Overlap size in words

    Returns:
        Chunking result dictionary
    """
    agent = ChunkerAgent(chunk_size=chunk_size, overlap=overlap)
    return agent.chunk(text)


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python chunker.py <text_file>")
        sys.exit(1)

    # Read text file
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        text = f.read()

    # Chunk the text
    result = chunk_text(text)

    if result['success']:
        print(f"✓ Created {result['total_chunks']} chunks")
        for i, chunk in enumerate(result['chunks']):
            print(f"\n--- Chunk {i} ({chunk['word_count']} words) ---")
            preview = chunk['content'][:150] + '...' if len(chunk['content']) > 150 else chunk['content']
            print(preview)
    else:
        print(f"✗ Chunking failed: {result['error']}")
        sys.exit(1)
