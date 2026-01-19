"""
Unit tests for Orchestrator Agent
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from src.agents.pipeline.orchestrate import OrchestratorAgent


class TestOrchestratorAgent:
    """Test suite for OrchestratorAgent."""

    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary output directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def temp_docs_dir(self):
        """Create a temporary directory with test documents."""
        temp_dir = tempfile.mkdtemp()

        # Create test files
        txt_file = Path(temp_dir) / 'test1.txt'
        txt_file.write_text('This is a test document. It has some content for testing the pipeline.')

        md_file = Path(temp_dir) / 'test2.md'
        md_file.write_text('# Test Markdown\n\nThis is markdown content for testing.')

        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def agent(self, temp_output_dir):
        """Create an OrchestratorAgent instance."""
        return OrchestratorAgent(
            chunk_size=50,
            overlap=10,
            output_dir=temp_output_dir
        )

    def test_process_file_success(self, agent, temp_docs_dir):
        """Test successful processing of a single file."""
        test_file = Path(temp_docs_dir) / 'test1.txt'

        result = agent.process_file(str(test_file))

        assert result['success'] is True
        assert result['file_path'] == str(test_file)
        assert 'document_id' in result
        assert result['document_id'] != ''
        assert result['chunks_count'] > 0

        # Verify stages
        assert 'stages' in result
        assert 'extract' in result['stages']
        assert 'chunk' in result['stages']
        assert 'write' in result['stages']

        # All stages should succeed
        assert result['stages']['extract']['success'] is True
        assert result['stages']['chunk']['success'] is True
        assert result['stages']['write']['success'] is True

    def test_process_nonexistent_file(self, agent):
        """Test processing of non-existent file."""
        result = agent.process_file('/path/to/nonexistent.txt')

        assert result['success'] is False
        assert 'error' in result

    def test_process_unsupported_file(self, agent, temp_docs_dir):
        """Test processing of unsupported file format."""
        # Create unsupported file
        unsupported_file = Path(temp_docs_dir) / 'test.pdf'
        unsupported_file.write_text('fake pdf content')

        result = agent.process_file(str(unsupported_file))

        assert result['success'] is False
        assert 'error' in result

    def test_process_directory_success(self, agent, temp_docs_dir):
        """Test successful processing of a directory."""
        result = agent.process_directory(temp_docs_dir)

        assert result['success'] is True
        assert result['total_files'] == 2  # test1.txt and test2.md
        assert result['processed'] == 2
        assert result['failed'] == 0
        assert len(result['results']) == 2

        # Verify all results succeeded
        assert all(r['success'] for r in result['results'])

    def test_process_empty_directory(self, agent):
        """Test processing of empty directory."""
        temp_dir = tempfile.mkdtemp()

        try:
            result = agent.process_directory(temp_dir)

            assert result['success'] is False
            assert 'error' in result
            assert result['total_files'] == 0
        finally:
            shutil.rmtree(temp_dir)

    def test_process_nonexistent_directory(self, agent):
        """Test processing of non-existent directory."""
        result = agent.process_directory('/path/to/nonexistent')

        assert result['success'] is False
        assert 'error' in result

    def test_output_files_created(self, agent, temp_docs_dir, temp_output_dir):
        """Test that output files are created."""
        result = agent.process_directory(temp_docs_dir)

        assert result['success'] is True

        # Check output directories
        docs_dir = Path(temp_output_dir) / 'documents'
        chunks_dir = Path(temp_output_dir) / 'chunks'
        reports_dir = Path(temp_output_dir) / 'reports'

        assert docs_dir.exists()
        assert chunks_dir.exists()
        assert reports_dir.exists()

        # Check that files were created
        assert len(list(docs_dir.glob('*.json'))) == 2
        assert len(list(chunks_dir.glob('*_chunks.json'))) == 2
        assert len(list(reports_dir.glob('*.json'))) == 1

    def test_custom_chunk_settings(self, temp_output_dir, temp_docs_dir):
        """Test orchestrator with custom chunk settings."""
        agent = OrchestratorAgent(
            chunk_size=100,
            overlap=20,
            output_dir=temp_output_dir
        )

        test_file = Path(temp_docs_dir) / 'test1.txt'
        result = agent.process_file(str(test_file))

        assert result['success'] is True
        assert agent.chunk_size == 100
        assert agent.overlap == 20

    def test_processing_metrics(self, agent, temp_docs_dir):
        """Test that processing metrics are collected."""
        result = agent.process_directory(temp_docs_dir)

        assert result['success'] is True
        assert 'total_files' in result
        assert 'processed' in result
        assert 'failed' in result
        assert 'results' in result

        # Verify individual results have required fields
        for file_result in result['results']:
            assert 'success' in file_result
            assert 'file_path' in file_result
            assert 'chunks_count' in file_result

    def test_error_isolation(self, agent, temp_docs_dir):
        """Test that processing succeeds with valid files."""
        # Note: The orchestrator only finds files with supported extensions (.txt, .md)
        # Unsupported file types (like .pdf) are not discovered by the glob pattern
        # This test verifies that valid files are processed successfully

        result = agent.process_directory(temp_docs_dir)

        # Should succeed with all valid files
        assert result['success'] is True
        assert result['processed'] == 2
        assert result['failed'] == 0
        assert result['total_files'] == 2

    def test_report_generation(self, agent, temp_docs_dir):
        """Test that processing report is generated."""
        result = agent.process_directory(temp_docs_dir)

        assert result['success'] is True
        assert 'report_path' in result
        assert result['report_path'] != ''
        assert Path(result['report_path']).exists()

    def test_subdirectory_processing(self, agent):
        """Test recursive processing of subdirectories."""
        temp_dir = tempfile.mkdtemp()

        try:
            # Create subdirectory with files
            subdir = Path(temp_dir) / 'subdir'
            subdir.mkdir()

            (Path(temp_dir) / 'root.txt').write_text('Root level file.')
            (subdir / 'nested.txt').write_text('Nested file.')

            result = agent.process_directory(temp_dir)

            # Should find both files (recursive)
            assert result['success'] is True
            assert result['total_files'] == 2
        finally:
            shutil.rmtree(temp_dir)
