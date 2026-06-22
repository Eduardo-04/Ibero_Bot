import os
import yaml
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class DevCfg:
    """
    Clase para cargar y manejar la configuración de los equipos (devices)
    desde un archivo YAML.
    """
    def __init__(self, path: str = "cfg/devices.yaml"):
        """Inicializa leyendo el archivo de dispositivos."""
        full = BASE_DIR / path
        with open(full, "r", encoding="utf-8") as f:
            self.raw = yaml.safe_load(f) or {}
        self.devices = self.raw.get("devices", {}) or {}

    def keys(self):
        """Retorna una lista con las claves de los equipos disponibles."""
        return list(self.devices.keys())

    def label(self, key: str) -> str:
        """Obtiene el nombre legible (label) de un equipo dado su clave."""
        d = self.devices.get(key, {}) or {}
        return d.get("label", key)

    def token(self, key: str) -> str:
        """
        Obtiene el token de acceso de un equipo. Lee el nombre de la variable de
        entorno desde la configuración y busca el valor en el entorno (.env).
        """
        d = self.devices.get(key, {}) or {}
        env_name = d.get("env_token")
        if not env_name:
            raise RuntimeError(f"Falta env_token para device '{key}' en devices.yaml")
        val = os.getenv(env_name)
        if not val:
            raise RuntimeError(f"Falta variable de entorno {env_name} en .env")
        return val
