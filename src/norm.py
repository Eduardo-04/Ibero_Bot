from dataclasses import dataclass
from pathlib import Path
import yaml
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent

@dataclass
class Semaforo:
    """Clase de datos que representa el estado normativo (semáforo) de un sensor."""
    lvl: str        # good | fair | bad | vbad | xvbad | na
    emoji: str      # Emoji representativo del estado (ej. 🟢, 🔴)
    name: str       # Nombre legible (ej. "Buena", "Aceptable")
    msg: str        # Mensaje descriptivo corto

class Norm:
    """
    Clase para manejar las normativas y límites aceptables de las mediciones, 
    cargadas desde un archivo de configuración (norms.yaml).
    """
    def __init__(self, path: str = "cfg/norms.yaml"):
        """Inicializa leyendo el archivo de normativas."""
        full = BASE_DIR / path
        with open(full, "r", encoding="utf-8") as f:
            self.raw = yaml.safe_load(f) or {}
        self.limits = self.raw.get("limits", {}) or {}

    def _bands(self, sensor_id: str):
        """Retorna las bandas (niveles de semáforo) configuradas para un sensor específico."""
        return (self.limits.get(sensor_id) or {}).get("bands") or []

    def _target_unit(self, sensor_id: str) -> str:
        """Obtiene la unidad de medida en la que está expresada la norma para un sensor."""
        return ((self.limits.get(sensor_id) or {}).get("unit") or "").strip().lower()

    def _convert(self, sensor_id: str, value: float, unit_in: Optional[str]) -> float:
        """
        Convierte value a la unidad esperada por la norma (si aplica).
        Hoy solo necesitamos NO2: ppb -> ppm.
        """
        unit_in = (unit_in or "").strip().lower()
        unit_out = self._target_unit(sensor_id)

        # NO2 norma en ppm; sensor suele venir en ppb
        if sensor_id == "no2" and unit_out == "ppm":
            if unit_in == "ppb":
                return value / 1000.0
            # si ya viene en ppm o no sabemos, lo dejamos igual
            return value

        # PM suelen venir en ug/m3, no convertimos aquí
        return value

    def check(self, sensor_id: str, value: Optional[float], unit_in: Optional[str] = None) -> Semaforo:
        """
        Evalúa el valor de una medición contra las bandas normativas configuradas y
        retorna un objeto Semaforo con el estado resultante.
        
        Args:
            sensor_id: El ID del sensor (ej. 'temp_ambiente').
            value: El valor de la medición (o promedio).
            unit_in: La unidad de entrada de la medición.
        
        Returns:
            Semaforo correspondiente al nivel de la medición.
        """
        if value is None:
            return Semaforo("na", "⚪", "Sin dato", "Sin dato.")

        bands = self._bands(sensor_id)
        if not bands:
            return Semaforo("na", "⚪", "Sin norma", "Sin norma configurada.")

        try:
            v = float(value)
        except Exception:
            return Semaforo("na", "⚪", "Sin dato", "Dato inválido.")

        v = self._convert(sensor_id, v, unit_in)

        # Recorre bandas en orden; max==null significa “sin límite superior”
        for b in bands:
            bmax = b.get("max", None)
            lvl = b.get("lvl", "na")
            emoji = b.get("emoji", "⚪")
            name = b.get("name", "Sin norma")

            if bmax is None:
                return Semaforo(lvl, emoji, name, name)

            try:
                bmax_f = float(bmax)
            except Exception:
                continue

            if v <= bmax_f:
                return Semaforo(lvl, emoji, name, name)

        # fallback (si algo raro en bandas)
        last = bands[-1]
        return Semaforo(last.get("lvl", "na"), last.get("emoji", "⚪"), last.get("name", "Sin norma"), last.get("name", "Sin norma"))

