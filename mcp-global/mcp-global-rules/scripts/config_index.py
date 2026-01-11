"""
Config Index
=============
Index configuration files, env vars, and settings.

Usage:
    python mcp.py config-index
    python mcp.py config-index --env
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set
import json
import os
import re
import sys

from .utils import Console, find_project_root


@dataclass
class ConfigItem:
    """A configuration item."""
    name: str
    value: Optional[str]
    source: str  # file path
    type: str  # 'env', 'json', 'yaml', 'ini', 'toml'
    line: int = 0


# Patterns for finding env var usage in code
ENV_PATTERNS = [
    r'os\.environ\[[\'"]([\w_]+)[\'"]\]',
    r'os\.environ\.get\([\'"]([\w_]+)[\'"]',
    r'os\.getenv\([\'"]([\w_]+)[\'"]',
    r'config\[[\'"]([\w_]+)[\'"]\]',
    r'settings\.([\w_]+)',
    r'process\.env\.([\w_]+)',
    r'\$\{([\w_]+)\}',
]


def find_config_files(root: Path) -> List[Path]:
    """Find configuration files."""
    patterns = [
        '.env', '.env.*', 'config.json', 'config.yaml', 'config.yml',
        'settings.json', 'settings.yaml', 'settings.yml', 'settings.py',
        'pyproject.toml', 'setup.cfg', 'requirements.txt',
        'package.json', 'tsconfig.json',
        '*.ini', '*.toml', '*.conf'
    ]

    files = []

    for pattern in patterns:
        for path in root.glob(pattern):
            if path.is_file() and '.git' not in str(path):
                files.append(path)
        for path in root.glob(f'**/{pattern}'):
            if path.is_file() and '.git' not in str(path) and 'node_modules' not in str(path):
                files.append(path)

    return list(set(files))


def parse_env_file(file_path: Path) -> List[ConfigItem]:
    """Parse .env file."""
    items = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        name, _, value = line.partition('=')
                        items.append(ConfigItem(
                            name=name.strip(),
                            value=value.strip().strip('"\''),
                            source=str(file_path),
                            type='env',
                            line=i
                        ))
    except Exception:
        pass

    return items


def parse_json_file(file_path: Path) -> List[ConfigItem]:
    """Parse JSON config file."""
    items = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        def extract(obj, prefix=''):
            for key, value in obj.items() if isinstance(obj, dict) else []:
                full_key = f"{prefix}.{key}" if prefix else key
                if isinstance(value, dict):
                    extract(value, full_key)
                else:
                    items.append(ConfigItem(
                        name=full_key,
                        value=str(value)[:50] if value is not None else None,
                        source=str(file_path),
                        type='json'
                    ))

        extract(data)
    except Exception:
        pass

    return items


def find_env_usage_in_file(file_path: Path) -> Set[str]:
    """Find env var usage in a code file."""
    env_vars = set()

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        for pattern in ENV_PATTERNS:
            matches = re.findall(pattern, content)
            env_vars.update(matches)
    except Exception:
        pass

    return env_vars


def index_configs(root: Path = None) -> Dict:
    """Build configuration index."""
    root = root or find_project_root() or Path.cwd()

    Console.info("Indexing configuration...")

    index = {
        "config_files": [],
        "env_vars": {},
        "env_usage": {},
        "missing_vars": []
    }

    # Find and parse config files
    config_files = find_config_files(root)

    for config_path in config_files:
        index["config_files"].append(str(config_path.relative_to(root)))

        if config_path.name.startswith('.env'):
            items = parse_env_file(config_path)
            for item in items:
                index["env_vars"][item.name] = {
                    "source": item.source,
                    "has_value": item.value is not None and item.value != ''
                }
        elif config_path.suffix == '.json':
            items = parse_json_file(config_path)

    # Find env var usage in code
    all_used = set()
    extensions = ['.py', '.js', '.ts']

    for ext in extensions:
        for code_file in root.rglob(f'*{ext}'):
            if '.git' in str(code_file) or 'node_modules' in str(code_file):
                continue

            used = find_env_usage_in_file(code_file)
            if used:
                rel_path = str(code_file.relative_to(root))
                index["env_usage"][rel_path] = list(used)
                all_used.update(used)

    # Find missing env vars (used but not defined)
    defined = set(index["env_vars"].keys())
    index["missing_vars"] = list(all_used - defined)

    # Save index
    index_path = root / '.mcp' / 'config_index.json'
    index_path.parent.mkdir(parents=True, exist_ok=True)

    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2)

    Console.ok(f"Found {len(config_files)} config files, {len(index['env_vars'])} env vars")

    if index["missing_vars"]:
        Console.warn(f"Missing env vars: {', '.join(index['missing_vars'][:5])}")

    return index


def get_env_vars_for_file(file_path: Path, root: Path = None) -> List[str]:
    """Get env vars used by a specific file."""
    return list(find_env_usage_in_file(file_path))


def main():
    """CLI entry point."""
    Console.header("Config Index")

    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    root = find_project_root() or Path.cwd()

    if '--index' in sys.argv:
        index_configs(root)
        return 0

    if '--env' in sys.argv:
        index = index_configs(root)
        print("\n## Defined Environment Variables")
        for name, info in index["env_vars"].items():
            status = "✓" if info["has_value"] else "✗"
            print(f"  {status} {name}")
        return 0

    if '--missing' in sys.argv:
        index = index_configs(root)
        if index["missing_vars"]:
            Console.warn("Used but not defined:")
            for var in index["missing_vars"]:
                print(f"  - {var}")
        else:
            Console.ok("All used env vars are defined!")
        return 0

    if args:
        file_path = Path(args[0])
        vars_used = get_env_vars_for_file(file_path)
        Console.info(f"Env vars used by {file_path.name}:")
        for var in vars_used:
            print(f"  - {var}")
    else:
        index_configs(root)

    return 0


if __name__ == "__main__":
    sys.exit(main())
