"""Graph construction module for converting entities to SurrealDB graph nodes and edges."""

import hashlib
import logging
import re
from typing import List, Optional
from app.models.domain import ExtractedEntities
from app.db.connection import SurrealDBManager

logger = logging.getLogger(__name__)


class GraphBuilder:
    """Builds SurrealDB graph nodes and edges from extracted entities."""
    
    def _generate_paper_id(self, title: str) -> str:
        """Generate deterministic paper ID from title.
        
        Args:
            title: Paper title
            
        Returns:
            SurrealDB record ID (e.g., "paper:abc123...")
        """
        # Normalize title: lowercase, strip whitespace
        normalized = title.lower().strip()
        # Generate hash
        hash_obj = hashlib.md5(normalized.encode('utf-8'))
        hash_hex = hash_obj.hexdigest()[:16]  # Use first 16 chars
        return f"paper:{hash_hex}"
    
    def _generate_author_id(self, name: str) -> str:
        """Generate deterministic author ID from name.
        
        Args:
            name: Author name
            
        Returns:
            SurrealDB record ID (e.g., "author:abc123...")
        """
        normalized = name.lower().strip()
        hash_obj = hashlib.md5(normalized.encode('utf-8'))
        hash_hex = hash_obj.hexdigest()[:16]
        return f"author:{hash_hex}"
    
    def _generate_topic_id(self, name: str) -> str:
        """Generate deterministic topic ID from name.
        
        Args:
            name: Topic name
            
        Returns:
            SurrealDB record ID (e.g., "topic:abc123...")
        """
        normalized = name.lower().strip()
        hash_obj = hashlib.md5(normalized.encode('utf-8'))
        hash_hex = hash_obj.hexdigest()[:16]
        return f"topic:{hash_hex}"
    
    def _generate_institution_id(self, name: str) -> str:
        """Generate deterministic institution ID from name.
        
        Args:
            name: Institution name
            
        Returns:
            SurrealDB record ID (e.g., "institution:abc123...")
        """
        normalized = name.lower().strip()
        hash_obj = hashlib.md5(normalized.encode('utf-8'))
        hash_hex = hash_obj.hexdigest()[:16]
        return f"institution:{hash_hex}"
    
    def build_paper_node(self, entities: ExtractedEntities) -> str:
        """Build SurrealQL CREATE statement for paper node.
        
        Args:
            entities: Extracted entities
            
        Returns:
            SurrealQL CREATE statement
        """
        paper_id = self._generate_paper_id(entities.title)
        
        # Build SET clause
        fields = [f"title = {self._escape_string(entities.title)}"]
        
        # Add optional fields if present
        if entities.year is not None:
            fields.append(f"year = {entities.year}")
        
        if entities.venue is not None:
            fields.append(f"venue = {self._escape_string(entities.venue)}")
        
        # Join fields
        set_clause = ", ".join(fields)
        
        return f"UPSERT {paper_id} SET {set_clause}"
    
    def build_author_nodes(self, entities: ExtractedEntities) -> List[str]:
        """Build SurrealQL CREATE statements for author nodes.
        
        Args:
            entities: Extracted entities
            
        Returns:
            List of SurrealQL CREATE statements
        """
        statements = []
        
        for author in entities.authors:
            author_id = self._generate_author_id(author.name)
            
            fields = [f"name = {self._escape_string(author.name)}"]
            
            if author.institution is not None:
                fields.append(f"institution = {self._escape_string(author.institution)}")
            
            set_clause = ", ".join(fields)
            statements.append(f"UPSERT {author_id} SET {set_clause}")
        
        return statements
    
    def build_topic_nodes(self, entities: ExtractedEntities) -> List[str]:
        """Build SurrealQL CREATE statements for topic nodes.
        
        Args:
            entities: Extracted entities
            
        Returns:
            List of SurrealQL CREATE statements
        """
        statements = []
        
        for topic in entities.topics:
            topic_id = self._generate_topic_id(topic)
            set_clause = f"name = {self._escape_string(topic)}"
            statements.append(f"UPSERT {topic_id} SET {set_clause}")
        
        return statements
    
    def build_institution_nodes(self, entities: ExtractedEntities) -> List[str]:
        """Build SurrealQL CREATE statements for institution nodes.
        
        Args:
            entities: Extracted entities
            
        Returns:
            List of SurrealQL CREATE statements
        """
        statements = []
        
        for institution in entities.institutions:
            institution_id = self._generate_institution_id(institution)
            set_clause = f"name = {self._escape_string(institution)}"
            statements.append(f"UPSERT {institution_id} SET {set_clause}")
        
        return statements
    
    def build_authored_by_edges(
        self,
        paper_id: str,
        author_ids: List[str]
    ) -> List[str]:
        """Build SurrealQL RELATE statements for authored_by edges.
        
        Args:
            paper_id: Paper record ID
            author_ids: List of author record IDs
            
        Returns:
            List of SurrealQL RELATE statements
        """
        statements = []
        
        for author_id in author_ids:
            statements.append(
                f"RELATE {paper_id}->authored_by->{author_id}"
            )
        
        return statements
    
    def build_cites_edges(
        self,
        paper_id: str,
        cited_paper_ids: List[str]
    ) -> List[str]:
        """Build SurrealQL RELATE statements for cites edges.
        
        Args:
            paper_id: Paper record ID
            cited_paper_ids: List of cited paper record IDs
            
        Returns:
            List of SurrealQL RELATE statements
        """
        statements = []
        
        for cited_id in cited_paper_ids:
            statements.append(
                f"RELATE {paper_id}->cites->{cited_id}"
            )
        
        return statements

    def build_citation_stub_nodes(
        self,
        cited_titles: List[str]
    ) -> List[str]:
        """Build UPSERT statements for citation stub paper nodes.

        This ensures cited paper targets exist and can be rendered in graph traversal.
        """
        statements = []
        for title in cited_titles:
            if not title or not title.strip():
                continue
            cited_id = self._generate_paper_id(title)
            set_clause = f"title = {self._escape_string(title.strip())}"
            statements.append(f"UPSERT {cited_id} SET {set_clause}")
        return statements
    
    def build_belongs_to_edges(
        self,
        paper_id: str,
        topic_ids: List[str]
    ) -> List[str]:
        """Build SurrealQL RELATE statements for belongs_to edges.
        
        Args:
            paper_id: Paper record ID
            topic_ids: List of topic record IDs
            
        Returns:
            List of SurrealQL RELATE statements
        """
        statements = []
        
        for topic_id in topic_ids:
            statements.append(
                f"RELATE {paper_id}->belongs_to->{topic_id}"
            )
        
        return statements
    
    def build_affiliated_with_edge(
        self,
        author_id: str,
        institution_id: str
    ) -> str:
        """Build SurrealQL RELATE statement for affiliated_with edge.
        
        Args:
            author_id: Author record ID
            institution_id: Institution record ID
            
        Returns:
            SurrealQL RELATE statement
        """
        return f"RELATE {author_id}->affiliated_with->{institution_id}"
    
    def _escape_string(self, value: str) -> str:
        """Escape string for SurrealQL.
        
        Args:
            value: String value to escape
            
        Returns:
            Escaped string wrapped in quotes
        """
        # Escape single quotes by doubling them
        escaped = value.replace("'", "''")
        return f"'{escaped}'"


