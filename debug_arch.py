from pathlib import Path
import re
from dataclasses import dataclass
from typing import List

@dataclass
class LayerRule:
    layer: str
    patterns: List[str]

DEFAULT_RULES = [
    LayerRule(
        layer='controller',
        patterns=['*controller*', '*handler*', '*route*', 'app.api*', 'app.view*']
    ),
    LayerRule(
        layer='service',
        patterns=['*service*', '*manager*', '*logic*']
    ),
    LayerRule(
        layer='repository',
        patterns=['*repository*', '*dao*', '*dal*']
    ),
    LayerRule(
        layer='model',
        patterns=['*model*', '*entity*', '*schema*', '*dto*']
    ),
    LayerRule(
        layer='util',
        patterns=['*util*', '*helper*', '*common*', '*lib*']
    ),
]

def detect_layer(path: Path, rules: List[LayerRule]) -> str:
    name = path.stem.lower()
    parts = [p.lower() for p in path.parts]

    for rule in rules:
        for pattern in rule.patterns:
            regex = pattern.replace('*', '.*')
            if re.search(regex, name) or any(re.search(regex, p) for p in parts):
                return rule.layer
    return "unknown"

root = Path(r"c:\Users\dbiss\Desktop\Projects\Personal\Project-Firefly\agent_manager")
for path in root.rglob("*.py"):
    layer = detect_layer(path, DEFAULT_RULES)
    if layer == "controller":
        print(f"CONTROLLER: {path}")
    elif layer == "model":
        print(f"MODEL: {path}")
    elif layer == "service":
        pass # Service is expected default for agent_manager
    else:
        print(f"{layer.upper()}: {path}")
