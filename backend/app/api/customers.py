from fastapi import APIRouter
from app.models.crm import CustomerCreate, CustomerUpdate
from app.services.neo4j import Neo4jService

router = APIRouter()

@router.get("/")
async def list_customers(skip: int = 0, limit: int = 100):
    neo = Neo4jService()
    try:
        items = neo.list_customers(skip, limit)
        return {"items": items, "skip": skip, "limit": limit}
    finally:
        neo.close()

@router.get("/{customer_id}")
async def get_customer(customer_id: str):
    return {"id": customer_id}

@router.post("/")
async def create_customer(customer: CustomerCreate):
    return {"created": customer.model_dump()}

@router.put("/{customer_id}")
async def update_customer(customer_id: str, customer: CustomerUpdate):
    return {"id": customer_id, "updated": customer.model_dump()}

@router.delete("/{customer_id}")
async def delete_customer(customer_id: str):
    return {"deleted": customer_id}

@router.get("/{customer_id}/interactions")
async def get_customer_interactions(customer_id: str):
    return {"id": customer_id, "interactions": []}

@router.get("/{customer_id}/deals")
async def get_customer_deals(customer_id: str):
    return {"id": customer_id, "deals": []}