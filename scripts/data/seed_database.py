import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BACKEND = os.path.join(ROOT, "backend")
sys.path.append(BACKEND)

from app.services.neo4j import Neo4jService
from app.services.data_generator import generate_companies, generate_customers
from app.db.neo4j_schema import init_schema

def run():
    neo = Neo4jService()
    try:
        init_schema(neo._driver)
        companies = generate_companies()
        customers = generate_customers()
        for c in companies:
            neo.create_company(c)
        for u in customers:
            neo.create_customer(u)
    finally:
        neo.close()

if __name__ == "__main__":
    run()