import os
import shutil
import subprocess
from typing import Dict, Any
from app.core.config import settings

class MicrosoftGraphRAGIntegrator:
    def __init__(self, root: str | None = None):
        base = root or os.path.join(os.path.dirname(__file__), "..", "..", "..", "graphrag_index")
        self.root = os.path.abspath(base)
        self.input_dir = os.path.join(self.root, "input")
        self.env_file = os.path.join(self.root, ".env")

    def _graphrag_bin(self) -> str:
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        candidates = [
            os.path.join(repo_root, "backend", "venv", "bin", "graphrag"),
            os.path.join(repo_root, "venv", "bin", "graphrag"),
            "graphrag",
        ]
        for c in candidates:
            if os.path.isabs(c):
                if os.path.exists(c):
                    return c
            else:
                return c
        return "graphrag"

    def _run(self, args: list[str]) -> tuple[int, str]:
        try:
            p = subprocess.run(args, cwd=self.root, capture_output=True, text=True)
            out = (p.stdout or "") + ("\n" + p.stderr if p.stderr else "")
            return p.returncode, out
        except Exception as e:
            return 1, str(e)

    def init_project(self) -> Dict[str, Any]:
        os.makedirs(self.root, exist_ok=True)
        gr = self._graphrag_bin()
        code, out = self._run([gr, "init", "--root", self.root])
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not os.path.exists(self.env_file):
            try:
                with open(self.env_file, "w") as f:
                    f.write(f"GRAPHRAG_API_KEY={api_key}\n")
            except Exception:
                pass
        else:
            try:
                lines = []
                with open(self.env_file, "r") as f:
                    lines = f.read().splitlines()
                found = False
                for i, l in enumerate(lines):
                    if l.startswith("GRAPHRAG_API_KEY="):
                        lines[i] = f"GRAPHRAG_API_KEY={api_key}"
                        found = True
                        break
                if not found:
                    lines.append(f"GRAPHRAG_API_KEY={api_key}")
                with open(self.env_file, "w") as f:
                    f.write("\n".join(lines) + "\n")
            except Exception:
                pass
        return {"returncode": code, "output": out}

    def prepare_input_from_dir(self, src_dir: str) -> Dict[str, Any]:
        os.makedirs(self.input_dir, exist_ok=True)
        try:
            merged = []
            for root, _, files in os.walk(src_dir):
                for fn in files:
                    if fn.endswith(('.ts', '.tsx', '.js', '.md', '.txt')):
                        fp = os.path.join(root, fn)
                        try:
                            with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                                merged.append(f.read())
                        except Exception:
                            pass
            out_file = os.path.join(self.input_dir, 'corpus.txt')
            with open(out_file, 'w') as f:
                f.write("\n\n".join(merged))
            return {"files": 1, "bytes": sum(len(m) for m in merged)}
        except Exception as e:
            return {"files": 0, "error": str(e)}

    def run_index(self) -> Dict[str, Any]:
        gr = self._graphrag_bin()
        code, out = self._run([gr, "index", "--root", self.root])
        return {"returncode": code, "output": out}

    def latest_artifacts(self) -> Dict[str, Any]:
        out_dir = os.path.join(self.root, "output")
        if not os.path.isdir(out_dir):
            return {"artifacts": None}
        try:
            ts = sorted([d for d in os.listdir(out_dir) if d.isdigit()])[-1]
            artifacts = os.path.join(out_dir, ts, "artifacts")
            return {"artifacts": artifacts}
        except Exception:
            return {"artifacts": None}
