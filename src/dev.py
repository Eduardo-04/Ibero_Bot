import os
import yaml
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class DevCfg:
    def __init__(self, path: str = "cfg/devices.yaml"):
        full = BASE_DIR / path
        with open(full, "r", encoding="utf-8") as f:
            self.raw = yaml.safe_load(f) or {}
        self.devices = self.raw.get("devices", {}) or {}

    def keys(self):
        return list(self.devices.keys())

    def label(self, key: str) -> str:
        d = self.devices.get(key, {}) or {}
        return d.get("label", key)

    def token(self, key: str) -> str:
        d = self.devices.get(key, {}) or {}
        env_name = d.get("env_token")
        if not env_name:
            raise RuntimeError(f"Falta env_token para device '{key}' en devices.yaml")
        val = os.getenv(env_name)
        if not val:
            raise RuntimeError(f"Falta variable de entorno {env_name} en .env")
        return val
