"""Document loaders for extracting text from various sources."""

from pathlib import Path
from typing import Union, List
import fitz  # PyMuPDF
import arxiv
import httpx
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.models.domain import RawDocument, Chunk


class PaperNotFoundError(Exception):
    """Raised when a paper cannot be found."""
    pass


class PDFLoader:
    """Loader for extracting text from PDF files."""
    
    def load(self, file_path: Union[str, Path]) -> RawDocument:
        """Load text from a PDF file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            RawDocument with extracted text and metadata
            
        Raises:
            ValueError: If the file is not a valid PDF
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise ValueError(f"File not found: {file_path}")
        
        try:
            doc = fitz.open(str(file_path))
            text_parts = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text_parts.append(page.get_text())
            
            full_text = "\n".join(text_parts)
            
            metadata = {
                "source": "pdf",
                "filename": file_path.name,
                "pages": len(doc),
            }
            
            doc.close()
            
            return RawDocument(text=full_text, metadata=metadata)
            
        except Exception as e:
            raise ValueError(f"Invalid PDF file: {e}")
    
    def load_bytes(self, pdf_bytes: bytes) -> RawDocument:
        """Load text from PDF bytes.
        
        Args:
            pdf_bytes: PDF file content as bytes
            
        Returns:
            RawDocument with extracted text and metadata
            
        Raises:
            ValueError: If the bytes are not a valid PDF
        """
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            text_parts = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text_parts.append(page.get_text())
            
            full_text = "\n".join(text_parts)
            
            metadata = {
                "source": "pdf",
                "pages": len(doc),
            }
            
            doc.close()
            
            return RawDocument(text=full_text, metadata=metadata)
            
        except Exception as e:
            raise ValueError(f"Invalid PDF bytes: {e}")


class ArxivLoader:
    """Loader for fetching papers from arXiv."""
    
    def __init__(self):
        """Initialize the arXiv loader with a client."""
        self.client = arxiv.Client()
    
    def load(self, arxiv_id: str) -> RawDocument:
        """Load paper metadata and abstract from arXiv.
        
        Args:
            arxiv_id: arXiv paper ID (e.g., "2401.00001")
            
        Returns:
            RawDocument with abstract as text and paper metadata
            
        Raises:
            PaperNotFoundError: If the paper cannot be found
        """
        try:
            # Search for the paper by ID
            search = arxiv.Search(
                id_list=[arxiv_id],
                max_results=1
            )
            
            results = list(self.client.results(search))
            
            if not results:
                raise PaperNotFoundError(f"Paper not found: {arxiv_id}")
            
            paper = results[0]
            
            # Extract author names
            authors = [author.name for author in paper.authors]
            
            metadata = {
                "source": "arxiv",
                "title": paper.title,
                "arxiv_id": arxiv_id,
                "authors": authors,
                "published": str(paper.published) if paper.published else None,
                "year": paper.published.year if paper.published else None,
                "entry_id": paper.entry_id,
            }
            
            return RawDocument(text=paper.summary, metadata=metadata)
            
        except PaperNotFoundError:
            raise
        except Exception as e:
            raise PaperNotFoundError(f"Error fetching paper {arxiv_id}: {e}")


class SemanticScholarLoader:
    """Loader for fetching papers from Semantic Scholar API."""
    
    BASE_URL = "https://api.semanticscholar.org/graph/v1"
    
    def load(self, paper_id: str) -> RawDocument:
        """Load paper metadata and abstract from Semantic Scholar.
        
        Args:
            paper_id: Semantic Scholar paper ID
            
        Returns:
            RawDocument with abstract as text and paper metadata
            
        Raises:
            PaperNotFoundError: If the paper cannot be found
        """
        url = f"{self.BASE_URL}/paper/{paper_id}"
        params = {
            "fields": "title,abstract,year,authors,venue,citations.paperId,citations.title"
        }
        
        try:
            with httpx.Client() as client:
                response = client.get(url, params=params, timeout=30.0)
                
                if response.status_code == 404:
                    raise PaperNotFoundError(f"Paper not found: {paper_id}")
                
                response.raise_for_status()
                data = response.json()
            
            # Extract author names
            authors = []
            if "authors" in data:
                authors = [
                    {"name": author.get("name", ""), "authorId": author.get("authorId")}
                    for author in data.get("authors", [])
                ]
            
            # Extract citations
            citations = []
            if "citations" in data:
                citations = [
                    {"paperId": cit.get("paperId"), "title": cit.get("title")}
                    for cit in data.get("citations", [])
                    if cit.get("paperId")
                ]
            
            metadata = {
                "source": "semantic_scholar",
                "paper_id": paper_id,
                "title": data.get("title", ""),
                "year": data.get("year"),
                "venue": data.get("venue"),
                "authors": authors,
                "citations": citations,
            }
            
            abstract = data.get("abstract", "")
            if not abstract:
                abstract = ""  # Some papers may not have abstracts
            
            return RawDocument(text=abstract, metadata=metadata)
            
        except PaperNotFoundError:
            raise
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise PaperNotFoundError(f"Paper not found: {paper_id}")
            raise PaperNotFoundError(f"Error fetching paper {paper_id}: {e}")
        except Exception as e:
            raise PaperNotFoundError(f"Error fetching paper {paper_id}: {e}")


class TextChunker:
    """Splits text into chunks using LangChain's RecursiveCharacterTextSplitter."""
    
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 100):
        """Initialize the text chunker.
        
        Args:
            chunk_size: Target size of each chunk in tokens
            chunk_overlap: Number of tokens to overlap between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Initialize LangChain text splitter
        # Note: chunk_size and chunk_overlap are approximate in characters
        # LangChain uses tiktoken for token counting, but we approximate with characters
        # A rough estimate: 1 token ≈ 4 characters
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size * 4,  # Approximate character count
            chunk_overlap=chunk_overlap * 4,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
    
    def chunk(self, document: RawDocument) -> List[Chunk]:
        """Split a RawDocument into chunks.
        
        Args:
            document: RawDocument to chunk
            
        Returns:
            List of Chunk objects with content, index, and metadata
        """
        # Split the text
        text_chunks = self.splitter.split_text(document.text)
        
        # Create Chunk objects
        chunks = []
        for idx, text_chunk in enumerate(text_chunks):
            chunk = Chunk(
                content=text_chunk,
                index=idx,
                metadata=document.metadata.copy(),  # Preserve all metadata
            )
            chunks.append(chunk)
        
        return chunks
