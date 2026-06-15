from datetime import datetime
from dateutil.relativedelta import relativedelta
from dateutil import tz

def now(tz_name: str) -> datetime:
    return datetime.now(tz.gettz(tz_name))

def fmt_api(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def parse_range(rng: str, tz_name: str) -> tuple[datetime, datetime]:
    """
    Acepta:
      - "10m" (minutos), "1h", "1d"
      - "1m", "3m", "6m" (meses)  <-- OJO: aquí m=mes
      - "1mo", "3mo", "6mo" (meses explícito)
      - "1y"
      - "YYYY-MM-DD:YYYY-MM-DD"
    """
    rng = (rng or "").strip()
    end = now(tz_name)

    # Fechas manuales: 2026-02-01:2026-02-17
    if ":" in rng and len(rng.split(":")) == 2:
        a, b = rng.split(":")
        a = a.strip()
        b = b.strip()
        start_dt = datetime.strptime(a, "%Y-%m-%d").replace(tzinfo=tz.gettz(tz_name))
        end_dt = datetime.strptime(b, "%Y-%m-%d").replace(tzinfo=tz.gettz(tz_name))
        end_dt = end_dt.replace(hour=23, minute=59, second=59)
        return start_dt, end_dt

    r = rng.lower()

    # meses explícito: 1mo, 3mo, 6mo, 12mo, etc.
    if r.endswith("mo") and r[:-2].isdigit():
        n = int(r[:-2])
        return end - relativedelta(months=n), end

    # meses "cortos" por UX: 1m, 3m, 6m
    if r in {"1m", "3m", "6m"}:
        n = int(r[:-1])
        return end - relativedelta(months=n), end

    # minutos: 10m, 15m, 30m, 45m, 59m
    if r.endswith("m") and r[:-1].isdigit():
        n = int(r[:-1])
        return end - relativedelta(minutes=n), end

    # horas
    if r.endswith("h") and r[:-1].isdigit():
        n = int(r[:-1])
        return end - relativedelta(hours=n), end

    # días
    if r.endswith("d") and r[:-1].isdigit():
        n = int(r[:-1])
        return end - relativedelta(days=n), end

    # año
    if r == "1y":
        return end - relativedelta(years=1), end

    # default: 10 minutos
    return end - relativedelta(minutes=10), end


