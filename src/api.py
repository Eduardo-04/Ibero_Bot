import requests
from requests.exceptions import Timeout, RequestException
import csv
from io import StringIO
import datetime

class LocalESP32API:
    """
    Clase para interactuar con el servidor HTTP local del ESP32.
    """
    def __init__(self, ip_address: str, timeout: int = 10):
        """
        Inicializa la instancia de la API local.
        
        Args:
            ip_address: Dirección IP del ESP32 en la red local.
            timeout: Tiempo de espera máximo para las peticiones.
        """
        self.base_url = f"http://{ip_address}"
        self.timeout = timeout

        self.s = requests.Session()
        self.s.headers.update({
            "User-Agent": "BotIbero Local",
            "Connection": "close",
        })

    def get_current_data(self, sensor_id: str = None):
        """
        Obtiene la lectura instantánea del ESP32 a través del endpoint JSON en el puerto 81.
        Retorna el formato simulado esperado: {'Data': valor, 'TimeStamp': 'YYYY-MM-DD HH:MM:SS'}
        """
        url = f"{self.base_url}:81/sensor"
        try:
            r = self.s.get(url, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            
            val = None
            if sensor_id == "temp_ambiente":
                val = data.get("temperature_c")
            elif sensor_id == "hum_ambiente":
                val = data.get("humidity_percent")
            elif sensor_id == "presion_atm":
                val = data.get("pressure_hpa")
            elif sensor_id == "resistencia_gas":
                val = data.get("gas_resistance_ohms")
            
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            return {
                "Data": val,
                "TimeStamp": ts
            }
        except Exception as e:
            print(f"[!] ESP32 error HTTP (current): {e}")
            return None

    def get_camera_capture(self):
        """
        Obtiene la imagen de la cámara del ESP32 (JPEG) a través del puerto 80.
        Retorna los bytes de la imagen.
        """
        url = f"{self.base_url}/capture"
        try:
            r = self.s.get(url, timeout=self.timeout)
            r.raise_for_status()
            return r.content
        except Exception as e:
            print(f"[!] ESP32 error HTTP (camera): {e}")
            return None

    def get_history_data(self, sensor_id: str = None, dt_start: str = None, dt_end: str = None):
        """
        Devuelve una lista vacía ya que la nueva versión del ESP32 no guarda historial.
        """
        return []
