import os
from dotenv import load_dotenv
from datetime import datetime
from dateutil.relativedelta import relativedelta

from api import SmAPI
from cfg import Cfg
from norm import Norm
from dt import parse_range, fmt_api
from dev import DevCfg

load_dotenv()

BASE_URL = os.getenv("SMABILITY_BASE_URL")
TZ_NAME = os.getenv("TZ", "America/Mexico_City")


def fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def avg_from_rows(rows: list[dict]) -> float | None:
    vals = []
    for r in rows:
        try:
            vals.append(float(r.get("Data")))
        except Exception:
            continue
    if not vals:
        return None
    return sum(vals) / len(vals)


def main(device_key: str = "iniat", sensor_id: int = 9):
    dev = DevCfg("cfg/devices.yaml")
    token = dev.token(device_key)
    dev_label = dev.label(device_key)

    api = SmAPI(BASE_URL, token)
    cfg = Cfg("cfg/sensors.yaml")
    norm = Norm("cfg/norms.yaml")

    label = cfg.label(sensor_id)
    unit = cfg.unit(sensor_id)
    alias = cfg.alias(sensor_id)

    # 1) Valor actual = último dato (miramos 10 minutos)
    end = datetime.now()
    start_last = end - relativedelta(minutes=10)
    last = api.latest(sensor_id, fmt(start_last), fmt(end))

    if not last:
        print(f"[{dev_label}] {label}: sin datos recientes.")
        return

    raw_last = last.get("Data")
    ts_last = last.get("TimeStamp")

    # 2) Promedio normativo
    # PM => 12h, NO2 => 1h
    if alias in {"pm25", "pm10"}:
        rng_norm = "12h"
        unit_in_for_norm = None
    elif alias == "no2":
        rng_norm = "1h"
        unit_in_for_norm = "ppb"  # tu YAML indica ppb
    else:
        # sensores sin norma por ahora
        rng_norm = "1h"
        unit_in_for_norm = None

    start_norm, end_norm = parse_range(rng_norm, TZ_NAME)
    rows_norm = api.get_data(sensor_id, fmt_api(start_norm), fmt_api(end_norm))
    avg_norm = avg_from_rows(rows_norm)

    sem = norm.check(alias, avg_norm, unit_in=unit_in_for_norm)

    # Si NO2: norma en ppm, pero mostramos ambos (ppb y ppm) si hay promedio
    no2_ppm = None
    if alias == "no2" and avg_norm is not None:
        no2_ppm = avg_norm / 1000.0

    print(f"[{dev_label}] {sem.emoji} {label}")
    print(f"Último: {raw_last} {unit}".strip())
    print(f"Hora último: {ts_last}")

    if alias in {"pm25", "pm10"}:
        if avg_norm is None:
            print("Promedio 12h: sin datos")
        else:
            print(f"Promedio 12h: {avg_norm:.1f} {unit}".strip())
    elif alias == "no2":
        if avg_norm is None:
            print("Promedio 1h: sin datos")
        else:
            # avg_norm está en ppb (promedio simple de Data); convertimos a ppm para referencia
            print(f"Promedio 1h: {avg_norm:.1f} {unit}".strip())
            print(f"Promedio 1h (ppm): {no2_ppm:.3f} ppm")
    else:
        if avg_norm is None:
            print("Promedio 1h: sin datos")
        else:
            print(f"Promedio 1h: {avg_norm:.2f} {unit}".strip())

    print(f"Semáforo (CDMX): {sem.name}")


if __name__ == "__main__":
    import sys
    dev_key = sys.argv[1] if len(sys.argv) > 1 else "iniat"
    sid = int(sys.argv[2]) if len(sys.argv) > 2 else 9
    main(dev_key, sid)

