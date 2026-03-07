#!/usr/bin/env python3
"""Create a simple test PDF for ingestion testing."""

import fitz  # PyMuPDF

def create_test_pdf(output_path: str = "test_paper.pdf"):
    """Create a simple academic-style test PDF."""
    
    # Create a new PDF document
    doc = fitz.open()
    
    # Page 1: Title and Abstract
    page1 = doc.new_page(width=595, height=842)  # A4 size
    
    # Title
    title_rect = fitz.Rect(50, 50, 545, 150)
    page1.insert_text(
        title_rect.tl,  # Top-left point
        "A Test Paper on Knowledge Graphs for AI Research",
        fontsize=18,
        fontname="helv",
        color=(0, 0, 0),
    )
    
    # Authors
    authors_rect = fitz.Rect(50, 160, 545, 200)
    page1.insert_text(
        authors_rect.tl,
        "John Doe, Jane Smith, Alice Johnson",
        fontsize=12,
        fontname="helv",
        color=(0.3, 0.3, 0.3),
    )
    
    # Abstract section
    abstract_text = """Abstract
    
This is a test paper designed for PDF ingestion testing in the ResearchGraph Assistant system. 
The paper discusses knowledge graphs and their application in AI research. Knowledge graphs 
provide a structured way to represent relationships between entities, making them valuable 
for semantic search and question answering systems.

This test document contains multiple sections including an introduction, methodology, 
results, and conclusions. It also includes citations to other papers to test citation 
extraction functionality."""

    abstract_rect = fitz.Rect(50, 220, 545, 400)
    page1.insert_textbox(
        abstract_rect,
        abstract_text,
        fontsize=11,
        fontname="helv",
        color=(0, 0, 0),
    )
    
    # Page 2: Introduction
    page2 = doc.new_page()
    
    intro_text = """1. Introduction

Knowledge graphs have become increasingly important in modern AI systems. They enable 
machines to understand relationships between concepts, entities, and facts. This paper 
explores how knowledge graphs can be used to enhance research paper discovery and 
question answering.

The main contributions of this work include:
- A novel approach to building knowledge graphs from research papers
- An efficient method for extracting relationships between papers
- A system for semantic search over research literature

2. Related Work

Several previous works have explored knowledge graphs for research papers. Vaswani et al. 
introduced the transformer architecture [1], which has become fundamental to modern NLP. 
Devlin et al. proposed BERT [2], a bidirectional encoder representation model. 
Brown et al. demonstrated the power of large language models with GPT-3 [3].

3. Methodology

Our approach involves three main steps:
1. Extract text and metadata from research papers
2. Identify entities such as authors, topics, and citations
3. Build a graph structure connecting these entities

The graph structure allows for efficient traversal and relationship discovery."""

    intro_rect = fitz.Rect(50, 50, 545, 750)
    page2.insert_textbox(
        intro_rect,
        intro_text,
        fontsize=11,
        fontname="helv",
        color=(0, 0, 0),
    )
    
    # Page 3: Results and Citations
    page3 = doc.new_page()
    
    results_text = """4. Results

Our experiments show that knowledge graphs significantly improve search relevance 
compared to traditional keyword-based search. The system successfully extracts 
relationships between papers, authors, and topics.

5. Conclusions

Knowledge graphs provide a powerful framework for organizing and searching 
research literature. Future work will explore more sophisticated relationship 
extraction and graph traversal algorithms.

References

[1] Vaswani, A., et al. "Attention Is All You Need." NIPS 2017.
[2] Devlin, J., et al. "BERT: Pre-training of Deep Bidirectional Transformers." 
    NAACL 2019.
[3] Brown, T., et al. "Language Models are Few-Shot Learners." NeurIPS 2020.
[4] Radford, A., et al. "GPT-4 Technical Report." OpenAI 2023."""

    results_rect = fitz.Rect(50, 50, 545, 750)
    page3.insert_textbox(
        results_rect,
        results_text,
        fontsize=11,
        fontname="helv",
        color=(0, 0, 0),
    )
    
    # Save the document
    doc.save(output_path)
    doc.close()
    
    print(f"✓ Created test PDF: {output_path}")
    print(f"  Pages: 3")
    print(f"  Contains: Title, Abstract, Introduction, Methodology, Results, Citations")


if __name__ == "__main__":
    import sys
    output_file = sys.argv[1] if len(sys.argv) > 1 else "test_paper.pdf"
    create_test_pdf(output_file)
