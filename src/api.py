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
            
            if sensor_id == "temp_ambiente":
                val = data.get("temperature_c")
            elif sensor_id == "hum_ambiente":
                val = data.get("humidity_percent")
                if val is None:
                    val = data.get("air_humidity_percent")
            elif sensor_id == "presion_atm":
                val = data.get("pressure_hpa")
            elif sensor_id == "resistencia_gas":
                val = data.get("gas_resistance_ohms")
            elif sensor_id == "hum_suelo":
                val = data.get("soil_moisture_percent")
            
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

class CloudAPI:
    """
    Clase para interactuar con el endpoint de AWS en la nube.
    """
    def __init__(self, url: str, timeout: int = 10):
        self.url = url
        self.timeout = timeout
        self.s = requests.Session()
        self.s.headers.update({
            "User-Agent": "BotIbero Cloud",
            "Connection": "close",
        })

    def get_current_data(self, sensor_id: str = None):
        try:
            r = self.s.get(self.url, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            
            val = None
            if sensor_id == "temp_ambiente":
                val = data.get("temperature")
            elif sensor_id == "hum_ambiente":
                val = data.get("humidity")
            elif sensor_id == "presion_atm":
                val = data.get("pressure")
            elif sensor_id == "resistencia_gas":
                val = data.get("gas")
                
            raw_ts = data.get("timestamp")
            if raw_ts:
                try:
                    dt = datetime.datetime.fromisoformat(raw_ts)
                    ts = dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    ts = raw_ts
            else:
                ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
            return {
                "Data": val,
                "TimeStamp": ts
            }
        except Exception as e:
            print(f"[!] AWS error HTTP: {e}")
            return None

    def get_camera_capture(self):
        return None

    def get_history_data(self, sensor_id: str = None, dt_start: str = None, dt_end: str = None):
        import os
        import pandas as pd
        from pathlib import Path
        
        csv_path = os.getenv("CSV_HUERTO_PATH")
        if not csv_path or not Path(csv_path).exists():
            return []
            
        try:
            df = pd.read_csv(csv_path)
            col_map = {
                "temp_ambiente": "temperature",
                "hum_ambiente": "humidity",
                "presion_atm": "pressure",
                "resistencia_gas": "gas"
            }
            if sensor_id not in col_map: 
                return []
                
            col = col_map[sensor_id]
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
            df = df.dropna(subset=['timestamp', col])
            
            if dt_start:
                start = pd.to_datetime(dt_start)
                df = df[df['timestamp'] >= start]
            if dt_end:
                end = pd.to_datetime(dt_end)
                df = df[df['timestamp'] <= end]
                
            rows = []
            for _, r in df.iterrows():
                rows.append({
                    "TimeStamp": r['timestamp'].strftime("%Y-%m-%d %H:%M:%S"),
                    "Data": r[col]
                })
            return rows
        except Exception as e:
            print(f"[!] Error leyendo historial de CSV AWS: {e}")
            return []

def get_api(dev_cfg, device_key: str):
    """
    Retorna la instancia correcta de API (Local o Cloud) según la configuración.
    """
    d = dev_cfg.config(device_key)
    if "cloud_url" in d:
        return CloudAPI(d["cloud_url"])
    else:
        return LocalESP32API(d.get("ip_address"))
