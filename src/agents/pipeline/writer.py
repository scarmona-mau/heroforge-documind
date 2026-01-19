"""
Writer Agent - Output storage for processed documents
Session 3: File-based JSON storage
Future: Database storage via Supabase (Session 4+)
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import uuid


class WriterAgent:
    """
    Writes processed documents and chunks to storage.

    Session 3 scope: JSON file storage in output/ directory
    Future: Supabase database storage with pgvector
    """

    def __init__(self, output_dir: str = 'output'):
        """
        Initialize writer with output directory.

        Args:
            output_dir: Base output directory path
        """
        self.output_dir = Path(output_dir)
        self.documents_dir = self.output_dir / 'documents'
        self.chunks_dir = self.output_dir / 'chunks'
        self.reports_dir = self.output_dir / 'reports'

        # Create directories if they don't exist
        self._ensure_directories()

    def _ensure_directories(self):
        """Create output directories if they don't exist."""
        self.documents_dir.mkdir(parents=True, exist_ok=True)
        self.chunks_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def write_document(
        self,
        file_path: str,
        text: str,
        metadata: Dict[str, Any],
        format: str,
        chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Write document and chunks to JSON files.

        Args:
            file_path: Original file path
            text: Extracted text content
            metadata: Document metadata
            format: File format (txt, md, etc.)
            chunks: List of chunk dictionaries

        Returns:
            Dict with keys:
                - success (bool): Whether write succeeded
                - document_id (str): Generated document ID
                - document_path (str): Path to document JSON
                - chunks_path (str): Path to chunks JSON
                - chunks_count (int): Number of chunks written
                - error (str, optional): Error message if failed
        """
        try:
            # Generate document ID
            doc_id = str(uuid.uuid4())

            # Create document data structure
            document = {
                'id': doc_id,
                'title': Path(file_path).stem,  # Filename without extension
                'file_path': file_path,
                'file_type': format,
                'content': text,
                'metadata': {
                    **metadata,
                    'processed_at': datetime.utcnow().isoformat(),
                },
            }

            # Create chunks data structure
            chunks_data = {
                'document_id': doc_id,
                'chunks': chunks,
                'total_chunks': len(chunks),
                'created_at': datetime.utcnow().isoformat(),
            }

            # Write document JSON
            doc_path = self.documents_dir / f'{doc_id}.json'
            with open(doc_path, 'w', encoding='utf-8') as f:
                json.dump(document, f, indent=2, ensure_ascii=False)

            # Write chunks JSON
            chunks_path = self.chunks_dir / f'{doc_id}_chunks.json'
            with open(chunks_path, 'w', encoding='utf-8') as f:
                json.dump(chunks_data, f, indent=2, ensure_ascii=False)

            return {
                'success': True,
                'document_id': doc_id,
                'document_path': str(doc_path),
                'chunks_path': str(chunks_path),
                'chunks_count': len(chunks),
            }

        except Exception as e:
            return {
                'success': False,
                'document_id': '',
                'document_path': '',
                'chunks_path': '',
                'chunks_count': 0,
                'error': f'Write failed: {str(e)}'
            }

    def write_report(self, report_data: Dict[str, Any], report_name: str = 'pipeline_report') -> Dict[str, Any]:
        """
        Write processing report to JSON file.

        Args:
            report_data: Report data dictionary
            report_name: Report filename (without extension)

        Returns:
            Dict with keys:
                - success (bool): Whether write succeeded
                - report_path (str): Path to report JSON
                - error (str, optional): Error message if failed
        """
        try:
            # Add timestamp
            report = {
                **report_data,
                'generated_at': datetime.utcnow().isoformat(),
            }

            # Write report JSON
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            report_path = self.reports_dir / f'{report_name}_{timestamp}.json'
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            return {
                'success': True,
                'report_path': str(report_path),
            }

        except Exception as e:
            return {
                'success': False,
                'report_path': '',
                'error': f'Report write failed: {str(e)}'
            }


def write_processed_document(
    file_path: str,
    text: str,
    metadata: Dict[str, Any],
    format: str,
    chunks: List[Dict[str, Any]],
    output_dir: str = 'output'
) -> Dict[str, Any]:
    """
    Convenience function to write a processed document.

    Args:
        file_path: Original file path
        text: Extracted text content
        metadata: Document metadata
        format: File format
        chunks: List of chunks
        output_dir: Output directory path

    Returns:
        Write result dictionary
    """
    agent = WriterAgent(output_dir=output_dir)
    return agent.write_document(file_path, text, metadata, format, chunks)


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python writer.py <document_json> <chunks_json>")
        print("  (This is typically called by the orchestrator)")
        sys.exit(1)

    # Demo: Read and write sample data
    print("Writer Agent - Demo mode")
    print("This agent is typically called by the orchestrator.")

    # Create writer
    writer = WriterAgent()

    # Write sample document
    result = writer.write_document(
        file_path='demo.txt',
        text='This is sample text for testing the writer agent.',
        metadata={'word_count': 9, 'char_count': 53},
        format='txt',
        chunks=[
            {'index': 0, 'content': 'This is sample text for testing the writer agent.', 'word_count': 9}
        ]
    )

    if result['success']:
        print(f"✓ Document written: {result['document_id']}")
        print(f"  Document JSON: {result['document_path']}")
        print(f"  Chunks JSON: {result['chunks_path']}")
        print(f"  Chunks count: {result['chunks_count']}")
    else:
        print(f"✗ Write failed: {result['error']}")
        sys.exit(1)
