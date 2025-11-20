import os
import ast
from typing import List, Dict, Any

class CodeAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.modules: List[Dict[str, Any]] = []
        self.classes: List[Dict[str, Any]] = []
        self.functions: List[Dict[str, Any]] = []
        self.imports: List[Dict[str, Any]] = []

    def parse_directory(self, path: str) -> Dict[str, List[Dict[str, Any]]]:
        for root, _, files in os.walk(path):
            for f in files:
                if f.endswith(".py"):
                    p = os.path.join(root, f)
                    with open(p, "r") as fh:
                        tree = ast.parse(fh.read())
                        self.visit(tree)
        return {
            "modules": self.modules,
            "classes": self.classes,
            "functions": self.functions,
            "imports": self.imports,
        }

    def visit_ClassDef(self, node: ast.ClassDef):
        info = {
            "name": node.name,
            "bases": [getattr(b, "id", "") for b in node.bases],
            "methods": [],
            "docstring": ast.get_docstring(node) or "",
        }
        for n in node.body:
            if isinstance(n, ast.FunctionDef):
                info["methods"].append(n.name)
        self.classes.append(info)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        info = {
            "name": node.name,
            "args": [a.arg for a in node.args.args],
            "returns": None,
            "docstring": ast.get_docstring(node) or "",
        }
        if node.returns is not None:
            try:
                info["returns"] = ast.unparse(node.returns)
            except Exception:
                info["returns"] = None
        self.functions.append(info)
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        for n in node.names:
            self.imports.append({"module": n.name})

    def visit_ImportFrom(self, node: ast.ImportFrom):
        self.imports.append({"module": node.module or "", "names": [n.name for n in node.names]})