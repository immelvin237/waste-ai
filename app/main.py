"""Wrapper module so `uvicorn app.main:app` works.

This dynamically loads the actual FastAPI `app` object from
the project's existing location at `waste-ai-clean/app/main.py`.
This avoids needing to rename directories or change imports.
"""
import importlib.util
from pathlib import Path

# Path to the real app file
HERE = Path(__file__).resolve().parent
target = (HERE / '..' / 'waste-ai-clean' / 'app' / 'main.py').resolve()

if not target.exists():
    raise ImportError(f"Target app file not found: {target}")

spec = importlib.util.spec_from_file_location("waste_ai_real_main", str(target))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

try:
    app = getattr(module, "app")
except AttributeError as e:
    raise ImportError(f"No 'app' object found in {target}") from e
