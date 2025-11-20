from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def list_interactions(skip: int = 0, limit: int = 100):
    return {"items": [], "skip": skip, "limit": limit}