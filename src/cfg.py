import yaml

def load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

class Cfg:
    def __init__(self, sensors_path: str = "cfg/sensors.yaml"):
        self.raw = load_yaml(sensors_path)
        # raw["sensors"] is now a list of dicts: [{'id': 'temp_ambiente', 'alias': 'Temperatura', 'label': 'Temperatura Ambiental', 'unit': '°C'}, ...]
        self.sensors_list = self.raw.get("sensors", [])
        
        self.sensors = {}
        self.labels = {}
        self.units = {}
        for s in self.sensors_list:
            sid = str(s.get("id"))
            alias = s.get("alias", sid)
            self.sensors[sid] = alias
            self.labels[alias] = s.get("label", alias)
            self.units[alias] = s.get("unit", "")

    def alias(self, sensor_id: str) -> str:
        return self.sensors.get(str(sensor_id), str(sensor_id))

    def label(self, sensor_id: str) -> str:
        a = self.alias(sensor_id)
        return self.labels.get(a, f"Sensor {sensor_id}")

    def unit(self, sensor_id: str) -> str:
        a = self.alias(sensor_id)
        return self.units.get(a, "")
