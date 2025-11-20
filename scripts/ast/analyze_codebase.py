import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "ast-parser"))
from code_analyzer import CodeAnalyzer

def run(path: str):
    analyzer = CodeAnalyzer()
    result = analyzer.parse_directory(path)
    print(result)

if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv) > 1 else "backend"
    run(p)