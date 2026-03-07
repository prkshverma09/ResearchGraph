"""Unit tests for domain models."""

import pytest
from datetime import datetime


def test_paper_model_creation():
    """Paper domain model should be creatable with required fields."""
    from app.models.domain import Paper
    
    paper = Paper(
        title="Test Paper",
        abstract="This is a test abstract.",
        year=2024
    )
    
    assert paper.title == "Test Paper"
    assert paper.abstract == "This is a test abstract."
    assert paper.year == 2024
    assert paper.venue is None  # Optional field


def test_author_model_creation():
    """Author domain model should be creatable with required fields."""
    from app.models.domain import Author
    
    author = Author(name="John Doe")
    
    assert author.name == "John Doe"
    assert author.institution is None  # Optional field


def test_paper_model_with_optional_fields():
    """Paper model should handle optional fields correctly."""
    from app.models.domain import Paper
    
    paper = Paper(
        title="Test Paper",
        abstract="Abstract",
        year=2024,
        venue="ICLR",
        doi="10.1234/test",
        arxiv_id="2401.00001"
    )
    
    assert paper.venue == "ICLR"
    assert paper.doi == "10.1234/test"
    assert paper.arxiv_id == "2401.00001"


def test_topic_model_creation():
    """Topic domain model should be creatable."""
    from app.models.domain import Topic
    
    topic = Topic(name="Machine Learning")
    assert topic.name == "Machine Learning"


def test_institution_model_creation():
    """Institution domain model should be creatable."""
    from app.models.domain import Institution
    
    institution = Institution(name="MIT", country="USA")
    assert institution.name == "MIT"
    assert institution.country == "USA"


def test_domain_models_serialization():
    """Domain models should serialize to dict."""
    from app.models.domain import Paper, Author
    
    paper = Paper(title="Test", abstract="Abstract", year=2024)
    paper_dict = paper.model_dump()
    
    assert isinstance(paper_dict, dict)
    assert paper_dict["title"] == "Test"
    assert paper_dict["year"] == 2024
