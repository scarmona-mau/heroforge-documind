"""
Integration tests for end-to-end pipeline processing
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path

from src.agents.pipeline.orchestrate import OrchestratorAgent


class TestPipelineE2E:
    """End-to-end integration tests for the document processing pipeline."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        docs_dir = tempfile.mkdtemp()
        output_dir = tempfile.mkdtemp()

        yield docs_dir, output_dir

        shutil.rmtree(docs_dir)
        shutil.rmtree(output_dir)

    @pytest.fixture
    def sample_documents(self, temp_dirs):
        """Create sample documents for testing."""
        docs_dir, _ = temp_dirs

        # Create TXT document
        txt_content = """
        Introduction to Machine Learning

        Machine learning is a subset of artificial intelligence that focuses on
        building systems that can learn from data. These systems improve their
        performance on specific tasks over time without being explicitly programmed.

        Types of Machine Learning

        There are three main types of machine learning: supervised learning,
        unsupervised learning, and reinforcement learning. Each type has its
        own use cases and applications.

        Supervised Learning

        Supervised learning involves training models on labeled data. The model
        learns to map inputs to outputs by finding patterns in the training data.
        Common applications include classification and regression tasks.

        Unsupervised Learning

        Unsupervised learning works with unlabeled data. The system tries to find
        hidden patterns or structures without explicit guidance. Clustering and
        dimensionality reduction are common techniques.

        Reinforcement Learning

        Reinforcement learning involves an agent learning to make decisions by
        interacting with an environment. The agent receives rewards or penalties
        and learns to maximize cumulative rewards over time.
        """

        txt_file = Path(docs_dir) / 'machine_learning.txt'
        txt_file.write_text(txt_content, encoding='utf-8')

        # Create MD document
        md_content = """
# Natural Language Processing

## Overview

Natural Language Processing (NLP) is a field of AI that focuses on the
interaction between computers and human language. It enables machines to
understand, interpret, and generate human language.

## Key Concepts

### Tokenization

Tokenization is the process of breaking text into individual words or tokens.
This is often the first step in NLP pipelines.

### Embeddings

Word embeddings represent words as dense vectors in a continuous space. Similar
words have similar vector representations, capturing semantic relationships.

### Language Models

Language models predict the likelihood of word sequences. Modern transformer-based
models like BERT and GPT have achieved remarkable performance on various NLP tasks.

## Applications

NLP powers many applications we use daily:

- Machine translation
- Sentiment analysis
- Named entity recognition
- Question answering systems
- Text summarization
- Chatbots and virtual assistants

## Challenges

Despite recent advances, NLP still faces challenges:

- Understanding context and ambiguity
- Handling multiple languages
- Dealing with domain-specific terminology
- Addressing bias in training data
- Ensuring privacy and security
        """

        md_file = Path(docs_dir) / 'nlp_guide.md'
        md_file.write_text(md_content, encoding='utf-8')

        return docs_dir

    def test_full_pipeline_processing(self, temp_dirs, sample_documents):
        """Test complete pipeline from extraction to storage."""
        docs_dir, output_dir = temp_dirs

        # Create orchestrator
        orchestrator = OrchestratorAgent(
            chunk_size=100,
            overlap=20,
            output_dir=output_dir
        )

        # Process documents
        result = orchestrator.process_directory(docs_dir)

        # Verify overall success
        assert result['success'] is True
        assert result['total_files'] == 2
        assert result['processed'] == 2
        assert result['failed'] == 0

        # Verify output files exist
        docs_output = Path(output_dir) / 'documents'
        chunks_output = Path(output_dir) / 'chunks'
        reports_output = Path(output_dir) / 'reports'

        assert docs_output.exists()
        assert chunks_output.exists()
        assert reports_output.exists()

        # Verify correct number of files
        doc_files = list(docs_output.glob('*.json'))
        chunk_files = list(chunks_output.glob('*_chunks.json'))
        report_files = list(reports_output.glob('*.json'))

        assert len(doc_files) == 2
        assert len(chunk_files) == 2
        assert len(report_files) == 1

    def test_document_content_preserved(self, temp_dirs, sample_documents):
        """Test that document content is correctly preserved."""
        docs_dir, output_dir = temp_dirs

        orchestrator = OrchestratorAgent(output_dir=output_dir)
        result = orchestrator.process_directory(docs_dir)

        assert result['success'] is True

        # Read document JSONs
        docs_output = Path(output_dir) / 'documents'
        doc_files = list(docs_output.glob('*.json'))

        for doc_file in doc_files:
            with open(doc_file, 'r', encoding='utf-8') as f:
                doc_data = json.load(f)

            # Verify structure
            assert 'id' in doc_data
            assert 'title' in doc_data
            assert 'content' in doc_data
            assert 'metadata' in doc_data

            # Verify content is not empty
            assert len(doc_data['content']) > 0
            assert doc_data['metadata']['word_count'] > 0

    def test_chunks_generated_correctly(self, temp_dirs, sample_documents):
        """Test that chunks are generated with proper structure."""
        docs_dir, output_dir = temp_dirs

        orchestrator = OrchestratorAgent(
            chunk_size=50,
            overlap=10,
            output_dir=output_dir
        )
        result = orchestrator.process_directory(docs_dir)

        assert result['success'] is True

        # Read chunks JSONs
        chunks_output = Path(output_dir) / 'chunks'
        chunk_files = list(chunks_output.glob('*_chunks.json'))

        for chunk_file in chunk_files:
            with open(chunk_file, 'r', encoding='utf-8') as f:
                chunks_data = json.load(f)

            # Verify structure
            assert 'document_id' in chunks_data
            assert 'chunks' in chunks_data
            assert 'total_chunks' in chunks_data

            # Verify chunks
            assert len(chunks_data['chunks']) > 0

            for chunk in chunks_data['chunks']:
                assert 'index' in chunk
                assert 'content' in chunk
                assert 'word_count' in chunk
                assert len(chunk['content']) > 0
                assert chunk['word_count'] > 0

    def test_report_contains_metrics(self, temp_dirs, sample_documents):
        """Test that processing report contains correct metrics."""
        docs_dir, output_dir = temp_dirs

        orchestrator = OrchestratorAgent(output_dir=output_dir)
        result = orchestrator.process_directory(docs_dir)

        assert result['success'] is True
        assert 'report_path' in result

        # Read report
        with open(result['report_path'], 'r', encoding='utf-8') as f:
            report = json.load(f)

        # Verify report structure
        assert 'directory' in report
        assert 'total_files' in report
        assert 'processed' in report
        assert 'failed' in report
        assert 'success_rate' in report
        assert 'config' in report
        assert 'results' in report
        assert 'generated_at' in report

        # Verify metrics
        assert report['total_files'] == 2
        assert report['processed'] == 2
        assert report['failed'] == 0
        assert report['success_rate'] == '100.0%'

        # Verify config
        assert 'chunk_size' in report['config']
        assert 'overlap' in report['config']

        # Verify individual results
        assert len(report['results']) == 2
        for result_item in report['results']:
            assert result_item['success'] is True
            assert 'document_id' in result_item
            assert 'chunks_count' in result_item

    def test_different_chunk_sizes(self, temp_dirs, sample_documents):
        """Test pipeline with different chunk size settings."""
        docs_dir, output_dir = temp_dirs

        # Test with small chunks
        orchestrator_small = OrchestratorAgent(
            chunk_size=30,
            overlap=5,
            output_dir=output_dir
        )

        test_file = Path(docs_dir) / 'machine_learning.txt'
        result_small = orchestrator_small.process_file(str(test_file))

        assert result_small['success'] is True
        small_chunks_count = result_small['chunks_count']

        # Clean up for next test
        for f in (Path(output_dir) / 'documents').glob('*.json'):
            f.unlink()
        for f in (Path(output_dir) / 'chunks').glob('*.json'):
            f.unlink()

        # Test with large chunks
        orchestrator_large = OrchestratorAgent(
            chunk_size=200,
            overlap=20,
            output_dir=output_dir
        )

        result_large = orchestrator_large.process_file(str(test_file))

        assert result_large['success'] is True
        large_chunks_count = result_large['chunks_count']

        # Smaller chunk size should create more chunks
        assert small_chunks_count >= large_chunks_count

    def test_unicode_handling(self, temp_dirs):
        """Test that pipeline correctly handles Unicode content."""
        docs_dir, output_dir = temp_dirs

        # Create file with Unicode content
        unicode_content = """
        多言語サポート

        This document contains multiple languages and special characters.

        中文：人工智能是计算机科学的一个分支。

        日本語：機械学習はAIの重要な技術です。

        Русский: Обработка естественного языка включает множество задач.

        العربية: التعلم العميق يستخدم الشبكات العصبية.

        Special characters: ñ, ü, é, ç, ß, ø, å

        Mathematical symbols: α, β, γ, π, Σ, ∫, √
        """

        unicode_file = Path(docs_dir) / 'unicode_test.txt'
        unicode_file.write_text(unicode_content, encoding='utf-8')

        # Process document
        orchestrator = OrchestratorAgent(output_dir=output_dir)
        result = orchestrator.process_file(str(unicode_file))

        assert result['success'] is True

        # Verify content is preserved
        doc_file = Path(output_dir) / 'documents' / f"{result['document_id']}.json"
        with open(doc_file, 'r', encoding='utf-8') as f:
            doc_data = json.load(f)

        # Check that various Unicode characters are preserved
        content = doc_data['content']
        assert '中文' in content
        assert '日本語' in content
        assert 'Русский' in content
        assert 'α' in content

    def test_error_recovery(self, temp_dirs):
        """Test that pipeline processes only supported file types."""
        docs_dir, output_dir = temp_dirs

        # Create mix of valid and unsupported files
        # Note: The orchestrator only discovers files with supported extensions
        (Path(docs_dir) / 'valid.txt').write_text('Valid content here.')
        (Path(docs_dir) / 'invalid.pdf').write_text('Fake PDF')  # Won't be discovered
        (Path(docs_dir) / 'another_valid.md').write_text('# Valid markdown')

        # Process directory
        orchestrator = OrchestratorAgent(output_dir=output_dir)
        result = orchestrator.process_directory(docs_dir)

        # Should process only valid file types
        assert result['success'] is True
        assert result['total_files'] == 2  # Only .txt and .md found
        assert result['processed'] == 2
        assert result['failed'] == 0

        # Verify valid files were processed
        doc_files = list((Path(output_dir) / 'documents').glob('*.json'))
        assert len(doc_files) == 2
