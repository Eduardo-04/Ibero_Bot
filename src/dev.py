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

    def config(self, key: str) -> dict:
        """Retorna el diccionario de configuración completo de un equipo."""
        return self.devices.get(key, {})

    def ip(self, key: str) -> str:
        """
        Obtiene la dirección IP de un equipo en la red local.
        """
        d = self.devices.get(key, {}) or {}
        ip_addr = d.get("ip_address")
        if not ip_addr and not d.get("cloud_url"):
            raise RuntimeError(f"Falta ip_address o cloud_url para device '{key}' en devices.yaml")
        return ip_addr or ""
