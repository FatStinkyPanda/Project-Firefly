"""
API Documentation Generator
===========================
Generate OpenAPI specs and markdown docs from Flask/FastAPI code.

Usage:
    python api_docs.py [path] [--output api.md]
    python -m scripts.api_docs src/
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import ast
import json
import re
import sys

from .utils import (
    find_python_files,
    find_project_root,
    parse_file,
    Console
)


@dataclass
class APIEndpoint:
    """An API endpoint definition."""
    path: str
    method: str
    function_name: str
    file_path: Path
    line_number: int
    docstring: Optional[str] = None
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    request_body: Optional[Dict[str, Any]] = None
    responses: Dict[str, Any] = field(default_factory=dict)


@dataclass
class APIDocumentation:
    """Complete API documentation."""
    title: str = "API Documentation"
    version: str = "1.0.0"
    endpoints: List[APIEndpoint] = field(default_factory=list)

    def to_openapi(self) -> Dict[str, Any]:
        """Convert to OpenAPI 3.0 spec."""
        paths: Dict[str, Dict] = {}

        for endpoint in self.endpoints:
            if endpoint.path not in paths:
                paths[endpoint.path] = {}

            method = endpoint.method.lower()
            paths[endpoint.path][method] = {
                "summary": endpoint.function_name,
                "description": endpoint.docstring or "",
                "operationId": endpoint.function_name,
                "parameters": endpoint.parameters,
                "responses": endpoint.responses or {"200": {"description": "Success"}}
            }

            if endpoint.request_body:
                paths[endpoint.path][method]["requestBody"] = endpoint.request_body

        return {
            "openapi": "3.0.0",
            "info": {
                "title": self.title,
                "version": self.version
            },
            "paths": paths
        }

    def to_markdown(self) -> str:
        """Convert to markdown documentation."""
        lines = [
            f"# {self.title}",
            "",
            f"**Version:** {self.version}",
            "",
            "## Endpoints",
            "",
        ]

        # Group by path
        by_path: Dict[str, List[APIEndpoint]] = {}
        for ep in self.endpoints:
            if ep.path not in by_path:
                by_path[ep.path] = []
            by_path[ep.path].append(ep)

        for path, endpoints in sorted(by_path.items()):
            lines.append(f"### `{path}`")
            lines.append("")

            for ep in endpoints:
                lines.append(f"#### {ep.method} `{path}`")
                lines.append("")
                lines.append(f"**Handler:** `{ep.function_name}`")
                lines.append(f"**Source:** `{ep.file_path}:{ep.line_number}`")
                lines.append("")

                if ep.docstring:
                    lines.append(ep.docstring)
                    lines.append("")

                if ep.parameters:
                    lines.append("**Parameters:**")
                    for param in ep.parameters:
                        lines.append(f"- `{param.get('name', '?')}` ({param.get('in', 'query')}): {param.get('description', '')}")
                    lines.append("")

                lines.append("---")
                lines.append("")

        return "\n".join(lines)


class FlaskRouteExtractor(ast.NodeVisitor):
    """Extract routes from Flask applications."""

    METHODS = {'get', 'post', 'put', 'delete', 'patch', 'options', 'head'}

    def __init__(self, path: Path, source_lines: List[str]):
        self.path = path
        self.source_lines = source_lines
        self.endpoints: List[APIEndpoint] = []
        self._app_names: set = set()

    def visit_Assign(self, node: ast.Assign):
        # Detect Flask app = Flask(__name__)
        if isinstance(node.value, ast.Call):
            if isinstance(node.value.func, ast.Name):
                if node.value.func.id == 'Flask':
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            self._app_names.add(target.id)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._check_decorators(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._check_decorators(node)
        self.generic_visit(node)

    def _check_decorators(self, node):
        for decorator in node.decorator_list:
            endpoint = self._parse_flask_decorator(decorator, node)
            if endpoint:
                self.endpoints.append(endpoint)

    def _parse_flask_decorator(self, decorator, func_node) -> Optional[APIEndpoint]:
        # @app.route('/path', methods=['GET'])
        if isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Attribute):
                if decorator.func.attr == 'route':
                    path = self._get_path_arg(decorator)
                    methods = self._get_methods_arg(decorator)
                    if path:
                        for method in methods:
                            return APIEndpoint(
                                path=path,
                                method=method,
                                function_name=func_node.name,
                                file_path=self.path,
                                line_number=func_node.lineno,
                                docstring=ast.get_docstring(func_node),
                                parameters=self._extract_params(path),
                                responses={"200": {"description": "Success"}}
                            )

                # @app.get, @app.post, etc.
                elif decorator.func.attr in self.METHODS:
                    path = self._get_path_arg(decorator)
                    if path:
                        return APIEndpoint(
                            path=path,
                            method=decorator.func.attr.upper(),
                            function_name=func_node.name,
                            file_path=self.path,
                            line_number=func_node.lineno,
                            docstring=ast.get_docstring(func_node),
                            parameters=self._extract_params(path)
                        )

        return None

    def _get_path_arg(self, call: ast.Call) -> Optional[str]:
        if call.args and isinstance(call.args[0], ast.Constant):
            return call.args[0].value
        return None

    def _get_methods_arg(self, call: ast.Call) -> List[str]:
        for keyword in call.keywords:
            if keyword.arg == 'methods':
                if isinstance(keyword.value, ast.List):
                    return [
                        elt.value.upper() if isinstance(elt, ast.Constant) else 'GET'
                        for elt in keyword.value.elts
                    ]
        return ['GET']

    def _extract_params(self, path: str) -> List[Dict]:
        """Extract path parameters like <id> or {id}."""
        params = []
        # Flask style: <type:name> or <name>
        for match in re.findall(r'<(?:\w+:)?(\w+)>', path):
            params.append({
                "name": match,
                "in": "path",
                "required": True,
                "schema": {"type": "string"}
            })
        return params


class FastAPIRouteExtractor(ast.NodeVisitor):
    """Extract routes from FastAPI applications."""

    METHODS = {'get', 'post', 'put', 'delete', 'patch', 'options', 'head'}

    def __init__(self, path: Path, source_lines: List[str]):
        self.path = path
        self.source_lines = source_lines
        self.endpoints: List[APIEndpoint] = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._check_decorators(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._check_decorators(node)
        self.generic_visit(node)

    def _check_decorators(self, node):
        for decorator in node.decorator_list:
            endpoint = self._parse_fastapi_decorator(decorator, node)
            if endpoint:
                self.endpoints.append(endpoint)

    def _parse_fastapi_decorator(self, decorator, func_node) -> Optional[APIEndpoint]:
        # @app.get("/path"), @router.post("/path")
        if isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Attribute):
                if decorator.func.attr in self.METHODS:
                    path = self._get_path_arg(decorator)
                    if path:
                        return APIEndpoint(
                            path=path,
                            method=decorator.func.attr.upper(),
                            function_name=func_node.name,
                            file_path=self.path,
                            line_number=func_node.lineno,
                            docstring=ast.get_docstring(func_node),
                            parameters=self._extract_params(path, func_node)
                        )

        return None

    def _get_path_arg(self, call: ast.Call) -> Optional[str]:
        if call.args and isinstance(call.args[0], ast.Constant):
            return call.args[0].value
        return None

    def _extract_params(self, path: str, func_node) -> List[Dict]:
        """Extract parameters from path and function signature."""
        params = []

        # Path parameters: {id}
        for match in re.findall(r'\{(\w+)\}', path):
            params.append({
                "name": match,
                "in": "path",
                "required": True,
                "schema": {"type": "string"}
            })

        # Query parameters from function args
        skip = {'request', 'response', 'db', 'session'}
        path_params = {p['name'] for p in params}

        for arg in func_node.args.args:
            if arg.arg not in skip and arg.arg not in path_params:
                params.append({
                    "name": arg.arg,
                    "in": "query",
                    "required": arg.annotation is not None,
                    "schema": {"type": "string"}
                })

        return params


def analyze_file(path: Path) -> List[APIEndpoint]:
    """Analyze a file for API endpoints."""
    tree = parse_file(path)
    if tree is None:
        return []

    try:
        with open(path, 'r', encoding='utf-8') as f:
            source_lines = f.readlines()
    except Exception:
        return []

    endpoints = []

    # Detect framework
    source = ''.join(source_lines)

    if 'flask' in source.lower() or 'Flask' in source:
        extractor = FlaskRouteExtractor(path, source_lines)
        extractor.visit(tree)
        endpoints.extend(extractor.endpoints)

    if 'fastapi' in source.lower() or 'FastAPI' in source:
        extractor = FastAPIRouteExtractor(path, source_lines)
        extractor.visit(tree)
        endpoints.extend(extractor.endpoints)

    return endpoints


def generate_api_docs(
    root: Path,
    title: str = "API Documentation",
    exclude_patterns: List[str] = None
) -> APIDocumentation:
    """Generate API documentation for a project."""
    docs = APIDocumentation(title=title)

    Console.info(f"Scanning {root}...")

    files = list(find_python_files(root, exclude_patterns))
    Console.info(f"Found {len(files)} Python files")

    for path in files:
        endpoints = analyze_file(path)
        docs.endpoints.extend(endpoints)

    Console.info(f"Found {len(docs.endpoints)} API endpoints")

    return docs


def main():
    """CLI entry point."""
    Console.header("API Documentation Generator")

    # Parse args
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    output_file = None
    output_format = 'markdown'

    for i, arg in enumerate(sys.argv):
        if arg == '--output' and i + 1 < len(sys.argv):
            output_file = Path(sys.argv[i + 1])
        if arg == '--json':
            output_format = 'json'

    if args:
        path = Path(args[0])
    else:
        path = find_project_root() or Path.cwd()

    if not path.exists():
        Console.fail(f"Path not found: {path}")
        return 1

    Console.info(f"Analyzing: {path}")

    docs = generate_api_docs(path)

    if len(docs.endpoints) == 0:
        Console.warn("No API endpoints found (Flask/FastAPI)")
        return 0

    if output_format == 'json':
        content = json.dumps(docs.to_openapi(), indent=2)
    else:
        content = docs.to_markdown()

    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        Console.ok(f"Documentation written to: {output_file}")
    else:
        print(content)

    return 0


if __name__ == "__main__":
    sys.exit(main())
