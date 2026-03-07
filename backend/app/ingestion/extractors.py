"""Entity extraction module using LLM."""

from typing import Optional, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from app.models.domain import ExtractedEntities, ExtractedAuthor
from app.config import settings


class EntityExtractor:
    """Extracts structured entities from paper text using LLM."""
    
    def __init__(self, model_name: str = "gpt-4o-mini"):
        """Initialize the entity extractor.
        
        Args:
            model_name: OpenAI model to use for extraction.
        """
        self.llm = ChatOpenAI(
            model=model_name,
            openai_api_key=settings.openai_api_key,
            temperature=0.0
        )
        self.structured_llm = self.llm.with_structured_output(ExtractedEntities)
        
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at extracting structured information from academic papers.
Extract the following entities from the provided text:
- Title: The paper title
- Authors: List of authors with their names and institutions (if mentioned)
- Topics: Research topics, keywords, or subject areas
- Institutions: Universities, companies, or research organizations mentioned
- Citations: Titles or identifiers of papers referenced in the text
- Year: Publication year (if mentioned)
- Venue: Conference or journal name (if mentioned)
- Key Findings: Main contributions or findings of the paper

Return structured data following the ExtractedEntities schema."""),
            ("human", "Extract entities from the following paper text:\n\n{text}")
        ])
    
    async def extract(
        self, 
        text: str, 
        existing_metadata: Optional[Dict[str, Any]] = None
    ) -> ExtractedEntities:
        """Extract entities from paper text.
        
        Args:
            text: Paper text to extract entities from.
            existing_metadata: Optional existing metadata to merge with extracted entities.
            
        Returns:
            ExtractedEntities object with extracted information.
            
        Raises:
            ValueError: If text is empty or whitespace only.
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        # Format prompt with text
        prompt = self.prompt_template.format_messages(text=text)
        
        # Call LLM with structured output
        extracted = await self.structured_llm.ainvoke(prompt)
        
        # Merge with existing metadata if provided
        if existing_metadata:
            extracted = self._merge_metadata(extracted, existing_metadata)
        
        return extracted
    
    def _merge_metadata(
        self, 
        extracted: ExtractedEntities, 
        existing_metadata: Dict[str, Any]
    ) -> ExtractedEntities:
        """Merge extracted entities with existing metadata.
        
        Existing metadata takes precedence for fields that are present.
        Authors are merged (both existing and extracted).
        
        Args:
            extracted: LLM-extracted entities.
            existing_metadata: Existing metadata dictionary.
            
        Returns:
            Merged ExtractedEntities.
        """
        merged_authors = []
        
        # Add existing authors if present
        if "authors" in existing_metadata:
            for author_data in existing_metadata["authors"]:
                if isinstance(author_data, dict):
                    merged_authors.append(ExtractedAuthor(
                        name=author_data.get("name", ""),
                        institution=author_data.get("institution")
                    ))
                elif isinstance(author_data, ExtractedAuthor):
                    merged_authors.append(author_data)
        
        # Add extracted authors (avoid duplicates by name)
        existing_names = {author.name.lower() for author in merged_authors}
        for author in extracted.authors:
            if author.name.lower() not in existing_names:
                merged_authors.append(author)
                existing_names.add(author.name.lower())
        
        # Build merged entities
        return ExtractedEntities(
            title=existing_metadata.get("title", extracted.title),
            authors=merged_authors if merged_authors else extracted.authors,
            topics=existing_metadata.get("topics", extracted.topics) if "topics" in existing_metadata else extracted.topics,
            institutions=existing_metadata.get("institutions", extracted.institutions) if "institutions" in existing_metadata else extracted.institutions,
            citations=existing_metadata.get("citations", extracted.citations) if "citations" in existing_metadata else extracted.citations,
            year=existing_metadata.get("year", extracted.year),
            venue=existing_metadata.get("venue", extracted.venue),
            key_findings=existing_metadata.get("key_findings", extracted.key_findings) if "key_findings" in existing_metadata else extracted.key_findings
        )
