import os
import sys
from pathlib import Path

os.environ["DEMO_MODE"] = "1"
os.environ.setdefault("AS_OF_DATE", "2026-10-23")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
