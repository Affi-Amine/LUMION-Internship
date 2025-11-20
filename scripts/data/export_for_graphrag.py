import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BACKEND = os.path.join(ROOT, "backend")
sys.path.append(BACKEND)

from app.services.neo4j import Neo4jService

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def save_documents(base_dir: str, docs):
    ensure_dir(base_dir)
    for i, content in enumerate(docs, start=1):
        with open(os.path.join(base_dir, f"doc_{i:03d}.txt"), "w") as f:
            f.write(content)

def run():
    out_dir = os.path.join(ROOT, "data", "output", "input")
    neo = Neo4jService()
    try:
        docs = neo.get_all_entities_as_text()
        save_documents(out_dir, docs)
    finally:
        neo.close()

if __name__ == "__main__":
    run()