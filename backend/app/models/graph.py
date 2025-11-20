from pydantic import BaseModel
from typing import Dict

class Node(BaseModel):
    id: str
    type: str
    properties: Dict[str, str]