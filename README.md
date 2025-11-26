# Code Graph Explorer

A full-stack demo focused on AST-based code graph indexing and visualization. It features a FastAPI backend, a Next.js frontend, and Neo4j to store and explore code entities and relationships. The GraphRAG layer answers structural queries about the codebase (e.g., calls, renders, imports).

## Prerequisites
- Python 3.11+
- Node.js 18+
- Neo4j 5.x

## Backend (FastAPI)
- `cd backend`
- `python -m venv venv`
- `source venv/bin/activate` (Windows: `venv\\Scripts\\activate`)
- `pip install -r requirements.txt`
- Ensure Neo4j is running and env vars are set
- Start API: `./venv/bin/uvicorn app.main:app --reload --port 8000`

The API is served at `http://localhost:8000` with CORS allowed for `http://localhost:3000`.

### Useful endpoints
- `POST /api/graph/import/ast` — import latest AST artifacts into Neo4j
- `GET /api/graph/export?dataset=code` — export code graph snapshot (nodes/edges)
- `GET /api/graph/neighbors/{node_id}` — direct neighbors of a node
- `POST /api/graphrag/query/local` — local GraphRAG search over code artifacts
- `POST /api/graphrag/query/global` — rank directory communities and summaries
- `POST /api/graphrag/query/drift` — compare segments by directory/period
- `GET /api/graphrag/debug/index` — verify GraphRAG artifacts are loaded

## Frontend (Next.js)
- `cd frontend`
- `npm install`
- `npm run dev`

The app runs at `http://localhost:3000`.

### Graph visualization
- Navigate to `http://localhost:3000/graph`
- Click a node to view details; use “Expand neighbors” to load and display connected nodes and edges
- Use minimap, zoom, and controls to explore

## GraphRAG Indexing (Code-Based)
- Inputs
  - Source is the frontend codebase: `frontend/src/**/*.{ts,tsx}`
  - The AST indexer parses components/functions/imports/hooks and builds a semantic graph
- Outputs
  - Default `GRAPHRAG_INDEX_PATH` is `graphrag-pipeline/output`.
  - Files produced under `<timestamp>/artifacts/`:
    - `create_final_text_units.json` (code snippets for local search)
    - `create_final_entities.json` (entities: File, Component, Function, Hook, Import, Export)
    - `create_final_relationships.json` (edges: CONTAINS, IMPORTS, CALLS, RENDERS, USES_HOOK, EXPORTS)
    - `create_final_community_reports.json` (directory-level summaries and top imports)
- Run the pipeline
  - `cd frontend`
  - `npm run index:frontend`
  - Console prints: `Artifacts written to: <path>`
- Backend indexing config
  - The backend reads the latest artifacts under `GRAPHRAG_INDEX_PATH`.
  - Verify: `GET /api/graphrag/debug/index`
  - Query: `POST /api/graphrag/query/local`

### Structural Query Examples
- Local:
  - `List functions that call graphAPI.` → returns caller functions (e.g., `GraphView`)
  - `Which components render GraphView?` → returns rendering components (e.g., `Page`)
  - `Which files import @/lib/api?` → returns importing file names
- Global:
  - `architecture overview` → top directory communities by components/functions with summaries
- Drift:
  - `graphAPI` with periods `Q1`=`src/components`, `Q2`=`src/app`, `Q3`=`src/lib`

### Graph Visualization (Code Graph)
- Import AST graph into Neo4j: `POST /api/graph/import/ast`
- Export code graph (backend): `GET /api/graph/export?dataset=code`
- Frontend page loads code graph by default at `http://localhost:3000/graph`
 - Legend on the Graph page:
   - `CodeFile` `#f0f4c3`, `Component` `#e8f5e9`, `Function` `#e3f2fd`, `Hook` `#fff9c4`, `Import` `#fce4ec`, `Export` `#ede7f6`, `Other` `#f3e5f5`

## Neo4j Usage Overview
- Connection is configured via env in `backend/app/core/config.py`
- Operations live in `backend/app/services/neo4j.py`:
  - Code graph: `CodeFile`, `Component`, `Function`, `Hook` with edges `CONTAINS`, `IMPORTS`, `CALLS`, `RENDERS`, `USES_HOOK`, `EXPORTS`
  - `export_graph_for_graphrag` and `export_graph_for_labels` return normalized nodes/edges for the frontend and GraphRAG
  - `get_neighbors(node_id)` fetches incoming/outgoing neighbor nodes and edges for expansion

## Experimentation
- Try different node selections on `/graph` and expand neighbors to reveal code relationships visually
- Local query example:
  ```json
  {
    "query": "Which components render GraphView?",
    "top_k": 5,
    "min_score": 0.0,
    "filters": null,
    "history": []
  }
  ```
- Global query example: `{"query":"architecture overview"}`
- Drift query example: `{"query":"graphAPI","periods":["Q1","Q2","Q3"]}`
- Inspect `GET /api/graphrag/debug/index` to confirm artifacts are loaded

## Project Structure
- `backend/` — FastAPI app (`app/main.py`, API routers, Neo4j service, config)
- `frontend/` — Next.js app (`src/app/graph/page.tsx`, `src/components/graph/GraphView.tsx`)
- `graphrag-pipeline/` — optional pipeline outputs under `output/` (ignored by git)

## Tips
- If expansion appears to do nothing, clear the search box on the graph page so new nodes aren’t filtered out
- For production, set strong credentials and restrict CORS; rotate any API keys regularly
