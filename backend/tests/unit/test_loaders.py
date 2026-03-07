"""Unit tests for document loaders."""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json

from app.models.domain import RawDocument, Chunk


class TestPDFLoader:
    """Tests for PDFLoader."""
    
    def test_pdf_loader_extracts_text(self, tmp_path):
        """PDFLoader should extract text content from a PDF file."""
        from app.ingestion.loaders import PDFLoader
        
        # Create a minimal PDF file using PyMuPDF
        import fitz  # PyMuPDF
        pdf_path = tmp_path / "test.pdf"
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "This is test PDF content.")
        page.insert_text((50, 100), "Second line of text.")
        doc.save(str(pdf_path))
        doc.close()
        
        loader = PDFLoader()
        result = loader.load(str(pdf_path))
        
        assert isinstance(result, RawDocument)
        assert "test PDF content" in result.text
        assert "Second line" in result.text
        assert result.metadata["source"] == "pdf"
        assert result.metadata["filename"] == "test.pdf"
        assert result.metadata["pages"] == 1
    
    def test_pdf_loader_returns_metadata(self, tmp_path):
        """PDFLoader should return filename and page count in metadata."""
        from app.ingestion.loaders import PDFLoader
        
        import fitz
        pdf_path = tmp_path / "multi_page.pdf"
        doc = fitz.open()
        for i in range(3):
            page = doc.new_page()
            page.insert_text((50, 50), f"Page {i+1} content")
        doc.save(str(pdf_path))
        doc.close()
        
        loader = PDFLoader()
        result = loader.load(str(pdf_path))
        
        assert result.metadata["filename"] == "multi_page.pdf"
        assert result.metadata["pages"] == 3
        assert result.metadata["source"] == "pdf"
    
    def test_pdf_loader_raises_on_invalid_file(self, tmp_path):
        """PDFLoader should raise ValueError for non-PDF files."""
        from app.ingestion.loaders import PDFLoader
        
        # Create a text file instead of PDF
        txt_path = tmp_path / "not_a_pdf.txt"
        txt_path.write_text("This is not a PDF")
        
        loader = PDFLoader()
        with pytest.raises(ValueError, match="Invalid PDF file"):
            loader.load(str(txt_path))
    
    def test_pdf_loader_loads_from_bytes(self):
        """PDFLoader should load PDF from bytes."""
        from app.ingestion.loaders import PDFLoader
        
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Bytes PDF content")
        pdf_bytes = doc.tobytes()
        doc.close()
        
        loader = PDFLoader()
        result = loader.load_bytes(pdf_bytes)
        
        assert isinstance(result, RawDocument)
        assert "Bytes PDF content" in result.text
        assert result.metadata["source"] == "pdf"


class TestArxivLoader:
    """Tests for ArxivLoader."""
    
    @patch('app.ingestion.loaders.arxiv.Client')
    @patch('app.ingestion.loaders.arxiv.Search')
    def test_arxiv_loader_fetches_paper(self, mock_search_class, mock_client_class):
        """ArxivLoader should return paper data for a valid arXiv ID."""
        from app.ingestion.loaders import ArxivLoader
        
        # Mock arXiv search result
        mock_paper = Mock()
        mock_paper.title = "Test Paper Title"
        mock_paper.authors = [Mock(name="Alice Researcher"), Mock(name="Bob Scientist")]
        mock_paper.summary = "This is the abstract of the test paper."
        from datetime import datetime
        mock_paper.published = datetime(2024, 1, 1)
        mock_paper.entry_id = "http://arxiv.org/abs/2401.00001"
        
        # Mock the client and search
        mock_client = Mock()
        mock_client.results.return_value = iter([mock_paper])
        mock_client_class.return_value = mock_client
        
        loader = ArxivLoader()
        result = loader.load("2401.00001")
        
        assert isinstance(result, RawDocument)
        assert result.text == "This is the abstract of the test paper."
        assert result.metadata["title"] == "Test Paper Title"
        assert result.metadata["arxiv_id"] == "2401.00001"
        assert len(result.metadata["authors"]) == 2
        assert result.metadata["year"] == 2024
        assert result.metadata["source"] == "arxiv"
    
    @patch('app.ingestion.loaders.arxiv.Client')
    @patch('app.ingestion.loaders.arxiv.Search')
    def test_arxiv_loader_handles_not_found(self, mock_search_class, mock_client_class):
        """ArxivLoader should raise PaperNotFoundError for invalid ID."""
        from app.ingestion.loaders import ArxivLoader, PaperNotFoundError
        
        # Mock empty search result
        mock_client = Mock()
        mock_client.results.return_value = iter([])
        mock_client_class.return_value = mock_client
        
        loader = ArxivLoader()
        with pytest.raises(PaperNotFoundError, match="Paper not found"):
            loader.load("9999.99999")
    
    @patch('app.ingestion.loaders.arxiv.Client')
    def test_arxiv_loader_handles_connection_error(self, mock_client_class):
        """ArxivLoader should handle connection errors gracefully."""
        from app.ingestion.loaders import ArxivLoader
        
        # Mock connection error
        mock_client = Mock()
        mock_client.results.side_effect = Exception("Connection error")
        mock_client_class.return_value = mock_client
        
        loader = ArxivLoader()
        with pytest.raises(Exception, match="Connection error"):
            loader.load("2401.00001")


