import requests
from requests.exceptions import Timeout, RequestException

class SmAPI:
    """
    Clase para interactuar con la API de Smability y obtener datos de los sensores.
    """
    def __init__(self, base_url: str, token: str, timeout: int = 30):
        """
        Inicializa la instancia de la API.
        
        Args:
            base_url: URL base de la API.
            token: Token de autenticación para la API.
            timeout: Tiempo de espera máximo para las peticiones (en segundos).
        """
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

        self.s = requests.Session()
        self.s.headers.update({
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) PythonRequests",
            "Connection": "close",
        })

    def get_data(self, sensor_id: str, dt_start: str, dt_end: str):
        """
        Obtiene los datos históricos de un sensor en un rango de fechas específico.
        
        Args:
            sensor_id: El ID del sensor a consultar.
            dt_start/dt_end: Rango de fechas en formato 'YYYY-MM-DD HH:MM:SS'.
            
        Returns: 
            Una lista de diccionarios con el formato [{'Data': 'xx', 'TimeStamp': 'YYYY-MM-DDTHH:MM:SS'}, ...]
        """
        url = f"{self.base_url}/GetData"
        params = {
            "token": self.token,
            "idSensor": sensor_id,
            "dtStart": dt_start,
            "dtEnd": dt_end,
        }

        try:
            r = self.s.get(url, params=params, timeout=self.timeout, headers={"Accept": "application/json"})
            r.raise_for_status()
            data = r.json()
            if not isinstance(data, list):
                print("⚠️ Smability: respuesta inesperada (no es lista).")
                return []
            return data

        except Timeout:
            print(f"⚠️ Smability timeout (>{self.timeout}s) sensor={sensor_id} {dt_start} -> {dt_end}")
            return []

        except RequestException as e:
            print(f"⚠️ Smability error HTTP sensor={sensor_id}: {e}")
            return []

        except ValueError as e:
            # JSON inválido u otro parseo
            print(f"⚠️ Smability JSON inválido sensor={sensor_id}: {e}")
            return []


    def latest(self, sensor_id: str, dt_start: str, dt_end: str):
        """
        Obtiene el registro más reciente de un sensor dentro de un rango de tiempo dado.
        
        Args:
            sensor_id: El ID del sensor a consultar.
            dt_start/dt_end: Rango de fechas en formato 'YYYY-MM-DD HH:MM:SS'.
            
        Returns:
            Un diccionario con el dato más reciente o None si no hay datos.
        """
        rows = self.get_data(sensor_id, dt_start, dt_end)
        if not rows:
            return None
        rows = sorted(rows, key=lambda x: x.get("TimeStamp", ""))
        return rows[-1]
