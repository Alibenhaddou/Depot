import os
import sys
import types
import importlib

# Ensure the package 'app' (JiraVision/app) is importable during tests
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app"))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Provide minimal stubs for third-party modules that may not be installed
# so tests can import the package modules without failing at collection time.
# Try importing the real packages first, only create stubs on ImportError.

# Ensure required env vars exist so pydantic BaseSettings can be
# constructed during imports
os.environ.setdefault("atlassian_client_id", "test-id")
os.environ.setdefault("atlassian_client_secret", "test-secret")
os.environ.setdefault("atlassian_redirect_uri", "")
os.environ.setdefault("atlassian_scopes", "read:jira")
os.environ.setdefault("app_secret_key", "secret-for-tests")

try:
    importlib.import_module("fastapi")
except Exception:
    fastapi = types.ModuleType("fastapi")
    fastapi.HTTPException = Exception
    sys.modules["fastapi"] = fastapi
    sys.modules["fastapi.responses"] = types.ModuleType("fastapi.responses")
    sys.modules["fastapi.staticfiles"] = types.ModuleType("fastapi.staticfiles")

try:
    importlib.import_module("pydantic")
except Exception:
    pydantic = types.ModuleType("pydantic")

    class BaseModel:
        def __init__(self, **data):
            for k, v in data.items():
                setattr(self, k, v)

    pydantic.BaseModel = BaseModel

    def field_validator(name=None):
        def deco(f):
            return f

        return deco

    pydantic.field_validator = field_validator
    sys.modules["pydantic"] = pydantic

try:
    importlib.import_module("pydantic_settings")
except Exception:
    pydantic_settings = types.ModuleType("pydantic_settings")

    class BaseSettings:
        def __init__(self, **_):
            pass

    pydantic_settings.BaseSettings = BaseSettings
    pydantic_settings.SettingsConfigDict = dict
    sys.modules["pydantic_settings"] = pydantic_settings

try:
    importlib.import_module("redis")
except Exception:
    redis = types.ModuleType("redis")

    class Redis:
        def __init__(self, *a, **k):
            pass

        def get(self, k):
            return None

        def set(self, *a, **k):
            pass

        def delete(self, *a, **k):
            pass

        def expire(self, *a, **k):
            pass

    redis.Redis = Redis
    sys.modules["redis"] = redis

try:
    importlib.import_module("httpx")
except Exception:
    httpx = types.ModuleType("httpx")

    class AsyncClient:
        def __init__(self, *a, **k):
            pass

    httpx.AsyncClient = AsyncClient
    sys.modules["httpx"] = httpx

try:
    importlib.import_module("itsdangerous")
except Exception:
    sys.modules["itsdangerous"] = types.ModuleType("itsdangerous")
