"""
Orchestrator Agent - Pipeline coordination
Session 3: Sequential document processing
Future: Parallel processing with asyncio (Session 5+)
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from .extractor import ExtractorAgent
from .chunker import ChunkerAgent
from .writer import WriterAgent


class OrchestratorAgent:
    """
    Coordinates the document processing pipeline.

    Session 3 scope: Sequential processing of documents
    Future: Parallel processing, advanced error recovery
    """

    def __init__(
        self,
        chunk_size: int = 500,
        overlap: int = 50,
        output_dir: str = 'output'
    ):
        """
        Initialize orchestrator with pipeline configuration.

        Args:
            chunk_size: Target chunk size in words
            overlap: Overlap size in words
            output_dir: Output directory for processed documents
        """
        self.extractor = ExtractorAgent()
        self.chunker = ChunkerAgent(chunk_size=chunk_size, overlap=overlap)
        self.writer = WriterAgent(output_dir=output_dir)

        self.chunk_size = chunk_size
        self.overlap = overlap
        self.output_dir = output_dir

    def process_file(self, file_path: str) -> Dict[str, Any]:
        """
        Process a single document through the pipeline.

        Pipeline stages:
        1. Extractor: Extract text from file
        2. Chunker: Split text into chunks
        3. Writer: Save to JSON files

        Args:
            file_path: Path to document file

        Returns:
            Dict with keys:
                - success (bool): Overall pipeline success
                - file_path (str): Input file path
                - document_id (str): Generated document ID
                - chunks_count (int): Number of chunks created
                - stages (dict): Results from each stage
                - error (str, optional): Error message if failed
        """
        stages = {}

        try:
            # Stage 1: Extract text
            print(f"  [1/3] Extracting text...")
            extract_result = self.extractor.extract(file_path)
            stages['extract'] = extract_result

            if not extract_result['success']:
                return {
                    'success': False,
                    'file_path': file_path,
                    'document_id': '',
                    'chunks_count': 0,
                    'stages': stages,
                    'error': f"Extraction failed: {extract_result.get('error', 'Unknown error')}"
                }

            # Stage 2: Chunk text
            print(f"  [2/3] Chunking text ({extract_result['metadata']['word_count']} words)...")
            chunk_result = self.chunker.chunk(extract_result['text'])
            stages['chunk'] = chunk_result

            if not chunk_result['success']:
                return {
                    'success': False,
                    'file_path': file_path,
                    'document_id': '',
                    'chunks_count': 0,
                    'stages': stages,
                    'error': f"Chunking failed: {chunk_result.get('error', 'Unknown error')}"
                }

            # Stage 3: Write to storage
            print(f"  [3/3] Writing {chunk_result['total_chunks']} chunks to storage...")
            write_result = self.writer.write_document(
                file_path=file_path,
                text=extract_result['text'],
                metadata=extract_result['metadata'],
                format=extract_result['format'],
                chunks=chunk_result['chunks']
            )
            stages['write'] = write_result

            if not write_result['success']:
                return {
                    'success': False,
                    'file_path': file_path,
                    'document_id': '',
                    'chunks_count': 0,
                    'stages': stages,
                    'error': f"Write failed: {write_result.get('error', 'Unknown error')}"
                }

            # Success
            return {
                'success': True,
                'file_path': file_path,
                'document_id': write_result['document_id'],
                'chunks_count': write_result['chunks_count'],
                'stages': stages,
            }

        except Exception as e:
            return {
                'success': False,
                'file_path': file_path,
                'document_id': '',
                'chunks_count': 0,
                'stages': stages,
                'error': f'Pipeline error: {str(e)}'
            }

    def process_directory(self, directory_path: str) -> Dict[str, Any]:
        """
        Process all documents in a directory.

        Args:
            directory_path: Path to directory containing documents

        Returns:
            Dict with keys:
                - success (bool): Overall success
                - total_files (int): Total files found
                - processed (int): Successfully processed
                - failed (int): Failed to process
                - results (list): Individual file results
                - report_path (str): Path to generated report
        """
        directory = Path(directory_path)

        if not directory.exists():
            return {
                'success': False,
                'total_files': 0,
                'processed': 0,
                'failed': 0,
                'results': [],
                'error': f'Directory not found: {directory_path}'
            }

        # Find all supported files (recursive)
        supported_extensions = self.extractor.SUPPORTED_FORMATS
        files = []
        for ext in supported_extensions:
            files.extend(directory.glob(f'**/*{ext}'))  # Recursive

        # Remove duplicates while preserving order
        seen = set()
        unique_files = []
        for file in files:
            if file not in seen:
                seen.add(file)
                unique_files.append(file)
        files = unique_files

        if not files:
            return {
                'success': False,
                'total_files': 0,
                'processed': 0,
                'failed': 0,
                'results': [],
                'error': f'No supported files found in {directory_path}'
            }

        print(f"\n{'='*60}")
        print(f"Document Processing Pipeline")
        print(f"{'='*60}")
        print(f"Directory: {directory_path}")
        print(f"Files found: {len(files)}")
        print(f"Chunk size: {self.chunk_size} words")
        print(f"Overlap: {self.overlap} words")
        print(f"Output: {self.output_dir}/")
        print(f"{'='*60}\n")

        # Process each file
        results = []
        processed_count = 0
        failed_count = 0

        for i, file_path in enumerate(files, 1):
            print(f"[{i}/{len(files)}] Processing: {file_path.name}")

            result = self.process_file(str(file_path))
            results.append(result)

            if result['success']:
                processed_count += 1
                print(f"  ✓ Success: {result['chunks_count']} chunks created")
                print(f"    Document ID: {result['document_id']}")
            else:
                failed_count += 1
                print(f"  ✗ Failed: {result.get('error', 'Unknown error')}")

            print()

        # Generate report
        report_data = {
            'directory': directory_path,
            'total_files': len(files),
            'processed': processed_count,
            'failed': failed_count,
            'success_rate': f"{(processed_count / len(files) * 100):.1f}%",
            'config': {
                'chunk_size': self.chunk_size,
                'overlap': self.overlap,
                'output_dir': self.output_dir,
            },
            'results': results,
        }

        report_result = self.writer.write_report(report_data)

        print(f"{'='*60}")
        print(f"Pipeline Complete")
        print(f"{'='*60}")
        print(f"Total files: {len(files)}")
        print(f"Processed: {processed_count}")
        print(f"Failed: {failed_count}")
        print(f"Success rate: {report_data['success_rate']}")

        if report_result['success']:
            print(f"Report: {report_result['report_path']}")
        print(f"{'='*60}\n")

        return {
            'success': processed_count > 0,
            'total_files': len(files),
            'processed': processed_count,
            'failed': failed_count,
            'results': results,
            'report_path': report_result.get('report_path', ''),
        }


def main():
    """CLI entry point for the orchestrator."""
    parser = argparse.ArgumentParser(
        description='DocuMind Document Processing Pipeline (Session 3)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process all documents in demo-docs/
  python orchestrate.py demo-docs/

  # Process with custom chunk size
  python orchestrate.py demo-docs/ --chunk-size 1000 --overlap 100

  # Process to custom output directory
  python orchestrate.py demo-docs/ --output output-custom/
        """
    )

    parser.add_argument(
        'directory',
        help='Directory containing documents to process'
    )
    parser.add_argument(
        '--chunk-size',
        type=int,
        default=500,
        help='Target chunk size in words (default: 500)'
    )
    parser.add_argument(
        '--overlap',
        type=int,
        default=50,
        help='Overlap size in words (default: 50)'
    )
    parser.add_argument(
        '--output',
        default='output',
        help='Output directory (default: output/)'
    )

    args = parser.parse_args()

    # Create orchestrator
    orchestrator = OrchestratorAgent(
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        output_dir=args.output
    )

    # Process directory
    result = orchestrator.process_directory(args.directory)

    # Exit with appropriate code
    sys.exit(0 if result['success'] else 1)


if __name__ == '__main__':
    main()
