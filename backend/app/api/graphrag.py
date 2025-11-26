from fastapi import APIRouter
import os
from app.models.queries import QueryRequest, DriftQueryRequest, ConversationalRequest
from app.services.graphrag import GraphRAGService
from app.core.config import settings
from app.services.ms_graphrag import MicrosoftGraphRAGIntegrator

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

@router.post("/index/embeddings")
async def index_embeddings():
    service = GraphRAGService(index_path=settings.graphrag_index_path)
    return service.enrich_text_unit_embeddings()

@router.post("/index/microsoft")
async def index_with_microsoft():
    integrator = MicrosoftGraphRAGIntegrator()
    init_res = integrator.init_project()
    src = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "frontend", "src"))
    prep_res = integrator.prepare_input_from_dir(src)
    run_res = integrator.run_index()
    latest = integrator.latest_artifacts()
    return {"init": init_res, "prepare": prep_res, "run": run_res, "artifacts": latest}

@router.post("/index/gemini_graph")
async def index_with_gemini_graph(limit: int = 50):
    service = GraphRAGService(index_path=settings.graphrag_index_path)
    return service.enrich_graph_with_gemini(limit=limit)
