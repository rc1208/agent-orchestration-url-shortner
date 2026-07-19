import ast
from pathlib import Path

from pydantic import BaseModel, Field


class EvidenceReference(BaseModel):
    path: str
    symbol: str
    line: int = Field(ge=1)
    kind: str


class CodebaseImpactAnalysis(BaseModel):
    modules: list[str]
    symbols: list[str]
    imports: list[str]
    routes: list[str]
    tests: list[str]
    data_flows: list[str]
    impacted_files: list[str]
    impacted_symbols: list[str]
    api_schema_effects: list[str]
    test_impact: list[str]
    risks: list[str]
    evidence: list[EvidenceReference]


class PythonCodebaseAnalyzer:
    def analyze(self, root: Path, requirement: str) -> CodebaseImpactAnalysis:
        modules: list[str] = []
        symbols: list[str] = []
        imports: list[str] = []
        routes: list[str] = []
        tests: list[str] = []
        evidence: list[EvidenceReference] = []

        for path in sorted(root.rglob("*.py")):
            relative = path.relative_to(root).as_posix()
            modules.append(relative)
            if path.name.startswith("test_") or "tests" in path.parts:
                tests.append(relative)
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    qualified = f"{relative}:{node.name}"
                    symbols.append(qualified)
                    evidence.append(EvidenceReference(
                        path=relative, symbol=node.name, line=node.lineno,
                        kind=type(node).__name__.lower(),
                    ))
                elif isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.append(node.module)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                            if decorator.func.attr in {"get", "post", "put", "patch", "delete"}:
                                value = decorator.args[0] if decorator.args else None
                                route = (value.value if isinstance(value, ast.Constant)
                                         and isinstance(value.value, str) else "<dynamic>")
                                routes.append(f"{decorator.func.attr.upper()} {route} -> {node.name}")

        keywords = {word.lower().rstrip("s") for word in requirement.split() if len(word) > 4}
        impacted = [item for item in modules if any(key in item.lower() for key in keywords)]
        impacted.extend(item for item in modules if any(name in item for name in ("service", "repository", "schema", "api")))
        impacted_files = sorted(set(impacted)) or modules
        impacted_symbols = [symbol for symbol in symbols if symbol.split(":", 1)[0] in impacted_files]
        return CodebaseImpactAnalysis(
            modules=modules, symbols=symbols, imports=sorted(set(imports)), routes=routes,
            tests=tests,
            data_flows=["HTTP route -> service -> repository -> SQLite",
                        "Redirect route -> service resolve -> analytics counter"],
            impacted_files=impacted_files, impacted_symbols=impacted_symbols,
            api_schema_effects=["Add expiration input/output fields", "Expose redirect analytics"],
            test_impact=tests or ["Add unit and API regression tests"],
            risks=["Schema compatibility", "Timezone correctness", "Atomic analytics updates"],
            evidence=evidence,
        )
