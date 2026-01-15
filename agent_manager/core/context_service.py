import re
import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("FireflyContextService")

class ContextCompressionService:
    """
    Manages active context compression:
    1. Generating 'skeleton' views of code files (signatures only).
    2. Managing the project_state.json anchor file.
    """

    def __init__(self, artifact_service=None):
        self.artifact_service = artifact_service
        # Default project state structure
        self.default_state = {
            "global_goal": "",
            "completed_milestones": [],
            "current_active_task": "",
            "known_bugs": [],
            "next_step_queue": []
        }

    def get_project_state(self, root_path: str) -> Dict[str, Any]:
        """Reads project_state.json from the project root."""
        state_path = Path(root_path) / "project_state.json"
        
        if not state_path.exists():
            return self.default_state.copy()

        try:
            with open(state_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read project_state.json: {e}")
            return self.default_state.copy()

    def update_project_state(self, root_path: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Updates specific fields in project_state.json."""
        current_state = self.get_project_state(root_path)
        current_state.update(updates)
        
        state_path = Path(root_path) / "project_state.json"
        try:
            with open(state_path, 'w', encoding='utf-8') as f:
                json.dump(current_state, f, indent=2)
            return current_state
        except Exception as e:
            logger.error(f"Failed to write project_state.json: {e}")
            raise

    def generate_skeleton(self, file_content: str, file_path: str) -> str:
        """
        Generates a compressed skeleton view of the code.
        Currently supports Python and TypeScript/JavaScript via regex.
        """
        extension = Path(file_path).suffix.lower()
        
        if extension == '.py':
            return self._skeletonize_python(file_content)
        elif extension in ['.ts', '.js', '.tsx', '.jsx']:
            return self._skeletonize_typescript(file_content)
        else:
            # Fallback for unsupported types: return first 50 lines or just summary
            lines = file_content.split('\n')
            return "\n".join(lines[:20]) + f"\n... ({len(lines)-20} more lines hidden) ..."

    def _skeletonize_python(self, content: str) -> str:
        """
        Extracts classes, functions, and docstrings from Python code.
        Preserves indentation to maintain structure.
        """
        skeleton_lines = []
        lines = content.split('\n')
        
        for line in lines:
            stripped = line.strip()
            
            # Preserve class definitions
            if stripped.startswith("class "):
                skeleton_lines.append(line)
                continue
                
            # Preserve function definitions
            if stripped.startswith("def "):
                skeleton_lines.append(line)
                continue
                
            # Preserve decorators
            if stripped.startswith("@"):
                skeleton_lines.append(line)
                continue
            
            # Preserve imports (optional, but good for context) - limiting to top level
            if (stripped.startswith("import ") or stripped.startswith("from ")) and not line.startswith("    "):
                skeleton_lines.append(line)
                continue
            
            # Pass/Ellipsis for bodies (very naive heuristically)
            # A better approach is to check if the PREVIOUS line was a def/class and add "    ..."
            # But for regex simplicity, we might just skip everything else.
            
            # Actually, to make it valid python (mostly), we need to ensure indented blocks have content.
            # But for an LLM view, "..." is fine even if it's not valid syntax.
            
        # Refined Logic:
        # We want to keep strictly:
        # - Imports
        # - Class defs
        # - Method defs
        # - Docstrings (if immediate)
        
        # Regex based implementation for better robustness than line iteration
        skeleton = []
        
        # 1. Keep Imports
        imports = re.findall(r'^(?:from\s+[\w\.]+\s+import\s+.+|import\s+.+)', content, re.MULTILINE)
        if imports:
            skeleton.extend(imports)
            skeleton.append("")
            
        # 2. Find all classes and functions
        # This regex captures the indentation, the type (class/def), the name, and arguments line
        # It handles multi-line definitions poorly without complex regex, assuming single line dicts for now
        
        lines = content.split('\n')
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Keep comments that start with # TODO or # NOTE
            if stripped.startswith("# TODO") or stripped.startswith("# NOTE"):
                skeleton.append(line)
                continue

            # Check for Class/Def
            if re.match(r'^\s*(class|def|@|async def)\s+', line):
                skeleton.append(line)
                
                # Check for docstring in next line
                if i + 1 < len(lines):
                    next_line = lines[i+1]
                    if '"""' in next_line or "'''" in next_line:
                        skeleton.append(next_line)
                        # Failure mode: multiline docstrings not fully captured here, 
                        # but often the first line is enough summary.
                
                # Add ellipse to indicate body hidden
                indent = len(line) - len(line.lstrip())
                skeleton.append(" " * (indent + 4) + "...")
                
        return "\n".join(skeleton)

    def _skeletonize_typescript(self, content: str) -> str:
        """
        Extracts interfaces, classes, types, and exported functions from TS/JS.
        """
        skeleton = []
        lines = content.split('\n')
        
        for line in lines:
            stripped = line.strip()
            
            # Keep imports
            if stripped.startswith("import ") or stripped.startswith("require("):
                skeleton.append(line)
                continue
                
            # Keep exports, classes, interfaces, types, functions
            if re.match(r'^\s*(export\s+)?(class|interface|type|enum|function|const|let|var)\s+', line):
                # Filter out simple variable assignments vs function assignments
                if " = " in line and "=>" not in line and "function" not in line and "class" not in line:
                    if "require" not in line:
                        continue
                skeleton.append(line)
                indent = len(line) - len(line.lstrip())
                skeleton.append(" " * (indent + 2) + "// ...")
                continue
            
            # Keep Class Methods (heuristic: starts with name + parens + brace)
            # e.g. "  ngOnInit() {" or "  public doSomething(x: string): void {"
            if "class" not in line and "interface" not in line: # Avoid double matching
                if re.match(r'^\s*(?:public|private|protected|static|async|readonly)*\s*[a-zA-Z0-9_]+\s*\(.*\)\s*(?::\s*[^\{]+)?\s*\{', line):
                     skeleton.append(line)
                     indent = len(line) - len(line.lstrip())
                     skeleton.append(" " * (indent + 2) + "// ...")
                
        return "\n".join(skeleton)
