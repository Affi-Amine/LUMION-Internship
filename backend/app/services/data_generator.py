from typing import List, Dict
from faker import Faker
from random import choice, randint
import json

faker = Faker()

def generate_companies(n: int = 50) -> List[Dict]:
    return [
        {
            "company_id": f"cmp_{i}",
            "name": faker.company(),
            "industry": choice(["Tech", "Finance", "Healthcare", "Retail"]),
            "size": choice(["Small", "Medium", "Enterprise"]),
            "revenue": float(randint(1, 100)) * 1_000_000,
            "location": faker.city(),
            "founded_date": str(faker.date_this_century()),
        }
        for i in range(1, n + 1)
    ]

def generate_customers(n: int = 200) -> List[Dict]:
    return [
        {
            "customer_id": f"cus_{i}",
            "first_name": faker.first_name(),
            "last_name": faker.last_name(),
            "email": faker.email(),
            "phone": faker.phone_number(),
            "role": choice(["Manager", "Director", "Engineer", "Analyst"]),
            "company_id": f"cmp_{randint(1, 50)}",
            "preferences": json.dumps({}),
            "lifetime_value": float(randint(1, 100)) * 1000,
            "created_date": str(faker.date_this_year()),
        }
        for i in range(1, n + 1)
    ]