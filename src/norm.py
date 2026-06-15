from dataclasses import dataclass
from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent

@dataclass
class Semaforo:
    lvl: str        # good | fair | bad | vbad | xvbad | na
    emoji: str
    name: str       # "Buena", "Aceptable", etc.
    msg: str        # texto corto para mostrar

class Norm:
    def __init__(self, path: str = "cfg/norms.yaml"):
        full = BASE_DIR / path
        with open(full, "r", encoding="utf-8") as f:
            self.raw = yaml.safe_load(f) or {}
        self.limits = self.raw.get("limits", {}) or {}

    def _bands(self, alias: str):
        return (self.limits.get(alias) or {}).get("bands") or []

    def _target_unit(self, alias: str) -> str:
        return ((self.limits.get(alias) or {}).get("unit") or "").strip().lower()

    def _convert(self, alias: str, value: float, unit_in: str | None) -> float:
        """
        Convierte value a la unidad esperada por la norma (si aplica).
        Hoy solo necesitamos NO2: ppb -> ppm.
        """
        unit_in = (unit_in or "").strip().lower()
        unit_out = self._target_unit(alias)

        # NO2 norma en ppm; sensor suele venir en ppb
        if alias == "no2" and unit_out == "ppm":
            if unit_in == "ppb":
                return value / 1000.0
            # si ya viene en ppm o no sabemos, lo dejamos igual
            return value

        # PM suelen venir en ug/m3, no convertimos aquí
        return value

    def check(self, alias: str, value: float | None, unit_in: str | None = None) -> Semaforo:
        """
        Evalúa el semáforo según cfg/norms.yaml (bandas).
        value: concentración (promedio normativo)
        unit_in: unidad de entrada (p.ej. 'ppb' para NO2). Para PM puedes dejar None.
        """
        if value is None:
            return Semaforo("na", "⚪", "Sin dato", "Sin dato.")

        bands = self._bands(alias)
        if not bands:
            return Semaforo("na", "⚪", "Sin norma", "Sin norma configurada.")

        try:
            v = float(value)
        except Exception:
            return Semaforo("na", "⚪", "Sin dato", "Dato inválido.")

        v = self._convert(alias, v, unit_in)

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

