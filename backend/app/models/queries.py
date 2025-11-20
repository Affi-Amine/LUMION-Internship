from pydantic import BaseModel
from typing import List, Optional, Any, Dict

class QueryRequest(BaseModel):
    query: str
    history: Optional[List[Any]] = None
    top_k: Optional[int] = 5
    offset: Optional[int] = 0
    min_score: Optional[float] = 0.0
    filters: Optional[Dict[str, Any]] = None

class DriftQueryRequest(BaseModel):
    query: str
    periods: List[str]
    top_k: Optional[int] = 5
    min_score: Optional[float] = 0.0
    filters: Optional[Dict[str, Any]] = None

class ConversationalRequest(BaseModel):
    query: str
    history: Optional[List[Any]] = None