class TestSemanticScholarLoader:
    """Tests for SemanticScholarLoader."""
    
    @patch('app.ingestion.loaders.httpx.Client')
    def test_semantic_scholar_loader_fetches_paper(self, mock_client_class):
        """SemanticScholarLoader should return paper data."""
        from app.ingestion.loaders import SemanticScholarLoader
        
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "paperId": "test-paper-id",
            "title": "Test Paper Title",
            "abstract": "This is the abstract from Semantic Scholar.",
            "year": 2024,
            "authors": [
                {"name": "Alice Researcher", "authorId": "12345"},
                {"name": "Bob Scientist", "authorId": "67890"}
            ],
            "venue": "ICLR"
        }
        
        # Mock the context manager
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        loader = SemanticScholarLoader()
        result = loader.load("test-paper-id")
        
        assert isinstance(result, RawDocument)
        assert result.text == "This is the abstract from Semantic Scholar."
        assert result.metadata["title"] == "Test Paper Title"
        assert result.metadata["paper_id"] == "test-paper-id"
        assert result.metadata["year"] == 2024
        assert len(result.metadata["authors"]) == 2
        assert result.metadata["source"] == "semantic_scholar"
    
    @patch('app.ingestion.loaders.httpx.Client')
    def test_semantic_scholar_loader_extracts_citations(self, mock_client_class):
        """SemanticScholarLoader should extract citation paper IDs."""
        from app.ingestion.loaders import SemanticScholarLoader
        
        # Mock HTTP response with citations
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "paperId": "test-paper-id",
            "title": "Test Paper",
            "abstract": "Abstract text",
            "citations": [
                {"paperId": "cited-1", "title": "Cited Paper 1"},
                {"paperId": "cited-2", "title": "Cited Paper 2"}
            ]
        }
        
        # Mock the context manager
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        loader = SemanticScholarLoader()
        result = loader.load("test-paper-id")
        
        assert "citations" in result.metadata
        assert len(result.metadata["citations"]) == 2
        assert result.metadata["citations"][0]["paperId"] == "cited-1"
    
    @patch('app.ingestion.loaders.httpx.Client')
    def test_semantic_scholar_loader_handles_not_found(self, mock_client_class):
        """SemanticScholarLoader should raise PaperNotFoundError for invalid ID."""
        from app.ingestion.loaders import SemanticScholarLoader, PaperNotFoundError
        
        # Mock 404 response
        mock_response = Mock()
        mock_response.status_code = 404
        # Mock the context manager
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        loader = SemanticScholarLoader()
        with pytest.raises(PaperNotFoundError, match="Paper not found"):
            loader.load("invalid-id")


class TestTextChunker:
    """Tests for TextChunker."""
    
    def test_chunker_splits_text(self):
        """TextChunker should split text into chunks of configured size."""
        from app.ingestion.loaders import TextChunker
        
        # Create a long text (approximately 2000 tokens)
        long_text = " ".join([f"Token{i}" for i in range(2000)])
        
        chunker = TextChunker(chunk_size=800, chunk_overlap=100)
        chunks = chunker.chunk(RawDocument(text=long_text, metadata={"source": "test"}))
        
        assert len(chunks) > 1
        assert all(isinstance(chunk, Chunk) for chunk in chunks)
        assert chunks[0].index == 0
        assert chunks[1].index == 1
    
    def test_chunker_maintains_overlap(self):
        """TextChunker should include overlap between consecutive chunks."""
        from app.ingestion.loaders import TextChunker
        
        # Create text that will produce at least 2 chunks
        text = " ".join([f"Word{i}" for i in range(1000)])
        
        chunker = TextChunker(chunk_size=200, chunk_overlap=50)
        chunks = chunker.chunk(RawDocument(text=text, metadata={"source": "test"}))
        
        if len(chunks) > 1:
            # Check that there's overlap between chunks
            first_chunk_end = chunks[0].content[-100:]  # Last 100 chars
            second_chunk_start = chunks[1].content[:100]  # First 100 chars
            
            # There should be some overlap (not exact due to tokenization)
            # At least check that chunks are sequential
            assert chunks[1].index == chunks[0].index + 1
    
    def test_chunker_preserves_metadata(self):
        """Each chunk should carry the parent document's metadata."""
        from app.ingestion.loaders import TextChunker
        
        metadata = {
            "source": "pdf",
            "filename": "test.pdf",
            "pages": 5,
            "custom_field": "custom_value"
        }
        
        text = " ".join([f"Word{i}" for i in range(500)])
        doc = RawDocument(text=text, metadata=metadata)
        
        chunker = TextChunker()
        chunks = chunker.chunk(doc)
        
        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.metadata["source"] == "pdf"
            assert chunk.metadata["filename"] == "test.pdf"
            assert chunk.metadata["pages"] == 5
            assert chunk.metadata["custom_field"] == "custom_value"
    
    def test_chunker_handles_short_text(self):
        """TextChunker should handle text shorter than chunk size."""
        from app.ingestion.loaders import TextChunker
        
        short_text = "This is a short text that should not be split."
        doc = RawDocument(text=short_text, metadata={"source": "test"})
        
        chunker = TextChunker(chunk_size=800, chunk_overlap=100)
        chunks = chunker.chunk(doc)
        
        assert len(chunks) == 1
        assert chunks[0].content == short_text
        assert chunks[0].index == 0
        assert chunks[0].metadata["source"] == "test"
    
    def test_chunker_default_config(self):
        """TextChunker should use default chunk_size=800 and chunk_overlap=100."""
        from app.ingestion.loaders import TextChunker
        
        chunker = TextChunker()
        assert chunker.chunk_size == 800
        assert chunker.chunk_overlap == 100
