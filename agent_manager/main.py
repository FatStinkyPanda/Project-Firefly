from pathlib import Path
import os
import sys
import traceback

# Ensure project root is in sys.path
sys.path.append(str(Path(__file__).parent.parent))

try:
    from agent_manager.main_controller import main

    if __name__ == "__main__":
        main()
except Exception:
    with open("backend_crash.log", "w") as f:
        f.write(traceback.format_exc())
    sys.exit(1)
