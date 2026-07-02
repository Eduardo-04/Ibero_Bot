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
        Obtiene la lectura instantánea scrapeando el HTML del ESP32 en la raíz (/).
        Retorna el formato simulado esperado: {'Data': valor, 'TimeStamp': 'YYYY-MM-DD HH:MM:SS'}
        """
        url = f"{self.base_url}/"
        try:
            r = self.s.get(url, timeout=self.timeout)
            r.raise_for_status()
            html = r.text
            
            val = 0
            if sensor_id == "hum_suelo" or not sensor_id:
                import re
                match = re.search(r"<div class='numero'>(\d+)%</div>", html)
                if match:
                    val = int(match.group(1))
                else:
                    print("⚠️ No se encontró la humedad en el HTML.")
            
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            return {
                "Data": val,
                "TimeStamp": ts
            }
        except Exception as e:
            print(f"⚠️ ESP32 error HTTP (current): {e}")
            return None

    def get_history_data(self, sensor_id: str = None, dt_start: str = None, dt_end: str = None):
        """
        Devuelve una lista vacía ya que la nueva versión del ESP32 no guarda historial.
        """
        return []
