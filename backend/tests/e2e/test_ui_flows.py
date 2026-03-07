"""Playwright UI E2E tests. Requires backend and frontend running."""

import pytest

pytest.importorskip("playwright", reason="Run: pip install pytest-playwright && playwright install chromium")

from pathlib import Path

FRONTEND_URL = "http://localhost:13000"


@pytest.mark.e2e
class TestHomepage:
    """Homepage load tests."""

    def test_homepage_loads(self, page):
        """Homepage should load and display ResearchGraph."""
        page.goto(FRONTEND_URL)
        page.wait_for_load_state("networkidle")
        assert "ResearchGraph" in page.content()

    def test_welcome_message_displayed(self, page):
        """Welcome message should be visible when no messages."""
        page.goto(FRONTEND_URL)
        page.wait_for_load_state("networkidle")
        assert page.get_by_text("Welcome to ResearchGraph").is_visible()

    def test_chat_input_visible(self, page):
        """Chat input and send button should be visible."""
        page.goto(FRONTEND_URL)
        page.wait_for_load_state("networkidle")
        textarea = page.get_by_placeholder("Ask a question about research papers...")
        assert textarea.is_visible()
        assert page.get_by_role("button", name="Send").is_visible()


@pytest.mark.e2e
class TestSidebar:
    """Sidebar navigation tests."""

    def test_sidebar_has_papers_and_ingest_tabs(self, page):
        """Sidebar should have Papers and Ingest tabs."""
        page.goto(FRONTEND_URL)
        page.wait_for_load_state("networkidle")
        assert page.get_by_role("button", name="Papers").is_visible()
        assert page.get_by_role("button", name="Ingest").is_visible()

    def test_ingest_tab_shows_upload_ui(self, page):
        """Ingest tab should show PDF upload and arXiv input."""
        page.goto(FRONTEND_URL)
        page.wait_for_load_state("networkidle")
        page.get_by_role("button", name="Ingest").click()
        assert page.get_by_text("Upload PDF").is_visible()
        assert page.get_by_placeholder("e.g., 2401.00001").is_visible()


@pytest.mark.e2e
class TestPDFIngestionUI:
    """PDF ingestion UI tests."""

    def test_pdf_upload_flow(self, page):
        """PDF upload should show success message after ingestion."""
        page.goto(FRONTEND_URL)
        page.wait_for_load_state("networkidle")
        page.get_by_role("button", name="Ingest").click()

        sample_pdf = Path(__file__).parent.parent / "fixtures" / "sample_paper.pdf"
        if not sample_pdf.exists():
            pytest.skip("Sample PDF not found")

        file_input = page.locator('input[type="file"][accept=".pdf"]')
        file_input.set_input_files(str(sample_pdf))

        page.get_by_text("Paper ingested successfully").wait_for(timeout=120000)
        assert page.get_by_text("nodes and").is_visible()


@pytest.mark.e2e
class TestArxivIngestionUI:
    """arXiv ingestion UI tests."""

    def test_arxiv_ingestion_flow(self, page):
        """arXiv ingestion should show success message."""
        page.goto(FRONTEND_URL)
        page.wait_for_load_state("networkidle")
        page.get_by_role("button", name="Ingest").click()

        arxiv_input = page.get_by_placeholder("e.g., 2401.00001")
        arxiv_input.fill("1706.03762")
        arxiv_input.press("Enter")

        page.get_by_text("Paper ingested successfully").wait_for(timeout=120000)


@pytest.mark.e2e
class TestAskFlowUI:
    """Ask question UI flow tests."""

    def test_ask_question_shows_response(self, page):
        """Asking a question should display response."""
        page.goto(FRONTEND_URL)
        page.wait_for_load_state("networkidle")

        page.get_by_placeholder("Ask a question about research papers...").fill(
            "Find papers about transformers"
        )
        page.get_by_role("button", name="Send").click()

        page.locator("text=transformer").first.wait_for(state="visible", timeout=60000)


@pytest.mark.e2e
class TestGraphVisualization:
    """Graph visualization UI tests."""

    def test_show_graph_button_toggles_graph(self, page):
        """Show Graph button should toggle graph panel."""
        page.goto(FRONTEND_URL)
        page.wait_for_load_state("networkidle")

        show_graph_btn = page.get_by_role("button", name="Show Graph")
        assert show_graph_btn.is_visible()
        show_graph_btn.click()
        page.get_by_role("button", name="Hide Graph").wait_for()


@pytest.mark.e2e
class TestDeletionAndClearUI:
    """Deletion and Clear Database UI tests."""

    def test_delete_paper_flow(self, page):
        """Should be able to delete an ingested paper."""
        # First ingest a paper via arXiv to ensure we have one
        page.goto(FRONTEND_URL)
        page.wait_for_load_state("networkidle")
        page.get_by_role("button", name="Ingest").click()
        arxiv_input = page.get_by_placeholder("e.g., 2401.00001")
        arxiv_input.fill("1706.03762")
        arxiv_input.press("Enter")
        page.get_by_text("Paper ingested successfully").wait_for(timeout=120000)

        # Now go to Papers tab
        page.get_by_role("button", name="Papers").click()
        page.wait_for_load_state("networkidle")

        # Setup dialog handler to accept confirm
        page.on("dialog", lambda dialog: dialog.accept())

        # Find the paper in the list
        paper_card = page.locator("div[role='option']").first
        paper_card.wait_for(state="visible")
        
        title_element = paper_card.locator("h3")
        title_text = title_element.inner_text()
        
        # Hover to make delete button visible
        paper_card.hover()
        
        # Click the delete button
        delete_btn = paper_card.get_by_title("Delete paper")
        delete_btn.click()
        
        # Wait for the item to be removed
        page.locator(f"text={title_text}").wait_for(state="hidden", timeout=10000)

    def test_clear_database_flow(self, page):
        """Should be able to clear the entire database."""
        page.goto(FRONTEND_URL)
        page.wait_for_load_state("networkidle")
        
        # Accept the confirm dialog
        page.on("dialog", lambda dialog: dialog.accept())

        page.get_by_role("button", name="Ingest").click()
        
        # Click Clear Database
        clear_btn = page.get_by_role("button", name="Clear Database")
        clear_btn.click()
        
        # Wait for page reload
        page.wait_for_load_state("networkidle")
        
        # Go to papers and verify it's empty
        page.get_by_role("button", name="Papers").click()
        page.wait_for_load_state("networkidle")
        assert page.get_by_text("No papers found").is_visible()
