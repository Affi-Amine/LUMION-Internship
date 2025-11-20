from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import customers, companies, deals, interactions, graphrag, analytics, graph

app = FastAPI(title="Smart CRM API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(customers.router, prefix="/api/customers", tags=["customers"]) 
app.include_router(companies.router, prefix="/api/companies", tags=["companies"]) 
app.include_router(deals.router, prefix="/api/deals", tags=["deals"]) 
app.include_router(interactions.router, prefix="/api/interactions", tags=["interactions"]) 
app.include_router(graphrag.router, prefix="/api/graphrag", tags=["graphrag"]) 
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"]) 
app.include_router(graph.router, prefix="/api/graph", tags=["graph"])