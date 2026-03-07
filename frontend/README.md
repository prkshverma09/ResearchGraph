# ResearchGraph Frontend

Next.js 14 frontend for the ResearchGraph Assistant application.

## Features

- **Chat Interface**: Interactive chat with the research agent
- **Paper List**: Browse and search ingested papers
- **Graph Visualization**: Interactive citation/author graph visualization
- **Ingestion Panel**: Upload PDFs or ingest papers from arXiv
- **Dark/Light Mode**: Theme support with system preference detection
- **Session Management**: Resume previous research sessions
- **Streaming Responses**: Real-time streaming of agent responses

## Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn

### Installation

```bash
cd frontend
npm install
```

### Development

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Build

```bash
npm run build
npm start
```

## Configuration

Set the backend API URL via environment variable:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

Or create a `.env.local` file:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Project Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── components/      # React components
│   │   │   ├── ChatMessage.tsx
│   │   │   ├── PaperList.tsx
│   │   │   ├── GraphVisualization.tsx
│   │   │   ├── IngestionPanel.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── ThemeProvider.tsx
│   │   ├── layout.tsx        # Root layout
│   │   ├── page.tsx          # Main chat page
│   │   └── globals.css       # Global styles
│   └── lib/
│       └── api.ts            # API client utilities
├── package.json
├── next.config.js
├── tailwind.config.js
└── tsconfig.json
```

## Components

### ChatMessage
Displays user and assistant messages with source citations.

### PaperList
Sidebar component showing ingested papers with search functionality.

### GraphVisualization
Interactive force-directed graph visualization of paper relationships using react-force-graph.

### IngestionPanel
Upload PDFs or ingest papers from arXiv with drag-and-drop support.

### Sidebar
Collapsible sidebar with tabs for papers and ingestion.

## API Client

The `api.ts` module provides typed wrappers for all backend endpoints:

- `api.search()` - Vector similarity search
- `api.ask()` - Ask research agent (non-streaming)
- `api.askStream()` - Ask research agent (streaming)
- `api.ingestPDF()` - Upload and ingest PDF
- `api.ingestArxiv()` - Ingest from arXiv
- `api.getCitationPath()` - Get citation path between papers
- `api.getPaperWithRelations()` - Get paper with graph relations
- `api.getGraphStats()` - Get graph statistics
- `api.createSession()` - Create new session
- `api.getSession()` - Get session data
- `api.listSessions()` - List all sessions

## Technologies

- **Next.js 14** - React framework with App Router
- **TypeScript** - Type safety
- **Tailwind CSS** - Utility-first CSS
- **react-force-graph** - Graph visualization
- **React Hooks** - State management
