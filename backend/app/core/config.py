import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    def __init__(self):
        self.neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD", "password123")
        self.api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        self.graphrag_index_path = os.getenv("GRAPHRAG_INDEX_PATH", "graphrag-pipeline/output")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")

settings = Settings()
