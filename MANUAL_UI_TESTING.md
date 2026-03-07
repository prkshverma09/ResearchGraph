# Manual UI Testing Guide

This guide describes how to run the ResearchGraph application locally and verify its functionality through the UI.

## 1. Setup Environment

To test the project manually, you need to run three components: SurrealDB (the database), the Python backend, and the Next.js frontend. 

You can run them by opening **three separate terminal windows** and running the following commands:

### Start the Database (SurrealDB)
In your first terminal, from the root of the project, start the database using Docker:
```bash
make db-up
```
*(When you're done testing, you can stop it later with `make db-down`)*

### Start the Backend
Open a second terminal, navigate to the backend directory, activate the virtual environment, and start the FastAPI server:
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 18001 --env-file .env --reload
```
*The backend will be running at **http://localhost:18001** (and you can view the API documentation at http://localhost:18001/docs).*

### Start the Frontend
Open a third terminal, navigate to the frontend directory, and start the Next.js development server. We need to pass the custom API URL and port so it connects to the backend properly:
```bash
cd frontend
NEXT_PUBLIC_API_URL=http://localhost:18001 npm run dev -- -p 13000
```

Once all three are running, open your browser and navigate to **http://localhost:13000** to use the application!

---

## 2. Expected Database State After E2E Tests

If you ran `./scripts/run-e2e-complete.sh` previously, you might expect to see papers in the UI. 

**However, the papers are not showing up because the E2E script runs `make db-down` or restarts the database fresh at the beginning of the test run, and the memory-based SurrealDB loses its data when stopped.**

SurrealDB in our `docker-compose.yml` is configured to run in memory:
`command: start --user root --pass root memory`

This means any papers ingested during the test run (like the `sample_paper.pdf` or the Arxiv paper `1706.03762`) were stored in RAM and disappeared when the database container was stopped or recreated.

---

## 3. Manual Testing Steps

To manually test the UI, follow these steps to ingest data and interact with it:

### Step 1: Ingest an Arxiv Paper
1. Click the **"Ingest"** tab in the left sidebar.
2. In the "Ingest from arXiv" section, enter a valid arXiv ID. 
   - *Example: `1706.03762` (Attention Is All You Need)*
3. Click **"Ingest"**.
4. Wait for the success message: `"Paper ingested successfully! Created X nodes and Y edges."`

### Step 2: Verify Search
1. Click the **"Papers"** tab in the left sidebar.
2. Search for a term related to the paper you just ingested (e.g., "Attention" or "Transformer").
3. You should see the paper appear in the search results.

### Step 3: Test the AI Assistant (Ask)
1. At the bottom of the main chat window, enter a question in the input box: `"Ask a question about research papers..."`
   - *Example: "What is the main contribution of the Attention is All You Need paper?"*
2. Click **"Send"**.
3. Verify that the AI streams a response back to you.

### Step 4: Test Graph Visualization
1. Click the **"Show Graph"** button in the top right corner.
2. The graph visualization panel should open.
3. Verify that you can see nodes (papers, authors, topics) and edges connecting them.