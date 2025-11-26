from fastapi import APIRouter, Query
from app.services.neo4j import Neo4jService
from app.services.graphrag import GraphRAGService
from app.core.config import settings

router = APIRouter()

@router.get("/export")
async def export_graph(dataset: str = Query(default="crm")):
    neo = Neo4jService()
    try:
        if dataset == "code":
            return neo.export_graph_for_labels(["CodeFile","Component","Function","Hook","Import","Export"])
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

@router.post("/import/ast")
async def import_ast_graph():
    svc = GraphRAGService(settings.graphrag_index_path)
    if svc.entities is None or svc.relationships is None:
        return {"imported": False, "reason": "No artifacts loaded"}
    try:
        ents = svc.entities.to_dict(orient="records")
        rels = svc.relationships.to_dict(orient="records")
    except Exception as e:
        return {"imported": False, "reason": f"Artifacts to_dict failed: {str(e)}"}
    neo = Neo4jService()
    try:
        try:
            res = neo.import_ast(ents, rels)
            return {"imported": True, **res}
        except Exception as e:
            return {"imported": False, "reason": f"Neo4j import failed: {str(e)}"}
    finally:
        neo.close()
