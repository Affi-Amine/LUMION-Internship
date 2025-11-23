# Smart CRM Platform

A full-stack CRM demo featuring a FastAPI backend, a Next.js frontend, and a Neo4j graph database for relationships between customers, companies, deals, and interactions. It also includes a lightweight GraphRAG exploration layer.

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
- `GET /api/graph/export` — full graph snapshot (nodes/edges)
- `GET /api/graph/neighbors/{node_id}` — direct neighbors of a node
- `POST /api/graphrag/query/local` — local GraphRAG search over indexed artifacts
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

## GraphRAG Pipeline and Indexing
- Inputs
  - Example docs are included in `graphrag-pipeline/input/`.
  - The indexing script reads from `data/output/input/`. Copy your `.txt` docs there:
    - `mkdir -p data/output/input && cp graphrag-pipeline/input/*.txt data/output/input/`
- Outputs
  - Default `GRAPHRAG_INDEX_PATH` is `graphrag-pipeline/output`.
  - Files produced:
    - `create_final_text_units.parquet` (chunked text, optional embeddings)
    - `create_final_entities.parquet` (naive entities)
    - `create_final_relationships.parquet` (edges exported from Neo4j if available)
    - `create_final_community_reports.parquet` (brief per-document report)
- Run the pipeline
  - `pip install -r backend/requirements.txt` (for optional Neo4j export)
  - Set `GEMINI_API_KEY` to enable embeddings
  - `python scripts/graphrag/run_indexing.py`
  - Console prints: `Artifacts written to: <path>`
- Backend indexing config
  - The backend reads the latest artifacts under `GRAPHRAG_INDEX_PATH`.
  - Verify: `GET /api/graphrag/debug/index`
  - Query: `POST /api/graphrag/query/local`

## Neo4j Usage Overview
- Connection is configured via env in `backend/app/core/config.py`
- Operations live in `backend/app/services/neo4j.py`:
  - Create/merge `Customer`, `Company`, `Deal`, `Interaction` and link edges like `WORKS_AT`, `HAS_DEAL`, `PARTICIPATED_IN`
  - `export_graph_for_graphrag` returns normalized nodes/edges for the frontend and GraphRAG
  - `get_neighbors(node_id)` fetches incoming/outgoing neighbor nodes and edges for expansion

## Experimentation
- Try different node selections on `/graph` and expand neighbors to reveal relationships visually
- Use `POST /api/graphrag/query/local` with a JSON body:
  ```json
  {
    "query": "top customers by deal value",
    "top_k": 5,
    "min_score": 0.0,
    "filters": null,
    "history": []
  }
  ```
- Inspect `GET /api/graphrag/debug/index` to confirm artifacts (if any) are loaded

## Project Structure
- `backend/` — FastAPI app (`app/main.py`, API routers, Neo4j service, config)
- `frontend/` — Next.js app (`src/app/graph/page.tsx`, `src/components/graph/GraphView.tsx`)
- `graphrag-pipeline/` — optional pipeline outputs under `output/` (ignored by git)

## Tips
- If expansion appears to do nothing, clear the search box on the graph page so new nodes aren’t filtered out
- For production, set strong credentials and restrict CORS; rotate any API keys regularly
