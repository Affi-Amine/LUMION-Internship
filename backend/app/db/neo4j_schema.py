def get_schema_statements():
    return [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Customer) REQUIRE c.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (co:Company) REQUIRE co.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (d:Deal) REQUIRE d.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (i:Interaction) REQUIRE i.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Product) REQUIRE p.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (r:SalesRep) REQUIRE r.id IS UNIQUE",
    ]

def init_schema(driver):
    stmts = get_schema_statements()
    with driver.session() as session:
        for s in stmts:
            session.execute_write(lambda tx: tx.run(s))