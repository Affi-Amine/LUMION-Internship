from fastapi import APIRouter
from app.services.neo4j import Neo4jService

router = APIRouter()

@router.get("/export")
async def export_graph():
    neo = Neo4jService()
    try:
        return neo.export_graph_for_graphrag()
    finally:
        neo.close()

@router.get("/neighbors/{node_id}")
async def get_neighbors(node_id: str, depth: int = 1):
    neo = Neo4jService()
    try:
        return neo.get_neighbors(node_id=node_id, depth=depth)
    finally:
        neo.close()

@router.get("/path/{source_id}/{target_id}")
async def find_path(source_id: str, target_id: str):
    return {"source": source_id, "target": target_id, "path": []}