"""
scripts/run_evaluation_pipeline.py

Run from the project root:
    python -m scripts.run_evaluation_pipeline
"""

import asyncio
import sys
from pathlib import Path

# Make sure the project root is on the path
sys.path.insert(0, str(Path(__file__).parents[1]))

from app.evaluation.evaluators import run_evaluation


if __name__ == "__main__":
    summary = asyncio.run(run_evaluation())
    sys.exit(0 if summary.pass_rate >= 0.75 else 1)