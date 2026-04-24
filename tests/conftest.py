import sys
from pathlib import Path

# Ensure `app` is importable when pytest is invoked from repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
