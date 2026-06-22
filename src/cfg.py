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
        
        self.sensors = {}
        self.labels = {}
        self.units = {}
        # Mapea los IDs a alias, labels y units para acceso rápido
        for s in self.sensors_list:
            sid = str(s.get("id"))
            alias = s.get("alias", sid)
            self.sensors[sid] = alias
            self.labels[alias] = s.get("label", alias)
            self.units[alias] = s.get("unit", "")

    def alias(self, sensor_id: str) -> str:
        """Obtiene el alias interno de un sensor dado su ID."""
        return self.sensors.get(str(sensor_id), str(sensor_id))

    def label(self, sensor_id: str) -> str:
        """Obtiene el nombre legible (label) de un sensor dado su ID."""
        a = self.alias(sensor_id)
        return self.labels.get(a, f"Sensor {sensor_id}")

    def unit(self, sensor_id: str) -> str:
        """Obtiene la unidad de medida (e.g., °C, %) de un sensor dado su ID."""
        a = self.alias(sensor_id)
        return self.units.get(a, "")
