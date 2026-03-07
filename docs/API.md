# ResearchGraph Assistant API Documentation

**Base URL:** `http://localhost:8001`  
**API Version:** 0.1.0  
**Format:** JSON

## Table of Contents

- [Health Check](#health-check)
- [Ingestion Endpoints](#ingestion-endpoints)
- [Search Endpoints](#search-endpoints)
- [Agent Endpoints](#agent-endpoints)
- [Session Endpoints](#session-endpoints)
- [Graph Endpoints](#graph-endpoints)
- [Error Responses](#error-responses)

---

## Health Check

### GET `/api/health`

Check the health status of the API and database connection.

**Response:**
```json
{
  "status": "ok",
  "db_connected": true
}
```

**Status Codes:**
- `200 OK`: Service is healthy
- `500 Internal Server Error`: Service error

**Example:**
```bash
curl http://localhost:8001/api/health
```

---

## Ingestion Endpoints

### POST `/api/ingest/pdf`

Upload and ingest a PDF file.

**Request:**
- **Content-Type:** `multipart/form-data`
- **Body:** PDF file upload

**Response:**
```json
{
  "paper_id": "paper:1706.03762",
  "status": "success",
  "nodes_created": 15,
  "edges_created": 42,
  "error": null
}
```

**Status Codes:**
- `200 OK`: Ingestion successful
- `400 Bad Request`: File is not a PDF
- `500 Internal Server Error`: Ingestion failed

**Example:**
```bash
curl -X POST http://localhost:8001/api/ingest/pdf \
  -F "file=@sample_paper.pdf"
```

**Error Response:**
```json
{
  "detail": "File must be a PDF"
}
```

---

### POST `/api/ingest/arxiv`

Ingest a paper from arXiv by ID.

**Request:**
```json
{
  "arxiv_id": "1706.03762"
}
```

**Response:**
```json
{
  "paper_id": "paper:1706.03762",
  "status": "success",
  "nodes_created": 12,
  "edges_created": 35,
  "error": null
}
```

**Status Codes:**
- `200 OK`: Ingestion successful
- `500 Internal Server Error`: Ingestion failed (paper not found, API error, etc.)

**Example:**
```bash
curl -X POST http://localhost:8001/api/ingest/arxiv \
  -H "Content-Type: application/json" \
  -d '{"arxiv_id": "1706.03762"}'
```

**Error Response:**
```json
{
  "detail": "Ingestion failed: Paper not found on arXiv"
}
```

---

### POST `/api/ingest/semantic-scholar`

Ingest a paper from Semantic Scholar by ID.

**Request:**
```json
{
  "paper_id": "CorpusID:12345678"
}
```

**Response:**
```json
{
  "paper_id": "paper:CorpusID:12345678",
  "status": "success",
  "nodes_created": 10,
  "edges_created": 28,
  "error": null
}
```

**Status Codes:**
- `200 OK`: Ingestion successful
- `500 Internal Server Error`: Ingestion failed

**Example:**
```bash
curl -X POST http://localhost:8001/api/ingest/semantic-scholar \
  -H "Content-Type: application/json" \
  -d '{"paper_id": "CorpusID:12345678"}'
```

---

## Search Endpoints

### POST `/api/search`

Perform vector similarity search on paper chunks.

**Request:**
```json
{
  "query": "transformers attention mechanism",
  "top_k": 5
}
```

**Parameters:**
- `query` (string, required): Search query text
- `top_k` (integer, optional): Number of results to return (1-50, default: 5)

**Response:**
```json
{
  "papers": [
    {
      "title": "Attention Is All You Need",
      "abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...",
      "paper_id": "paper:1706.03762",
      "relevance_score": 0.92
    },
    {
      "title": "BERT: Pre-training of Deep Bidirectional Transformers",
      "abstract": "We introduce BERT, a method for pre-training language representations...",
      "paper_id": "paper:1810.04805",
      "relevance_score": 0.87
    }
  ]
}
```

**Status Codes:**
- `200 OK`: Search successful
- `500 Internal Server Error`: Search failed

**Example:**
```bash
curl -X POST http://localhost:8001/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "transformers", "top_k": 5}'
```

---

## Agent Endpoints

### POST `/api/ask`

Ask the research agent a question (non-streaming).

**Request:**
```json
{
  "question": "Find papers about transformers",
  "session_id": "session:abc123"
}
```

**Parameters:**
- `question` (string, required): User's research question
- `session_id` (string, optional): Session ID for conversation continuity. If not provided, a new session is created.

**Response:**
```json
{
  "answer": "Based on the papers in the knowledge graph, here are the key papers about transformers:\n\n1. **Attention Is All You Need** (Vaswani et al., 2017) - Introduced the Transformer architecture...",
  "sources": [
    {
      "title": "Attention Is All You Need",
      "paper_id": "paper:1706.03762",
      "relevance_score": 0.92
    }
  ],
  "graph_paths": [
    [
      {
        "id": "paper:1706.03762",
        "title": "Attention Is All You Need"
      }
    ]
  ],
  "session_id": "session:abc123"
}
```

**Status Codes:**
- `200 OK`: Question processed successfully
- `500 Internal Server Error`: Agent processing failed

**Example:**
```bash
curl -X POST http://localhost:8001/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Find papers about transformers", "session_id": "test-session-123"}'
```

**Note:** This endpoint may fail with checkpoint errors (see Known Issues in README.md). The streaming endpoint below may be more reliable.

---

### POST `/api/ask/stream`

Ask the research agent a question with streaming response (Server-Sent Events).

**Request:**
```json
{
  "question": "What papers cite Attention Is All You Need?",
  "session_id": "session:abc123"
}
```

**Response:**
- **Content-Type:** `text/event-stream`
- **Format:** Server-Sent Events (SSE)

**Example:**
```bash
curl -X POST http://localhost:8001/api/ask/stream \
  -H "Content-Type: application/json" \
  -d '{"question": "Find papers about transformers"}' \
  --no-buffer
```

**SSE Event Format:**
```
data: {"type": "chunk", "content": "Based on"}
data: {"type": "chunk", "content": " the papers"}
data: {"type": "done", "session_id": "session:abc123"}
```

**Status Codes:**
- `200 OK`: Streaming started successfully
- `500 Internal Server Error`: Agent processing failed

---

## Session Endpoints

### POST `/api/sessions`

Create a new session.

**Request:**
```json
{
  "user_id": "user123"
}
```

**Parameters:**
- `user_id` (string, required): User identifier

**Response:**
```json
{
  "id": "session:abc123",
  "user_id": "user123",
  "created_at": "2026-03-07T10:00:00Z",
  "updated_at": "2026-03-07T10:00:00Z",
  "queries": [],
  "papers_explored": [],
  "notes": null
}
```

**Status Codes:**
- `200 OK`: Session created successfully
- `500 Internal Server Error`: Session creation failed

**Example:**
```bash
curl -X POST http://localhost:8001/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123"}'
```

---

### GET `/api/sessions/{session_id}`

Get a session by ID.

**Parameters:**
- `session_id` (path parameter, required): Session identifier

**Response:**
```json
{
  "id": "session:abc123",
  "user_id": "user123",
  "created_at": "2026-03-07T10:00:00Z",
  "updated_at": "2026-03-07T10:05:00Z",
  "queries": ["Find papers about transformers"],
  "papers_explored": ["paper:1706.03762"],
  "notes": null
}
```

**Status Codes:**
- `200 OK`: Session found
- `404 Not Found`: Session not found
- `500 Internal Server Error`: Server error

**Example:**
```bash
curl http://localhost:8001/api/sessions/session:abc123
```

---

### GET `/api/sessions`

List all sessions for a user.

**Query Parameters:**
- `user_id` (string, required): User identifier

**Response:**
```json
{
  "sessions": [
    {
      "id": "session:abc123",
      "user_id": "user123",
      "created_at": "2026-03-07T10:00:00Z",
      "updated_at": "2026-03-07T10:05:00Z",
      "queries": ["Find papers about transformers"],
      "papers_explored": ["paper:1706.03762"],
      "notes": null
    }
  ]
}
```

**Status Codes:**
- `200 OK`: Sessions retrieved successfully
- `500 Internal Server Error`: Server error

**Example:**
```bash
curl "http://localhost:8001/api/sessions?user_id=user123"
```

---

## Graph Endpoints

### GET `/api/graph/paper/{paper_id}`

Get a paper with its relations (authors, topics, citations).

**Parameters:**
- `paper_id` (path parameter, required): SurrealDB paper ID (e.g., `paper:1706.03762`)

**Response:**
```json
{
  "paper": {
    "id": "paper:1706.03762",
    "title": "Attention Is All You Need",
    "abstract": "The dominant sequence transduction models...",
    "year": 2017,
    "venue": "NIPS"
  },
  "authors": [
    {
      "id": "author:vaswani",
      "name": "Ashish Vaswani"
    }
  ],
  "topics": [
    {
      "id": "topic:transformers",
      "name": "Transformers"
    }
  ],
  "citations": [
    {
      "id": "paper:1810.04805",
      "title": "BERT: Pre-training of Deep Bidirectional Transformers"
    }
  ]
}
```

**Status Codes:**
- `200 OK`: Paper found
- `404 Not Found`: Paper not found
- `500 Internal Server Error`: Server error

**Example:**
```bash
curl http://localhost:8001/api/graph/paper/paper:1706.03762
```

---

### GET `/api/graph/stats`

Get graph statistics (counts of nodes and edges).

**Response:**
```json
{
  "papers": 150,
  "authors": 45,
  "topics": 23,
  "edges": 342
}
```

**Status Codes:**
- `200 OK`: Statistics retrieved successfully
- `500 Internal Server Error`: Server error

**Example:**
```bash
curl http://localhost:8001/api/graph/stats
```

---

### GET `/api/citation-path`

Find citation path between two papers.

**Query Parameters:**
- `paper_a` (string, required): Title or ID of first paper
- `paper_b` (string, required): Title or ID of second paper

**Response:**
```json
{
  "path": [
    {
      "id": "paper:1706.03762",
      "title": "Attention Is All You Need"
    },
    {
      "id": "paper:1810.04805",
      "title": "BERT: Pre-training of Deep Bidirectional Transformers"
    },
    {
      "id": "paper:2005.14165",
      "title": "Language Models are Few-Shot Learners"
    }
  ],
  "message": "Found citation path with 3 papers"
}
```

**Status Codes:**
- `200 OK`: Path found or no path exists
- `500 Internal Server Error`: Server error

**Example:**
```bash
curl "http://localhost:8001/api/citation-path?paper_a=Attention%20Is%20All%20You%20Need&paper_b=BERT"
```

**Note:** If no path exists, `path` will be an empty array and `message` will indicate no path was found.

---

## Error Responses

All endpoints may return error responses in the following format:

### 400 Bad Request
```json
{
  "detail": "File must be a PDF"
}
```

### 404 Not Found
```json
{
  "detail": "Session session:abc123 not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Search failed: Connection timeout"
}
```

**Common Error Scenarios:**

1. **Database Connection Error:**
   ```json
   {
     "detail": "Failed to connect to SurrealDB"
   }
   ```

2. **OpenAI API Error:**
   ```json
   {
     "detail": "OpenAI API error: Invalid API key"
   }
   ```

3. **Checkpoint Error (Known Issue):**
   ```json
   {
     "detail": "Failed to process question: TypeError: string indices must be integers, not 'str'"
   }
   ```
   See Known Issues in README.md for details.

4. **Validation Error:**
   ```json
   {
     "detail": [
       {
         "loc": ["body", "query"],
         "msg": "field required",
         "type": "value_error.missing"
       }
     ]
   }
   ```

---

## Rate Limiting

Currently, there are no rate limits enforced. However, consider:

- OpenAI API has rate limits (check your plan)
- SurrealDB connection pool limits
- Backend resource constraints

For production deployments, implement rate limiting middleware.

---

## Authentication

Currently, the API does not require authentication. For production:

1. Implement API key authentication
2. Add user authentication/authorization
3. Secure session management
4. Add CORS restrictions

---

## OpenAPI/Swagger Specification

The API follows OpenAPI 3.0 specification. To generate interactive documentation:

```bash
# FastAPI automatically generates OpenAPI schema at:
curl http://localhost:8001/openapi.json

# View Swagger UI at:
# http://localhost:8001/docs

# View ReDoc at:
# http://localhost:8001/redoc
```

---

## Versioning

Current API version: `0.1.0`

Future versions will use URL versioning:
- `/api/v1/...`
- `/api/v2/...`

---

## Support

For issues and questions:
- Check [README.md](../README.md) for troubleshooting
- Review [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) for development details
- See [E2E_TESTING_GUIDE.md](../E2E_TESTING_GUIDE.md) for testing