async def persist_graph(
    db_manager: SurrealDBManager,
    entities: ExtractedEntities
) -> str:
    """Persist graph nodes and edges to SurrealDB.
    
    This function:
    1. Generates all node creation statements
    2. Generates all edge creation statements
    3. Executes them in SurrealDB (with deduplication via deterministic IDs)
    
    Args:
        db_manager: SurrealDB manager instance
        entities: Extracted entities to persist
    """
    builder = GraphBuilder()
    
    # Generate paper node
    paper_id = builder._generate_paper_id(entities.title)
    paper_stmt = builder.build_paper_node(entities)
    
    # Generate author nodes and IDs
    author_stmts = builder.build_author_nodes(entities)
    author_ids = [
        builder._generate_author_id(author.name)
        for author in entities.authors
    ]
    
    # Generate topic nodes and IDs
    topic_stmts = builder.build_topic_nodes(entities)
    topic_ids = [
        builder._generate_topic_id(topic)
        for topic in entities.topics
    ]
    
    # Generate institution nodes and IDs
    institution_stmts = builder.build_institution_nodes(entities)
    institution_ids = [
        builder._generate_institution_id(inst)
        for inst in entities.institutions
    ]
    
    # Generate citation paper IDs (for papers that are cited)
    cited_paper_ids = [
        builder._generate_paper_id(citation)
        for citation in entities.citations
    ]
    citation_stub_stmts = builder.build_citation_stub_nodes(entities.citations)
    
    # Generate edges
    authored_by_stmts = builder.build_authored_by_edges(paper_id, author_ids)
    cites_stmts = builder.build_cites_edges(paper_id, cited_paper_ids)
    belongs_to_stmts = builder.build_belongs_to_edges(paper_id, topic_ids)
    
    # Generate affiliated_with edges
    affiliated_with_stmts = []
    for author in entities.authors:
        if author.institution:
            author_id = builder._generate_author_id(author.name)
            institution_id = builder._generate_institution_id(author.institution)
            affiliated_with_stmts.append(
                builder.build_affiliated_with_edge(author_id, institution_id)
            )
    
    # Collect all statements
    all_statements = [
        paper_stmt,
        *author_stmts,
        *topic_stmts,
        *institution_stmts,
        *citation_stub_stmts,
        *authored_by_stmts,
        *cites_stmts,
        *belongs_to_stmts,
        *affiliated_with_stmts,
    ]
    
    # Execute all statements
    # Node writes use UPSERT with deterministic IDs so repeated ingests enrich records.
    for statement in all_statements:
        try:
            relate_match = re.match(r"^\s*RELATE\s+(\S+)->([a-zA-Z_][a-zA-Z0-9_]*)->(\S+)\s*$", statement)
            if relate_match:
                source_id, relation_table, target_id = relate_match.groups()
                existing = await db_manager.execute(
                    f"SELECT * FROM {relation_table} WHERE in = {source_id} AND out = {target_id} LIMIT 1"
                )
                if existing:
                    continue
            await db_manager.execute(statement)
        except Exception as e:
            # Log error but continue - some nodes might already exist
            # SurrealDB will handle duplicates gracefully
            error_msg = str(e).lower()
            if "already exists" in error_msg or "duplicate" in error_msg:
                continue
            else:
                logger.error(f"Failed to execute statement: {statement}")
                logger.error(f"Error: {e}")
                raise
    
    logger.info(
        f"Persisted graph for paper '{entities.title}': "
        f"{len(author_stmts)} authors, {len(topic_stmts)} topics, "
        f"{len(institution_stmts)} institutions, {len(cites_stmts)} citations"
    )
    
    return paper_id
