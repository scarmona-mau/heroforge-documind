"""
Unit tests for Writer Agent
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path

from src.agents.pipeline.writer import WriterAgent, write_processed_document


class TestWriterAgent:
    """Test suite for WriterAgent."""

    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary output directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def agent(self, temp_output_dir):
        """Create a WriterAgent instance with temp directory."""
        return WriterAgent(output_dir=temp_output_dir)

    @pytest.fixture
    def sample_chunks(self):
        """Create sample chunks for testing."""
        return [
            {'index': 0, 'content': 'First chunk content here.', 'word_count': 4},
            {'index': 1, 'content': 'Second chunk content here.', 'word_count': 4},
        ]

    def test_write_document_success(self, agent, sample_chunks):
        """Test successful document writing."""
        result = agent.write_document(
            file_path='test.txt',
            text='Full document text here.',
            metadata={'word_count': 4, 'char_count': 24},
            format='txt',
            chunks=sample_chunks
        )

        assert result['success'] is True
        assert 'document_id' in result
        assert result['document_id'] != ''
        assert result['chunks_count'] == 2
        assert 'document_path' in result
        assert 'chunks_path' in result

        # Verify files were created
        assert Path(result['document_path']).exists()
        assert Path(result['chunks_path']).exists()

    def test_document_json_structure(self, agent, sample_chunks):
        """Test that document JSON has correct structure."""
        result = agent.write_document(
            file_path='test.txt',
            text='Full document text here.',
            metadata={'word_count': 4, 'char_count': 24},
            format='txt',
            chunks=sample_chunks
        )

        assert result['success'] is True

        # Read and verify document JSON
        with open(result['document_path'], 'r', encoding='utf-8') as f:
            doc_data = json.load(f)

        assert 'id' in doc_data
        assert 'title' in doc_data
        assert 'file_path' in doc_data
        assert 'file_type' in doc_data
        assert 'content' in doc_data
        assert 'metadata' in doc_data

        assert doc_data['file_path'] == 'test.txt'
        assert doc_data['file_type'] == 'txt'
        assert doc_data['content'] == 'Full document text here.'
        assert 'processed_at' in doc_data['metadata']

    def test_chunks_json_structure(self, agent, sample_chunks):
        """Test that chunks JSON has correct structure."""
        result = agent.write_document(
            file_path='test.txt',
            text='Full document text here.',
            metadata={'word_count': 4},
            format='txt',
            chunks=sample_chunks
        )

        assert result['success'] is True

        # Read and verify chunks JSON
        with open(result['chunks_path'], 'r', encoding='utf-8') as f:
            chunks_data = json.load(f)

        assert 'document_id' in chunks_data
        assert 'chunks' in chunks_data
        assert 'total_chunks' in chunks_data
        assert 'created_at' in chunks_data

        assert chunks_data['document_id'] == result['document_id']
        assert chunks_data['total_chunks'] == 2
        assert len(chunks_data['chunks']) == 2

        # Verify chunk structure
        for chunk in chunks_data['chunks']:
            assert 'index' in chunk
            assert 'content' in chunk
            assert 'word_count' in chunk

    def test_write_report(self, agent):
        """Test writing a processing report."""
        report_data = {
            'total_files': 5,
            'processed': 4,
            'failed': 1,
            'success_rate': '80.0%'
        }

        result = agent.write_report(report_data, report_name='test_report')

        assert result['success'] is True
        assert 'report_path' in result
        assert Path(result['report_path']).exists()

        # Read and verify report
        with open(result['report_path'], 'r', encoding='utf-8') as f:
            report = json.load(f)

        assert report['total_files'] == 5
        assert report['processed'] == 4
        assert report['failed'] == 1
        assert 'generated_at' in report

    def test_output_directories_created(self, temp_output_dir):
        """Test that output directories are created."""
        agent = WriterAgent(output_dir=temp_output_dir)

        # Check that subdirectories exist
        assert Path(temp_output_dir, 'documents').exists()
        assert Path(temp_output_dir, 'chunks').exists()
        assert Path(temp_output_dir, 'reports').exists()

    def test_unicode_content(self, agent):
        """Test writing documents with Unicode content."""
        chunks = [
            {'index': 0, 'content': 'Hello 世界! Привет мир!', 'word_count': 4}
        ]

        result = agent.write_document(
            file_path='unicode.txt',
            text='Hello 世界! Привет мир!',
            metadata={'word_count': 4},
            format='txt',
            chunks=chunks
        )

        assert result['success'] is True

        # Read and verify Unicode is preserved
        with open(result['document_path'], 'r', encoding='utf-8') as f:
            doc_data = json.load(f)

        assert '世界' in doc_data['content']
        assert 'Привет' in doc_data['content']

    def test_empty_chunks_list(self, agent):
        """Test writing document with no chunks."""
        result = agent.write_document(
            file_path='test.txt',
            text='Text here.',
            metadata={'word_count': 2},
            format='txt',
            chunks=[]
        )

        assert result['success'] is True
        assert result['chunks_count'] == 0

    def test_convenience_function(self, temp_output_dir, sample_chunks):
        """Test the write_processed_document convenience function."""
        result = write_processed_document(
            file_path='test.txt',
            text='Full document text.',
            metadata={'word_count': 3},
            format='txt',
            chunks=sample_chunks,
            output_dir=temp_output_dir
        )

        assert result['success'] is True
        assert Path(result['document_path']).exists()

    def test_multiple_documents(self, agent, sample_chunks):
        """Test writing multiple documents."""
        results = []

        for i in range(3):
            result = agent.write_document(
                file_path=f'test{i}.txt',
                text=f'Document {i} text.',
                metadata={'word_count': 3},
                format='txt',
                chunks=sample_chunks
            )
            results.append(result)

        # All should succeed
        assert all(r['success'] for r in results)

        # Each should have unique document ID
        doc_ids = [r['document_id'] for r in results]
        assert len(doc_ids) == len(set(doc_ids))

        # All files should exist
        for result in results:
            assert Path(result['document_path']).exists()
            assert Path(result['chunks_path']).exists()
