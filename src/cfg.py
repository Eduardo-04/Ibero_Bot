import yaml
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

def load_yaml(path: str) -> dict:
    """Carga un archivo YAML y retorna su contenido como diccionario."""
    full = BASE_DIR / path
    with open(full, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

class Cfg:
    """
    Clase encargada de cargar y administrar la configuración de los sensores
    desde un archivo YAML.
    """
    def __init__(self, sensors_path: str = "cfg/sensors.yaml"):
        """Inicializa la configuración leyendo el archivo especificado."""
        self.raw = load_yaml(sensors_path)
        # raw["sensors"] is now a list of dicts: [{'id': 'temp_ambiente', 'alias': 'Temperatura', 'label': 'Temperatura Ambiental', 'unit': '°C'}, ...]
        self.sensors_list = self.raw.get("sensors", [])
        
        self.sensors_ids = []
        self.labels = {}
        self.units = {}
        self.exclusions = {}
        # Mapea los IDs a labels y units para acceso rápido
        for s in self.sensors_list:
            sid = str(s.get("id"))
            self.sensors_ids.append(sid)
            self.labels[sid] = s.get("label", sid)
            self.units[sid] = s.get("unit", "")
            self.exclusions[sid] = s.get("exclude", [])

    def is_excluded(self, sensor_id: str, device_key: str) -> bool:
        """Verifica si un sensor debe ocultarse para un dispositivo específico."""
        return device_key in self.exclusions.get(str(sensor_id), [])

    def label(self, sensor_id: str) -> str:
        """Obtiene el nombre legible (label) de un sensor dado su ID."""
        return self.labels.get(str(sensor_id), f"Sensor {sensor_id}")

    def unit(self, sensor_id: str) -> str:
        """Obtiene la unidad de medida (e.g., °C, %) de un sensor dado su ID."""
        return self.units.get(str(sensor_id), "")
