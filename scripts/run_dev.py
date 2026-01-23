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

success = False
for p in candidates:
    sys.path.insert(0, p)
    importlib.invalidate_caches()
    try:
        mod = importlib.import_module("app.main")
        print(f"[INFO] app.main importé depuis : {p}")
        app = getattr(mod, "app")
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)
        success = True
        break
    except Exception:
        # Ne rien afficher pour les essais ratés
        if sys.path and sys.path[0] == p:
            sys.path.pop(0)
if not success:
    print("[ERREUR] Impossible d'importer 'app.main' avec les chemins testés :\n", candidates)
