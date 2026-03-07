#!/usr/bin/env python3
"""Create a minimal test PDF for E2E testing."""

import fitz  # PyMuPDF

CONTENT = """
Attention Mechanisms in Deep Learning

Authors: Alice Researcher (MIT), Bob Scientist (Stanford University)

Abstract:
We present a comprehensive study of attention mechanisms in deep learning models.
Our work builds upon the foundational "Attention Is All You Need" paper by Vaswani et al.
We explore how transformers have revolutionized natural language processing and
computer vision. Key contributions include analysis of self-attention, multi-head
attention, and positional encodings. We cite related work including BERT, GPT-3,
and Vision Transformers. Our experiments demonstrate improved performance on
standard benchmarks. This research was conducted at MIT and Stanford.

Keywords: transformers, attention, deep learning, neural networks, NLP

1. Introduction
Attention mechanisms have become central to modern deep learning. The transformer
architecture introduced in "Attention Is All You Need" (Vaswani et al., 2017)
has enabled unprecedented progress in natural language processing.

2. Related Work
Our work builds on several key papers: BERT (Devlin et al.), GPT-3 (Brown et al.),
and Vision Transformers (Dosovitskiy et al.). We also reference graph neural
networks and reinforcement learning literature.

3. Method
We implement a standard transformer encoder with 6 layers, 8 attention heads,
and 512-dimensional embeddings. We use cosine similarity for attention scoring.

4. Experiments
We evaluate on GLUE and SQuAD benchmarks. Our model achieves state-of-the-art
results on 8 of 9 GLUE tasks.

5. Conclusion
Attention mechanisms enable models to capture long-range dependencies effectively.
Future work will explore efficient attention variants and multimodal applications.

References:
- Vaswani et al. Attention Is All You Need. NeurIPS 2017.
- Devlin et al. BERT: Pre-training of Deep Bidirectional Transformers. NAACL 2019.
- Brown et al. Language Models are Few-Shot Learners. NeurIPS 2020.
"""


def create_test_pdf(output_path: str) -> None:
    """Create a minimal PDF with the given content."""
    doc = fitz.open()
    page = doc.new_page()
    rect = fitz.Rect(50, 50, 550, 750)
    page.insert_textbox(rect, CONTENT.strip(), fontsize=11, fontname="helv")
    doc.save(output_path)
    doc.close()
    print(f"Created test PDF at {output_path}")


if __name__ == "__main__":
    import sys
    output = sys.argv[1] if len(sys.argv) > 1 else "backend/tests/fixtures/sample_paper.pdf"
    create_test_pdf(output)
