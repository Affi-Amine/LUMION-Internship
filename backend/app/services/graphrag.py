import os
import glob
from typing import List, Dict, Any, Optional
import re
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
        def score(p: str) -> int:
            parent = os.path.basename(os.path.dirname(p))
            try:
                return int(parent)
            except Exception:
                return -1
        best = sorted(candidates, key=score)[-1]
        return best

    def _load_parquet(self, name: str) -> Optional[pd.DataFrame]:
        if not self.artifacts_dir:
            return None
        base = os.path.join(self.artifacts_dir, name)
        if os.path.exists(base):
            try:
                return pd.read_parquet(base)
            except Exception:
                pass
        alt_json = base.replace('.parquet', '.json')
        alt_csv = base.replace('.parquet', '.csv')
        if os.path.exists(alt_json):
            try:
                with open(alt_json, 'r') as f:
                    data = json.load(f)
                return pd.DataFrame(data)
            except Exception:
                return None
        if os.path.exists(alt_csv):
            try:
                return pd.read_csv(alt_csv)
            except Exception:
                return None
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
                did = str(row.get('document_id', ''))
                if filters.get('document_id') is not None and did != str(filters['document_id']):
                    continue
                if filters.get('document_id_contains') and filters['document_id_contains'] not in did:
                    continue
                regex = filters.get('document_id_regex')
                if regex:
                    try:
                        if not re.search(regex, did):
                            continue
                    except Exception:
                        pass
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
        ql = query.lower()
        extra = []
        if self.relationships is not None and not self.relationships.empty:
            if 'type' in self.relationships.columns and 'target' in self.relationships.columns and 'source' in self.relationships.columns:
                wants_calls = ('call' in ql or 'calls' in ql)
                asks_graphapi = ('graphapi' in ql)
                asks_graphragapi = ('graphragapi' in ql)
                if wants_calls and (asks_graphapi or asks_graphragapi):
                    try:
                        rels = self.relationships[self.relationships['type'] == 'CALLS']
                        tgt = rels['target'].astype(str).str.lower()
                        if asks_graphapi and not asks_graphragapi:
                            rels = rels[tgt.str.contains('graphapi\.')]  # only graphAPI.*
                        elif asks_graphragapi and not asks_graphapi:
                            rels = rels[tgt.str.contains('graphragapi\.')]  # only graphragAPI.*
                        else:
                            rels = rels[tgt.str.contains('graphapi\.') | rels['target'].astype(str).str.lower().str.contains('graphragapi\.')]
                        ids = list(set(rels['source'].tolist()))
                        if ids:
                            df = self.entities if self.entities is not None else None
                            names = []
                            if df is not None and 'id' in df.columns:
                                m = df[df['id'].isin(ids)]
                                for _, r in m.iterrows():
                                    names.append(str(r.get('name', '')))
                            extra = [n for n in names if n]
                            if extra:
                                answer = ('\n').join(extra)
                    except Exception:
                        pass
                # components that render X
                wants_render = ('render' in ql or 'renders' in ql)
                if wants_render:
                    try:
                        raw_tokens = [t for t in query.split() if t and t[0].isupper()]
                        tokens = [re.sub(r'[^A-Za-z0-9_]+$', '', t) for t in raw_tokens]
                        target_cmp_ids = [f"cmp_{t}" for t in tokens if t]
                        m = re.search(r"render\w*\s+(\w+)", ql)
                        if m:
                            target_cmp_ids.append(f"cmp_{m.group(1)}")
                        rels = self.relationships[self.relationships['type'] == 'RENDERS']
                        if target_cmp_ids:
                            rels = rels[rels['target'].astype(str).isin(target_cmp_ids)]
                        else:
                            tkn = None
                            if 'graphview' in ql:
                                tkn = 'graphview'
                            if tkn:
                                rels = rels[rels['target'].astype(str).str.lower().str.contains(f"cmp_{tkn}")]
                        src_ids = list(set(rels['source'].tolist()))
                        df = self.entities if self.entities is not None else None
                        names = []
                        if df is not None and 'id' in df.columns:
                            m = df[df['id'].isin(src_ids)]
                            for _, r in m.iterrows():
                                names.append(str(r.get('name', '')))
                        extra = sorted(list(set([n for n in names if n])))
                        if extra:
                            answer = ('\n').join(extra)
                    except Exception:
                        pass
                # files that import module X
                wants_imports = ('import' in ql or 'imports' in ql)
                if wants_imports:
                    try:
                        rels = self.relationships[self.relationships['type'] == 'IMPORTS']
                        mod_tokens = [t.strip("'\".,") for t in query.split() if '/' in t or t.startswith('@')]
                        if mod_tokens:
                            r = rels[rels['target'].astype(str).str.contains('|'.join([t.lower() for t in mod_tokens]))]
                        else:
                            r = rels
                        src_ids = list(set(r['source'].tolist()))
                        df = self.entities if self.entities is not None else None
                        names = []
                        if df is not None and 'id' in df.columns:
                            m = df[df['id'].isin(src_ids)]
                            for _, rr in m.iterrows():
                                names.append(str(rr.get('name', '')))
                        extra = [n for n in names if n]
                        if extra:
                            answer = ('\n').join(extra)
                    except Exception:
                        pass
        return {
            'answer': answer,
            'sources': citations,
            'entities': entities,
            'confidence': 0.5 if citations or extra else 0.1,
        }

    async def global_search(self, query: str, conversation_history: List = None, top_k: int = 5):
        df = self.community_reports
        reports = []
        if df is not None and not df.empty:
            text_col = 'report' if 'report' in df.columns else self._pick_text_col(df)
            scored = []
            for i, row in df.iterrows():
                txt = str(row.get(text_col, ''))
                s = self._keyword_score(txt, query) + self._keyword_score(str(row.get('community_id','')), query)
                if s > 0:
                    scored.append((s, i, row))
            scored.sort(key=lambda x: x[0], reverse=True)
            for s, i, row in scored[:top_k]:
                reports.append({'score': s, 'community_id': row.get('community_id'), 'report_preview': str(row.get(text_col, ''))[:280]})
            if not reports:
                try:
                    sort_col = 'components' if 'components' in df.columns else ('functions' if 'functions' in df.columns else None)
                    if sort_col:
                        top = df.sort_values(by=sort_col, ascending=False).head(top_k)
                        for _, r in top.iterrows():
                            reports.append({'score': float(r.get(sort_col, 0)), 'community_id': r.get('community_id'), 'report_preview': str(r.get(text_col, ''))[:280]})
                        answer = 'Top communities by code density: ' + ', '.join([f"{r['community_id']}({int(r['score'])})" for r in reports])
                    else:
                        answer = 'No community insights found.'
                except Exception:
                    answer = 'No community insights found.'
        if reports and (not answer or answer == 'No community insights found.'):
            answer = '\n'.join([r['report_preview'] for r in reports])
        return {
            'answer': answer,
            'communities': reports,
            'key_themes': [],
            'confidence': 0.5 if reports else 0.1,
        }

    async def drift_search(self, query: str, time_periods: List[str], top_k: int = 5, min_score: float = 0.0, filters: Optional[Dict[str, Any]] = None):
        timeline = []
        dir_map = {
            'Q1': r"frontend/src/components",
            'Q2': r"frontend/src/app",
            'Q3': r"frontend/src/lib",
        }
        for p in time_periods:
            regex = dir_map.get(p, None)
            f = dict(filters or {})
            if regex:
                f['document_id_regex'] = regex
            citations = self._top_units(query, k=top_k, min_score=min_score, filters=f)
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
