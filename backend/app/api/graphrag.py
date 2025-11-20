from fastapi import APIRouter
from app.models.queries import QueryRequest, DriftQueryRequest, ConversationalRequest
from app.services.graphrag import GraphRAGService
from app.core.config import settings

router = APIRouter()

@router.post("/query/local")
async def local_query(query: QueryRequest):
    service = GraphRAGService(index_path=settings.graphrag_index_path)
    return await service.local_search(
        query.query,
        query.history,
        top_k=query.top_k or 5,
        offset=query.offset or 0,
        min_score=query.min_score or 0.0,
        filters=query.filters or None,
    )

@router.post("/query/global")
async def global_query(query: QueryRequest):
    service = GraphRAGService(index_path=settings.graphrag_index_path)
    return await service.global_search(query.query, query.history, top_k=query.top_k or 5)

@router.post("/query/drift")
async def drift_query(query: DriftQueryRequest):
    service = GraphRAGService(index_path=settings.graphrag_index_path)
    return await service.drift_search(
        query.query,
        query.periods,
        top_k=query.top_k or 5,
        min_score=query.min_score or 0.0,
        filters=query.filters or None,
    )

@router.post("/query/conversational")
async def conversational_query(query: ConversationalRequest):
    service = GraphRAGService(index_path=settings.graphrag_index_path)
    return await service.local_search(query.query, query.history)

@router.get("/debug/index")
async def debug_index():
    service = GraphRAGService(index_path=settings.graphrag_index_path)
    return {
        "artifacts_dir": service.artifacts_dir,
        "text_units_loaded": bool(service.text_units is not None and not service.text_units.empty),
        "entities_loaded": bool(service.entities is not None and not service.entities.empty),
        "relationships_loaded": bool(service.relationships is not None and not service.relationships.empty),
        "community_reports_loaded": bool(service.community_reports is not None and not service.community_reports.empty),
    }

@router.get("/entities/{entity_id}")
async def get_entity_details(entity_id: str):
    return {"id": entity_id}