import os
import time
import glob
import pandas as pd
import json
try:
    import google.generativeai as genai
except Exception:
    genai = None

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
INPUT_DIR = os.path.join(ROOT, "data", "output", "input")
DEF_OUT_BASE = os.getenv("GRAPHRAG_INDEX_PATH", "graphrag-pipeline/output")
PIPELINE_OUT = DEF_OUT_BASE if os.path.isabs(DEF_OUT_BASE) else os.path.join(ROOT, DEF_OUT_BASE)

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def chunk_text(text: str, size: int = 600):
    chunks = []
    i = 0
    while i < len(text):
        chunks.append(text[i:i+size])
        i += size
    return chunks

def run():
    ts = str(int(time.time()))
    artifacts_dir = os.path.join(PIPELINE_OUT, ts, "artifacts")
    try:
        ensure_dir(artifacts_dir)
    except OSError as e:
        alt_base = os.path.join("/tmp", "lumion_graphrag_output")
        ensure_dir(alt_base)
        artifacts_dir = os.path.join(alt_base, ts, "artifacts")
        ensure_dir(artifacts_dir)

    text_units_rows = []
    entities_rows = []
    reports_rows = []

    for path in glob.glob(os.path.join(INPUT_DIR, "*.txt")):
        doc_id = os.path.basename(path)
        with open(path, "r") as f:
            content = f.read()
        chunks = chunk_text(content)
        can_embed = False
        if genai is not None and os.getenv("GEMINI_API_KEY"):
            try:
                genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
                can_embed = True
            except Exception:
                can_embed = False
        for idx, ch in enumerate(chunks):
            emb = None
            if can_embed:
                try:
                    r = genai.embed_content(model="text-embedding-004", content=ch)
                    e = r.get("embedding") if isinstance(r, dict) else getattr(r, "embedding", None)
                    emb = list(e) if e is not None else None
                except Exception:
                    emb = None
            row = {
                "document_id": doc_id,
                "chunk_id": idx,
                "text": ch,
            }
            if emb is not None:
                row["embedding"] = emb
            text_units_rows.append(row)
        # naive entities: pick capitalized words from first chunk
        words = [w.strip() for w in content.split()[:100] if w[:1].isupper() and w.isalpha()]
        for w in words[:10]:
            entities_rows.append({
                "id": f"ent_{doc_id}_{w}",
                "name": w,
                "type": "Token",
                "description": f"Auto-extracted token {w} from {doc_id}",
            })
        reports_rows.append({
            "community_id": doc_id,
            "report": content[:500],
        })

    df_units = pd.DataFrame(text_units_rows)
    df_entities = pd.DataFrame(entities_rows) if entities_rows else pd.DataFrame(columns=["id","name","type","description"]) 

    df_units.to_parquet(os.path.join(artifacts_dir, "create_final_text_units.parquet"), compression="snappy")
    df_entities.to_parquet(os.path.join(artifacts_dir, "create_final_entities.parquet"), compression="snappy")

    # relationships from Neo4j if available; else empty
    try:
        from app.services.neo4j import Neo4jService
        neo = Neo4jService()
        edges = neo.export_graph_for_graphrag().get("edges", [])
        pd.DataFrame(edges).to_parquet(os.path.join(artifacts_dir, "create_final_relationships.parquet"), compression="snappy")
        neo.close()
    except Exception:
        pd.DataFrame(columns=["source","target","type"]).to_parquet(os.path.join(artifacts_dir, "create_final_relationships.parquet"), compression="snappy")
    pd.DataFrame(reports_rows).to_parquet(os.path.join(artifacts_dir, "create_final_community_reports.parquet"), compression="snappy")

    print(f"Artifacts written to: {artifacts_dir}")

if __name__ == "__main__":
    run()