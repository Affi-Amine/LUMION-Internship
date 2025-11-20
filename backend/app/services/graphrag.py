import os
import glob
from typing import List, Dict, Any, Optional
import pandas as pd
import math
import json
try:
    import google.generativeai as genai
except Exception:
    genai = None

class GraphRAGService:
    def __init__(self, index_path: str):
        self.index_path = index_path
        self.artifacts_dir = self._latest_artifacts_dir(index_path)
        self.text_units = self._load_parquet('create_final_text_units.parquet')
        self.entities = self._load_parquet('create_final_entities.parquet')
        self.relationships = self._load_parquet('create_final_relationships.parquet')
        self.community_reports = self._load_parquet('create_final_community_reports.parquet')

    def _latest_artifacts_dir(self, base: str) -> Optional[str]:
        root = base
        if not os.path.isabs(root):
            repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
            root = os.path.abspath(os.path.join(repo_root, base))
        if not os.path.isdir(root):
            return None
        candidates = glob.glob(os.path.join(root, '*', 'artifacts'))
        if not candidates:
            return None
        return sorted(candidates)[-1]

    def _load_parquet(self, name: str) -> Optional[pd.DataFrame]:
        if not self.artifacts_dir:
            return None
        path = os.path.join(self.artifacts_dir, name)
        if not os.path.exists(path):
            return None
        try:
            return pd.read_parquet(path)
        except Exception:
            return None

    def _pick_text_col(self, df: pd.DataFrame) -> Optional[str]:
        for c in ['text', 'content', 'chunk', 'body', 'unit_text']:
            if c in df.columns:
                return c
        return None

    def _keyword_score(self, text: str, query: str) -> int:
        t = (text or '').lower()
        score = 0
        for w in query.lower().split():
            if w and w in t:
                score += 1
        return score

    def _cosine(self, a: List[float], b: List[float]) -> float:
        if not a or not b:
            return 0.0
        s = 0.0
        na = 0.0
        nb = 0.0
        for i in range(min(len(a), len(b))):
            s += a[i] * b[i]
            na += a[i] * a[i]
            nb += b[i] * b[i]
        if na == 0.0 or nb == 0.0:
            return 0.0
        return s / (math.sqrt(na) * math.sqrt(nb))

    def _embed(self, text: str) -> Optional[List[float]]:
        if genai is None:
            return None
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return None
        try:
            genai.configure(api_key=api_key)
            r = genai.embed_content(model="text-embedding-004", content=text)
            e = r.get("embedding") if isinstance(r, dict) else getattr(r, "embedding", None)
            return list(e) if e is not None else None
        except Exception:
            return None

    def _top_units(self, query: str, k: int = 5, offset: int = 0, min_score: float = 0.0, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        df = self.text_units
        if df is None or df.empty:
            return []
        text_col = self._pick_text_col(df)
        if not text_col:
            return []
        qemb = self._embed(query)
        scored = []
        for i, row in df.iterrows():
            txt = row.get(text_col, '')
            s_kw = self._keyword_score(str(txt), query)
            emb = None
            if 'embedding' in df.columns:
                e = row.get('embedding')
                try:
                    emb = e if isinstance(e, list) else json.loads(e) if isinstance(e, str) else None
                except Exception:
                    emb = None
            s_vec = self._cosine(qemb or [], emb or []) if qemb and emb else 0.0
            s = s_kw + s_vec
            if filters:
                if 'document_id' in filters and filters['document_id'] is not None and row.get('document_id') != filters['document_id']:
                    continue
            if s > 0:
                scored.append((s, i, row))
        scored.sort(key=lambda x: x[0], reverse=True)
        top = []
        sliced = scored[offset:offset + k]
        for s, i, row in sliced:
            if s < min_score:
                continue
            preview = str(row.get(text_col, ''))[:280]
            citation = {
                'score': s,
                'row_index': int(i),
                'text_preview': preview,
            }
            for cid in ['document_id', 'chunk_id', 'unit_id', 'source', 'entity_ids']:
                if cid in df.columns:
                    citation[cid] = row.get(cid)
            top.append(citation)
        return top

    async def local_search(self, query: str, conversation_history: List = None, top_k: int = 5, offset: int = 0, min_score: float = 0.0, filters: Optional[Dict[str, Any]] = None):
        citations = self._top_units(query, k=top_k, offset=offset, min_score=min_score, filters=filters)
        answer = '\n'.join([c['text_preview'] for c in citations]) or 'No matching context found.'
        entities = []
        if self.entities is not None and 'name' in self.entities.columns and 'type' in self.entities.columns:
            ents = []
            for _, row in self.entities.iterrows():
                name = str(row.get('name', ''))
                if name and self._keyword_score(name, query) > 0:
                    ents.append({'id': row.get('id'), 'name': name, 'type': row.get('type')})
            entities = ents[:5]
        return {
            'answer': answer,
            'sources': citations,
            'entities': entities,
            'confidence': 0.5 if citations else 0.1,
        }

    async def global_search(self, query: str, conversation_history: List = None, top_k: int = 5):
        df = self.community_reports
        reports = []
        if df is not None and not df.empty:
            text_col = self._pick_text_col(df) or ('report' if 'report' in df.columns else None)
            if text_col:
                scored = []
                for i, row in df.iterrows():
                    txt = str(row.get(text_col, ''))
                    s = self._keyword_score(txt, query)
                    if s > 0:
                        scored.append((s, i, row))
                scored.sort(key=lambda x: x[0], reverse=True)
                for s, i, row in scored[:top_k]:
                    reports.append({'score': s, 'community_id': row.get('community_id'), 'report_preview': str(row.get(text_col, ''))[:280]})
        answer = '\n'.join([r['report_preview'] for r in reports]) or 'No community insights found.'
        return {
            'answer': answer,
            'communities': reports,
            'key_themes': [],
            'confidence': 0.5 if reports else 0.1,
        }

    async def drift_search(self, query: str, time_periods: List[str], top_k: int = 5, min_score: float = 0.0, filters: Optional[Dict[str, Any]] = None):
        timeline = []
        for p in time_periods:
            citations = self._top_units(f"{query} {p}", k=top_k, min_score=min_score, filters=filters)
            timeline.append({'period': p, 'answer_preview': '\n'.join([c['text_preview'] for c in citations])[:280], 'metrics': {'matches': len(citations)}})
        return {
            'timeline': timeline,
            'trends': [],
            'insights': [],
        }

    def get_context_data(self, entity_id: str):
        if self.entities is None:
            return {}
        row = self.entities[self.entities.get('id') == entity_id] if 'id' in self.entities.columns else None
        if row is None or row.empty:
            return {}
        r = row.iloc[0]
        return {'id': r.get('id'), 'name': r.get('name'), 'type': r.get('type'), 'description': r.get('description')}