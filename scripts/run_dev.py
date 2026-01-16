"""Run the FastAPI app with a few sys.path tweaks to handle the repository layout in this environment.
This script will try several PYTHONPATH candidates and start uvicorn with the first working one.
"""
import importlib
import os
import sys

candidates = [
    os.path.abspath("."),
    os.path.abspath("app"),
    os.path.abspath("app/app"),
    os.path.abspath("JiraVision/app"),
    os.path.abspath("JiraVision/app/app"),
]

for p in candidates:
    print("Trying sys.path insert:", p)
    sys.path.insert(0, p)
    importlib.invalidate_caches()
    try:
        mod = importlib.import_module("app.main")
        print("Imported app.main from", p)
        app = getattr(mod, "app")
        import uvicorn

        uvicorn.run(app, host="0.0.0.0", port=8000)
        break
    except Exception as exc:
        print("Failed with", p, type(exc), exc)
        # remove the inserted path and try next
        if sys.path and sys.path[0] == p:
            sys.path.pop(0)
else:
    print("Could not import 'app.main' with any candidate PYTHONPATH.\nTried:", candidates)
