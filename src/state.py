from dataclasses import dataclass
from typing import Optional

@dataclass
class UIState:
    """
    Clase de datos para mantener el estado de la interfaz de usuario en Telegram 
    (por chat_id). Rastrea el equipo y sensor actualmente seleccionados, y el modo de acción.
    """
    device_key: Optional[str] = None
    sensor_id: Optional[str] = None
    mode: Optional[str] = None   # None | "plot" | "csv"
