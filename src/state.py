from dataclasses import dataclass

@dataclass
class UIState:
    device_key: str | None = None
    sensor_id: int | None = None
    mode: str | None = None   # None | "plot" | "csv"

