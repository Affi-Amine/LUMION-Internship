from fastapi import APIRouter

router = APIRouter()

@router.get("/dashboard")
async def get_dashboard_metrics():
    return {
        "total_customers": 0,
        "total_deals": 0,
        "total_revenue": 0,
        "avg_deal_size": 0,
        "conversion_rate": 0,
        "top_products": [],
        "top_reps": [],
        "recent_activities": []
    }

@router.get("/sales-pipeline")
async def get_sales_pipeline():
    return {"stages": []}

@router.get("/customer-segments")
async def get_customer_segments():
    return {"segments": []}

@router.get("/rep-performance")
async def get_rep_performance():
    return {"reps": []}