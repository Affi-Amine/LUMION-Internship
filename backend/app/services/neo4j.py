from neo4j import GraphDatabase
from typing import List, Dict, Any
from app.core.config import settings

class Neo4jService:
    def __init__(self, uri: str = settings.neo4j_uri, user: str = settings.neo4j_user, password: str = settings.neo4j_password):
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self._driver.close()

    def _run_write(self, query: str, params: Dict[str, Any]):
        with self._driver.session() as session:
            return session.execute_write(lambda tx: tx.run(query, **params).consume())

    def _run_read(self, query: str, params: Dict[str, Any] = None):
        with self._driver.session() as session:
            return session.execute_read(lambda tx: list(tx.run(query, **(params or {}))))

    def create_company(self, company_data: Dict):
        q = (
            "MERGE (co:Company {id:$id}) "
            "SET co += $props "
        )
        params = {"id": company_data.get("company_id") or company_data.get("id"), "props": company_data}
        return self._run_write(q, params)

    def create_customer(self, customer_data: Dict):
        q = (
            "MERGE (c:Customer {id:$id}) "
            "SET c += $props "
        )
        params = {"id": customer_data.get("customer_id") or customer_data.get("id"), "props": customer_data}
        res = self._run_write(q, params)
        cid = params["id"]
        coid = customer_data.get("company_id")
        if coid:
            self.link_customer_to_company(cid, coid)
        return res

    def create_deal(self, deal_data: Dict):
        q = (
            "MERGE (d:Deal {id:$id}) "
            "SET d += $props "
        )
        params = {"id": deal_data.get("deal_id") or deal_data.get("id"), "props": deal_data}
        res = self._run_write(q, params)
        cid = deal_data.get("customer_id")
        if cid:
            self._run_write(
                "MATCH (c:Customer {id:$cid}),(d:Deal {id:$did}) MERGE (c)-[:HAS_DEAL]->(d)",
                {"cid": cid, "did": params["id"]},
            )
        return res

    def create_interaction(self, interaction_data: Dict):
        q = (
            "MERGE (i:Interaction {id:$id}) "
            "SET i += $props "
        )
        params = {"id": interaction_data.get("interaction_id") or interaction_data.get("id"), "props": interaction_data}
        res = self._run_write(q, params)
        cid = interaction_data.get("customer_id")
        if cid:
            self._run_write(
                "MATCH (c:Customer {id:$cid}),(i:Interaction {id:$iid}) MERGE (c)-[:PARTICIPATED_IN]->(i)",
                {"cid": cid, "iid": params["id"]},
            )
        return res

    def link_customer_to_company(self, customer_id: str, company_id: str):
        q = "MATCH (c:Customer {id:$cid}),(co:Company {id:$coid}) MERGE (c)-[:WORKS_AT]->(co)"
        return self._run_write(q, {"cid": customer_id, "coid": company_id})

    def export_graph_for_graphrag(self) -> Dict:
        nodes_q = "MATCH (n) RETURN labels(n) AS labels, n.id AS id, properties(n) AS props"
        edges_q = "MATCH (a)-[r]->(b) RETURN a.id AS source, b.id AS target, type(r) AS type"
        nodes = self._run_read(nodes_q)
        edges = self._run_read(edges_q)
        return {
            "nodes": [{"id": rec["id"], "labels": rec["labels"], "props": rec["props"]} for rec in nodes],
            "edges": [{"source": rec["source"], "target": rec["target"], "type": rec["type"]} for rec in edges],
        }

    def export_graph_for_labels(self, labels: List[str]) -> Dict:
        nodes_q = (
            "MATCH (n) WHERE any(l IN labels(n) WHERE l IN $labels) "
            "RETURN labels(n) AS labels, n.id AS id, properties(n) AS props"
        )
        edges_q = (
            "MATCH (a)-[r]->(b) WHERE any(l IN labels(a) WHERE l IN $labels) AND any(m IN labels(b) WHERE m IN $labels) "
            "RETURN a.id AS source, b.id AS target, type(r) AS type"
        )
        nodes = self._run_read(nodes_q, {"labels": labels})
        edges = self._run_read(edges_q, {"labels": labels})
        return {
            "nodes": [{"id": rec["id"], "labels": rec["labels"], "props": rec["props"]} for rec in nodes],
            "edges": [{"source": rec["source"], "target": rec["target"], "type": rec["type"]} for rec in edges],
        }

    def get_all_entities_as_text(self) -> List[str]:
        customers = self._run_read(
            "MATCH (c:Customer) OPTIONAL MATCH (c)-[:WORKS_AT]->(co:Company) "
            "OPTIONAL MATCH (c)-[:HAS_DEAL]->(d:Deal) "
            "OPTIONAL MATCH (c)-[:PARTICIPATED_IN]->(i:Interaction) "
            "RETURN c, co, collect(d) AS deals, collect(i) AS interactions"
        )
        docs: List[str] = []
        for rec in customers:
            c = rec["c"]
            co = rec["co"]
            deals = [d for d in rec["deals"] if d is not None]
            interactions = [i for i in rec["interactions"] if i is not None]
            lines = [
                f"Customer: {c.get('first_name','')} {c.get('last_name','')} ({c.get('email','')})",
                f"Company: {co.get('name','') if co else ''}",
                f"Role: {c.get('role','')}",
                "Deals:",
            ]
            for d in deals:
                lines.append(f"- Deal {d.get('id','')}: stage {d.get('stage','')} value {d.get('value','')}")
            lines.append("Interactions:")
            for i in interactions:
                lines.append(f"- {i.get('type','')} on {i.get('date','')}: {i.get('summary','')}")
            docs.append("\n".join(lines))
        return docs

    def list_customers(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        rows = self._run_read("MATCH (c:Customer) RETURN c SKIP $skip LIMIT $limit", {"skip": skip, "limit": limit})
        return [dict(r["c"]) for r in rows]

    def get_neighbors(self, node_id: str, depth: int = 1) -> Dict:
        nodes_out = self._run_read(
            "MATCH (n {id:$id})-[]->(m) RETURN m.id AS id, labels(m) AS labels, properties(m) AS props",
            {"id": node_id},
        )
        nodes_in = self._run_read(
            "MATCH (m)-[]->(n {id:$id}) RETURN m.id AS id, labels(m) AS labels, properties(m) AS props",
            {"id": node_id},
        )
        edges_out = self._run_read(
            "MATCH (n {id:$id})-[r]->(m) RETURN n.id AS source, m.id AS target, type(r) AS type",
            {"id": node_id},
        )
        edges_in = self._run_read(
            "MATCH (m)-[r]->(n {id:$id}) RETURN m.id AS source, n.id AS target, type(r) AS type",
            {"id": node_id},
        )
        seen = set()
        nodes = []
        for rec in nodes_out + nodes_in:
            nid = rec["id"]
            if nid == node_id:
                continue
            if nid in seen:
                continue
            seen.add(nid)
            nodes.append({"id": rec["id"], "labels": rec["labels"], "props": rec["props"]})
        edges = [{"source": r["source"], "target": r["target"], "type": r["type"]} for r in edges_out + edges_in]
        return {"nodes": nodes, "edges": edges}

    def import_ast(self, entities: List[Dict[str, Any]], relationships: List[Dict[str, Any]]) -> Dict:
        created = 0
        def label_for(t: str) -> str:
            m = {
                'File': 'CodeFile',
                'Component': 'Component',
                'Function': 'Function',
                'Hook': 'Hook',
                'Import': 'Import',
                'Export': 'Export',
            }
            return m.get(t, 'Code')
        for e in entities:
            idv = e.get('id')
            typ = label_for(str(e.get('type', 'Code')))
            props = {}
            for k, v in e.items():
                if k in ['id', 'type']:
                    continue
                if isinstance(v, (str, int, float)) or v is None:
                    props[k] = v
                else:
                    try:
                        import json
                        props[k] = json.dumps(v)
                    except Exception:
                        props[k] = str(v)
            q = f"MERGE (n:{typ} {{id:$id}}) SET n += $props"
            self._run_write(q, {"id": idv, "props": props})
            created += 1
        for r in relationships:
            src = r.get('source')
            tgt = r.get('target')
            typ = str(r.get('type', 'RELATED_TO'))
            q = f"MATCH (a {{id:$src}}),(b {{id:$tgt}}) MERGE (a)-[:{typ}]->(b)"
            self._run_write(q, {"src": src, "tgt": tgt})
        return {"nodes": created, "edges": len(relationships)}
