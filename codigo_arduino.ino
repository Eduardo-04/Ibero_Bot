/*
  XIAO ESP32S3 Sense CAM + BME688/BME680
  Version: IP fija IBERO + video real optimizado para celular/PC + BME688 cada 30 segundos

  Funciones:
  - El XIAO usa IP fija en la red Primavera26.
  - Si no conecta, crea red propia de respaldo: XIAO-CAM-BME688.
  - Pagina principal ligera con stream MJPEG real y datos del BME688.
  - Endpoint /sensor en JSON para dashboard externo.
  - El sensor se actualiza cada 30 segundos sin bloquear el stream.

  Librerias necesarias en Arduino IDE:
  - Adafruit BME680 Library
  - Adafruit Unified Sensor

  Conexiones BME688 en I2C:
  - BME688 VCC/VIN -> 3V3 del XIAO
  - BME688 GND     -> GND del XIAO
  - BME688 SDI/SDA -> D4 del XIAO = GPIO5
  - BME688 SCK/SCL -> D5 del XIAO = GPIO6

  IMPORTANTE:
  - En Tools/Herramientas activa PSRAM: Enabled u OPI PSRAM.
  - Usa una red WiFi de 2.4 GHz.
*/

// IMPORTANTE:
// esp_camera.h y Adafruit Unified Sensor usan el mismo nombre "sensor_t".
// Renombramos SOLO el sensor_t de la camara para evitar el choque de compilacion.
#define sensor_t camera_sensor_t
#include "esp_camera.h"
#undef sensor_t

#include <WiFi.h>
#include "esp_http_server.h"
#include <Wire.h>
#include <Adafruit_BME680.h>

// =====================================================
// CONFIGURACION DEL USUARIO
// =====================================================

const char* DEVICE_ID = "xiao_cam_bme688";

// Red de la IBERO con IP fija.
const char* WIFI_SSID = "Primavera26";
const char* WIFI_PASSWORD = "Ib3r02026pR1m";

// IP fija asignada a este sistema.
// Como por DHCP te dio 172.22.85.38, dejamos esa misma.
// En Primavera26 normalmente se usa mascara /22: 255.255.252.0.
// Para 172.22.85.x, el gateway esperado es 172.22.87.254.
IPAddress LOCAL_IP(172, 22, 85, 38);
IPAddress GATEWAY(172, 22, 87, 254);
IPAddress SUBNET(255, 255, 252, 0);
IPAddress PRIMARY_DNS(172, 22, 87, 254);
IPAddress SECONDARY_DNS(8, 8, 8, 8);

// Red propia si no logra conectarse a Primavera26.
const char* AP_SSID = "XIAO-CAM-BME688";
const char* AP_PASSWORD = "12345678";

const unsigned long WIFI_CONNECT_TIMEOUT_MS = 45000;
const unsigned long SENSOR_READ_INTERVAL_MS = 30000;  // 30 segundos

// Ajustes de camara: video real MJPEG, pero ligero para celular.
// Resolucion recomendada para video estable: VGA.
// Para mas calidad prueba FRAMESIZE_SVGA. Para mas fluidez prueba FRAMESIZE_QVGA.
const framesize_t CAMERA_FRAME_SIZE = FRAMESIZE_VGA;
const int CAMERA_JPEG_QUALITY = 14;  // Menor numero = mejor calidad, pero mas lento. 10-16 recomendado.
const int STREAM_DELAY_MS = 35;      // 35 ms aprox. 20-30 fps teoricos, depende de WiFi.

// Pines I2C externos del XIAO ESP32S3 Sense.
const int BME_SDA_PIN = 5;  // D4 = SDA = GPIO5
const int BME_SCL_PIN = 6;  // D5 = SCL = GPIO6

// =====================================================
// PINES CAMARA XIAO ESP32S3 SENSE
// =====================================================

#define PWDN_GPIO_NUM     -1
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM     10

#define SIOD_GPIO_NUM     40
#define SIOC_GPIO_NUM     39

#define Y9_GPIO_NUM       48
#define Y8_GPIO_NUM       11
#define Y7_GPIO_NUM       12
#define Y6_GPIO_NUM       14
#define Y5_GPIO_NUM       16
#define Y4_GPIO_NUM       18
#define Y3_GPIO_NUM       17
#define Y2_GPIO_NUM       15

#define VSYNC_GPIO_NUM    38
#define HREF_GPIO_NUM     47
#define PCLK_GPIO_NUM     13

// =====================================================
// OBJETOS Y VARIABLES GLOBALES
// =====================================================

httpd_handle_t video_httpd = NULL;   // Pagina + video en puerto 80 para celular/PC
httpd_handle_t sensor_httpd = NULL;  // JSON del BME688 en puerto 81 para no congelar el video
Adafruit_BME680 bme;

bool usingAccessPoint = false;
bool bmeDetected = false;
uint8_t bmeAddress = 0x00;
unsigned long lastSensorReadMillis = 0;

struct SensorData {
  bool ok = false;
  float temperature = NAN;
  float humidity = NAN;
  float pressure = NAN;
  float gasResistance = NAN;
  unsigned long millisTime = 0;
};

SensorData lastData;

// =====================================================
// STREAM MJPEG
// =====================================================

#define PART_BOUNDARY "123456789000000000000987654321"
static const char* STREAM_CONTENT_TYPE = "multipart/x-mixed-replace;boundary=" PART_BOUNDARY;
static const char* STREAM_BOUNDARY = "\r\n--" PART_BOUNDARY "\r\n";
static const char* STREAM_PART = "Content-Type: image/jpeg\r\nContent-Length: %zu\r\n\r\n";

// =====================================================
// FUNCIONES AUXILIARES
// =====================================================

String floatToString(float value, int decimals) {
  if (isnan(value)) return "null";
  return String(value, decimals);
}

String floatToText(float value, int decimals) {
  if (isnan(value)) return "--";
  return String(value, decimals);
}

String getCurrentIP() {
  if (usingAccessPoint) return WiFi.softAPIP().toString();
  return WiFi.localIP().toString();
}

String getCurrentSSID() {
  if (usingAccessPoint) return String(AP_SSID);
  return WiFi.SSID();
}

String getCurrentBSSID() {
  if (!usingAccessPoint && WiFi.status() == WL_CONNECTED) {
    return WiFi.BSSIDstr();
  }

  if (usingAccessPoint) {
    return WiFi.softAPmacAddress();
  }

  return "SIN_BSSID";
}

String getConnectionMode() {
  if (usingAccessPoint) return "Red propia del ESP32/AP";
  if (WiFi.status() == WL_CONNECTED) return "Conectado a WiFi con IP fija";
  return "Sin conexion";
}

String wifiStatusToText(wl_status_t status) {
  switch (status) {
    case WL_IDLE_STATUS: return "WL_IDLE_STATUS: esperando";
    case WL_NO_SSID_AVAIL: return "WL_NO_SSID_AVAIL: no se encontro el SSID";
    case WL_SCAN_COMPLETED: return "WL_SCAN_COMPLETED: escaneo completado";
    case WL_CONNECTED: return "WL_CONNECTED: conectado";
    case WL_CONNECT_FAILED: return "WL_CONNECT_FAILED: fallo de conexion/password";
    case WL_CONNECTION_LOST: return "WL_CONNECTION_LOST: conexion perdida";
    case WL_DISCONNECTED: return "WL_DISCONNECTED: desconectado";
    default: return "Estado WiFi desconocido: " + String((int)status);
  }
}

String encryptionTypeToText(wifi_auth_mode_t type) {
  switch (type) {
    case WIFI_AUTH_OPEN: return "Abierta";
    case WIFI_AUTH_WEP: return "WEP";
    case WIFI_AUTH_WPA_PSK: return "WPA";
    case WIFI_AUTH_WPA2_PSK: return "WPA2";
    case WIFI_AUTH_WPA_WPA2_PSK: return "WPA/WPA2";
    case WIFI_AUTH_WPA2_ENTERPRISE: return "WPA2-Enterprise";
    default: return "Seguridad tipo " + String((int)type);
  }
}

bool scanForConfiguredSSID() {
  Serial.println();
  Serial.println("Escaneando redes WiFi visibles...");

  int networkCount = WiFi.scanNetworks(false, true);

  if (networkCount <= 0) {
    Serial.println("No se detectaron redes WiFi.");
    return false;
  }

  bool foundTarget = false;

  Serial.print("Redes encontradas: ");
  Serial.println(networkCount);

  for (int i = 0; i < networkCount; i++) {
    String ssid = WiFi.SSID(i);
    int32_t rssi = WiFi.RSSI(i);
    uint8_t channel = WiFi.channel(i);
    wifi_auth_mode_t enc = WiFi.encryptionType(i);

    Serial.print(i + 1);
    Serial.print(") SSID: ");
    Serial.print(ssid.length() ? ssid : "<oculta>");
    Serial.print(" | RSSI: ");
    Serial.print(rssi);
    Serial.print(" dBm | Canal: ");
    Serial.print(channel);
    Serial.print(" | BSSID: ");
    Serial.print(WiFi.BSSIDstr(i));
    Serial.print(" | Seguridad: ");
    Serial.println(encryptionTypeToText(enc));

    if (ssid == String(WIFI_SSID)) {
      foundTarget = true;
    }
  }

  WiFi.scanDelete();

  if (foundTarget) {
    Serial.print("La red configurada SI fue detectada: ");
    Serial.println(WIFI_SSID);
  } else {
    Serial.print("La red configurada NO fue detectada: ");
    Serial.println(WIFI_SSID);
    Serial.println("Puede estar fuera de rango, ser solo 5 GHz o tener senal debil.");
  }

  Serial.println();
  return foundTarget;
}

void startFallbackAccessPoint() {
  Serial.println("Creando red propia del ESP32 como respaldo...");
  WiFi.disconnect(true, true);
  delay(500);
  WiFi.mode(WIFI_AP);
  delay(500);

  usingAccessPoint = true;

  IPAddress apIP(192, 168, 4, 1);
  IPAddress apGateway(192, 168, 4, 1);
  IPAddress apSubnet(255, 255, 255, 0);
  WiFi.softAPConfig(apIP, apGateway, apSubnet);

  bool apOk = WiFi.softAP(AP_SSID, AP_PASSWORD, 6, 0, 4);

  if (apOk) {
    Serial.println("Red propia creada correctamente.");
    Serial.print("Nombre de red: ");
    Serial.println(AP_SSID);
    Serial.print("Contrasena: ");
    Serial.println(AP_PASSWORD);
    Serial.print("Abre: http://");
    Serial.println(WiFi.softAPIP());
    Serial.println("Si el celular dice 'sin internet', selecciona mantener conexion.");
  } else {
    Serial.println("Error: no se pudo crear la red propia.");
  }
}

void startWiFiFixed() {
  Serial.println();
  Serial.println("========== WIFI IP FIJA ==========");
  Serial.print("Equipo: ");
  Serial.println(DEVICE_ID);
  Serial.print("SSID configurado: ");
  Serial.println(WIFI_SSID);

  usingAccessPoint = false;

  WiFi.persistent(false);
  WiFi.disconnect(true, true);
  delay(1000);

  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);

  Serial.print("MAC WiFi del XIAO: ");
  Serial.println(WiFi.macAddress());

  scanForConfiguredSSID();

  Serial.println("Configurando IP fija...");
  Serial.print("LOCAL_IP: ");
  Serial.println(LOCAL_IP);
  Serial.print("GATEWAY: ");
  Serial.println(GATEWAY);
  Serial.print("SUBNET: ");
  Serial.println(SUBNET);

  bool configOk = WiFi.config(LOCAL_IP, GATEWAY, SUBNET, PRIMARY_DNS, SECONDARY_DNS);

  if (!configOk) {
    Serial.println("Advertencia: WiFi.config fallo. Intentare conectar de todos modos.");
  }

  Serial.println("Conectando a WiFi con IP fija...");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long startAttemptTime = millis();

  while (WiFi.status() != WL_CONNECTED && millis() - startAttemptTime < WIFI_CONNECT_TIMEOUT_MS) {
    delay(500);
    Serial.print(".");

    if ((millis() - startAttemptTime) % 5000 < 600) {
      Serial.print(" [");
      Serial.print(wifiStatusToText(WiFi.status()));
      Serial.print("] ");
    }
  }

  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    usingAccessPoint = false;
    Serial.println("WiFi conectado correctamente con IP fija");
    Serial.print("SSID conectado: ");
    Serial.println(WiFi.SSID());
    Serial.print("BSSID conectado: ");
    Serial.println(WiFi.BSSIDstr());
    Serial.print("IP fija: http://");
    Serial.println(WiFi.localIP());
    Serial.print("Gateway/router: ");
    Serial.println(WiFi.gatewayIP());
    Serial.print("Mascara de subred: ");
    Serial.println(WiFi.subnetMask());
    Serial.print("DNS: ");
    Serial.println(WiFi.dnsIP());
    Serial.print("RSSI/senal: ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");

    if (WiFi.localIP() != LOCAL_IP) {
      Serial.println("Aviso: la IP final no coincide con LOCAL_IP. Revisa gateway/subnet o conflicto de red.");
    }
  } else {
    Serial.println("No se pudo conectar a Primavera26 con IP fija.");
    Serial.print("Estado final: ");
    Serial.println(wifiStatusToText(WiFi.status()));
    Serial.println("Se inicia red propia para poder entrar a la pagina.");
    startFallbackAccessPoint();
  }

  Serial.println("==================================");
  Serial.println();
}

// =====================================================
// SENSOR BME688/BME680
// =====================================================

bool startBME688() {
  Serial.println();
  Serial.println("========== BME688 ==========");
  Serial.print("Iniciando I2C en SDA GPIO");
  Serial.print(BME_SDA_PIN);
  Serial.print(" / SCL GPIO");
  Serial.println(BME_SCL_PIN);

  Wire.begin(BME_SDA_PIN, BME_SCL_PIN);
  Wire.setClock(100000);

  if (bme.begin(0x76, &Wire)) {
    bmeDetected = true;
    bmeAddress = 0x76;
  } else if (bme.begin(0x77, &Wire)) {
    bmeDetected = true;
    bmeAddress = 0x77;
  } else {
    bmeDetected = false;
    bmeAddress = 0x00;
  }

  if (!bmeDetected) {
    Serial.println("Error: no se detecto el BME688/BME680 en 0x76 ni 0x77.");
    Serial.println("Revisa VCC 3V3, GND, SDI/SDA en D4 y SCK/SCL en D5.");
    Serial.println("Tambien revisa que el modulo este en modo I2C.");
    Serial.println("============================");
    Serial.println();
    return false;
  }

  Serial.print("BME688/BME680 detectado en direccion I2C 0x");
  Serial.println(bmeAddress, HEX);

  bme.setTemperatureOversampling(BME680_OS_8X);
  bme.setHumidityOversampling(BME680_OS_2X);
  bme.setPressureOversampling(BME680_OS_4X);
  bme.setIIRFilterSize(BME680_FILTER_SIZE_3);

  // Calentador interno para resistencia de gas.
  bme.setGasHeater(320, 150);

  Serial.println("BME688/BME680 iniciado correctamente");
  Serial.println("============================");
  Serial.println();
  return true;
}

SensorData readBME688() {
  SensorData data;
  data.millisTime = millis();

  if (!bmeDetected) {
    data.ok = false;
    return data;
  }

  if (bme.performReading()) {
    data.ok = true;
    data.temperature = bme.temperature;
    data.humidity = bme.humidity;
    data.pressure = bme.pressure / 100.0;       // Pa a hPa
    data.gasResistance = bme.gas_resistance;    // Ohms
  } else {
    data.ok = false;
  }

  return data;
}

void printSensorData(const SensorData& data) {
  Serial.println("========== LECTURA BME688 ==========");
  Serial.print("Millis: ");
  Serial.println(data.millisTime);
  Serial.print("Estado: ");
  Serial.println(data.ok ? "OK" : "ERROR");

  if (data.ok) {
    Serial.print("Temperatura: ");
    Serial.print(data.temperature);
    Serial.println(" C");

    Serial.print("Humedad: ");
    Serial.print(data.humidity);
    Serial.println(" %");

    Serial.print("Presion: ");
    Serial.print(data.pressure);
    Serial.println(" hPa");

    Serial.print("Gas: ");
    Serial.print(data.gasResistance);
    Serial.println(" Ohms");
  }

  Serial.println("====================================");
  Serial.println();
}

void updateSensorIfNeeded() {
  unsigned long now = millis();

  if (now - lastSensorReadMillis >= SENSOR_READ_INTERVAL_MS) {
    lastData = readBME688();
    printSensorData(lastData);
    lastSensorReadMillis = now;
  }
}

// =====================================================
// CAMARA
// =====================================================

bool startCamera() {
  Serial.println();
  Serial.println("========== CAMARA ==========");

  camera_config_t config = {};

  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;

  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;

  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;

  // Si tu version del core ESP32 marca error aqui, cambia sccb por sscb.
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;

  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;

  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;

  if (psramFound()) {
    Serial.println("PSRAM detectada");
    config.frame_size = CAMERA_FRAME_SIZE;
    config.jpeg_quality = CAMERA_JPEG_QUALITY;
    config.fb_count = 2;
    config.fb_location = CAMERA_FB_IN_PSRAM;
    config.grab_mode = CAMERA_GRAB_LATEST;
  } else {
    Serial.println("PSRAM NO detectada, usando QVGA basico");
    config.frame_size = FRAMESIZE_QVGA;
    config.jpeg_quality = 16;
    config.fb_count = 1;
    config.fb_location = CAMERA_FB_IN_DRAM;
    config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  }

  esp_err_t err = esp_camera_init(&config);

  if (err != ESP_OK) {
    Serial.printf("ERROR CAMARA. Codigo: 0x%x\n", err);
    Serial.println("Revisa flex de camara y PSRAM activada.");
    Serial.println("============================");
    Serial.println();
    return false;
  }

  Serial.println("Camara iniciada correctamente");

  camera_sensor_t *s = esp_camera_sensor_get();

  if (s != NULL) {
    s->set_brightness(s, 1);
    s->set_contrast(s, 1);
    s->set_saturation(s, 0);

    // Si sale volteada, descomenta una o ambas:
    // s->set_vflip(s, 1);
    // s->set_hmirror(s, 1);
  }

  Serial.println("============================");
  Serial.println();
  return true;
}

// =====================================================
// SERVIDOR WEB HTTPD
// =====================================================

static esp_err_t index_handler(httpd_req_t *req) {
  String html = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>XIAO CAM + BME688</title>
  <style>
    * { box-sizing: border-box; }
    body {
      font-family: Arial, sans-serif;
      background: #0d1117;
      color: #f5f5f5;
      margin: 0;
      padding: 12px;
      text-align: center;
    }
    h1 {
      font-size: 20px;
      margin: 8px 0 2px;
    }
    .sub {
      color: #9da7b1;
      font-size: 12px;
      margin-bottom: 10px;
    }
    .wrap {
      width: 100%;
      max-width: 980px;
      margin: 0 auto;
    }
    .box {
      background: #151b23;
      border: 1px solid #2b3542;
      border-radius: 12px;
      padding: 10px;
      margin-bottom: 10px;
    }
    img {
      display: block;
      width: 100%;
      max-width: 850px;
      margin: 0 auto;
      border-radius: 10px;
      background: #000;
      border: 1px solid #303b48;
    }
    .sensor {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 8px;
    }
    .card {
      background: #0f141b;
      border: 1px solid #27313d;
      border-radius: 10px;
      padding: 10px 6px;
    }
    .label {
      color: #9da7b1;
      font-size: 12px;
    }
    .val {
      font-size: 22px;
      font-weight: bold;
      margin-top: 5px;
      line-height: 1.1;
    }
    .unit {
      color: #9da7b1;
      font-size: 11px;
      margin-top: 2px;
    }
    .info {
      color: #b8c2cc;
      font-size: 12px;
      line-height: 1.5;
      margin-top: 8px;
      word-break: break-word;
    }
    .ok { color: #42e384; font-weight: bold; }
    .bad { color: #ff7070; font-weight: bold; }
    a {
      color: #7cc7ff;
      text-decoration: none;
    }
    @media (max-width: 700px) {
      body { padding: 8px; }
      h1 { font-size: 18px; }
      .sensor { grid-template-columns: repeat(2, 1fr); }
      .val { font-size: 20px; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <h1>XIAO ESP32S3 CAM + BME688</h1>
    <div class="sub">Video en vivo MJPEG + sensor cada 30 s</div>

    <div class="box">
      <img id="cam" src="/stream" alt="Camara en vivo">
    </div>

    <div class="box">
      <div class="sensor">
        <div class="card">
          <div class="label">Temperatura</div>
          <div class="val"><span id="temp">%TEMP%</span></div>
          <div class="unit">°C</div>
        </div>
        <div class="card">
          <div class="label">Humedad</div>
          <div class="val"><span id="hum">%HUM%</span></div>
          <div class="unit">%</div>
        </div>
        <div class="card">
          <div class="label">Presion</div>
          <div class="val"><span id="press">%PRESS%</span></div>
          <div class="unit">hPa</div>
        </div>
        <div class="card">
          <div class="label">Gas</div>
          <div class="val"><span id="gas">%GAS%</span></div>
          <div class="unit">Ω</div>
        </div>
      </div>

      <div class="info">
        IP: <b>http://%IP%</b> &nbsp; | &nbsp;
        SSID: <b>%SSID%</b> &nbsp; | &nbsp;
        BSSID: <b>%BSSID%</b><br>
        Sensor: <span id="bmeStatus">%BME_STATUS%</span> &nbsp; | &nbsp;
        I2C: <span id="bmeAddress">%BME_ADDR%</span> &nbsp; | &nbsp;
        Última lectura: <span id="lastMillis">%MILLIS%</span> ms<br>
        JSON: <a href="%SENSOR_URL%" target="_blank">%SENSOR_URL%</a>
      </div>
    </div>
  </div>

  <script>
    const sensorUrl = '%SENSOR_URL%';

    function setText(id, value) {
      const el = document.getElementById(id);
      if (el) el.textContent = value;
    }

    function fmt(value, decimals) {
      if (value === null || value === undefined || isNaN(value)) return '--';
      return Number(value).toFixed(decimals);
    }

    async function updateSensor() {
      try {
        const res = await fetch(sensorUrl + '?t=' + Date.now(), { cache: 'no-store' });
        const data = await res.json();

        setText('temp', fmt(data.temperature_c, 2));
        setText('hum', fmt(data.humidity_percent, 2));
        setText('press', fmt(data.pressure_hpa, 2));
        setText('gas', fmt(data.gas_resistance_ohms, 0));
        setText('lastMillis', data.millis);
        setText('bmeAddress', data.bme_i2c_address);

        const status = document.getElementById('bmeStatus');
        if (data.bme_ok) {
          status.textContent = 'OK';
          status.className = 'ok';
        } else {
          status.textContent = 'ERROR';
          status.className = 'bad';
        }
      } catch (e) {
        const status = document.getElementById('bmeStatus');
        status.textContent = 'SIN RESPUESTA';
        status.className = 'bad';
      }
    }

    setInterval(updateSensor, 30000);
  </script>
</body>
</html>
)rawliteral";

  String sensorUrl = "http://" + getCurrentIP() + ":81/sensor";

  html.replace("%DEVICE_ID%", String(DEVICE_ID));
  html.replace("%IP%", getCurrentIP());
  html.replace("%SSID%", getCurrentSSID());
  html.replace("%BSSID%", getCurrentBSSID());
  html.replace("%TEMP%", floatToText(lastData.temperature, 2));
  html.replace("%HUM%", floatToText(lastData.humidity, 2));
  html.replace("%PRESS%", floatToText(lastData.pressure, 2));
  html.replace("%GAS%", floatToText(lastData.gasResistance, 0));
  html.replace("%MILLIS%", String(lastData.millisTime));
  html.replace("%BME_STATUS%", lastData.ok ? "OK" : "ERROR");
  html.replace("%BME_ADDR%", bmeDetected ? ("0x" + String(bmeAddress, HEX)) : "NO_DETECTADO");
  html.replace("%SENSOR_URL%", sensorUrl);

  httpd_resp_set_type(req, "text/html");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  return httpd_resp_send(req, html.c_str(), html.length());
}

static esp_err_t sensor_handler(httpd_req_t *req) {
  String json = "{";
  json += "\"device_id\":\"" + String(DEVICE_ID) + "\",";
  json += "\"connection_mode\":\"" + getConnectionMode() + "\",";
  json += "\"wifi_ssid\":\"" + getCurrentSSID() + "\",";
  json += "\"wifi_bssid\":\"" + getCurrentBSSID() + "\",";
  json += "\"ip_address\":\"" + getCurrentIP() + "\",";
  json += "\"dhcp_enabled\":false,";
  json += "\"gateway\":\"" + WiFi.gatewayIP().toString() + "\",";
  json += "\"subnet\":\"" + WiFi.subnetMask().toString() + "\",";
  json += "\"rssi_dbm\":" + String((WiFi.status() == WL_CONNECTED) ? WiFi.RSSI() : 0) + ",";
  json += "\"sensor_interval_s\":" + String(SENSOR_READ_INTERVAL_MS / 1000) + ",";
  json += "\"bme_ok\":" + String(lastData.ok ? "true" : "false") + ",";
  json += "\"bme_detected\":" + String(bmeDetected ? "true" : "false") + ",";
  json += "\"bme_i2c_address\":\"";
  if (bmeDetected) {
    json += "0x";
    json += String(bmeAddress, HEX);
  } else {
    json += "NO_DETECTADO";
  }
  json += "\",";
  json += "\"millis\":" + String(lastData.millisTime) + ",";
  json += "\"temperature_c\":" + floatToString(lastData.temperature, 2) + ",";
  json += "\"humidity_percent\":" + floatToString(lastData.humidity, 2) + ",";
  json += "\"pressure_hpa\":" + floatToString(lastData.pressure, 2) + ",";
  json += "\"gas_resistance_ohms\":" + floatToString(lastData.gasResistance, 0);
  json += "}";

  httpd_resp_set_type(req, "application/json");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  return httpd_resp_send(req, json.c_str(), json.length());
}

static esp_err_t capture_handler(httpd_req_t *req) {
  camera_fb_t *fb = esp_camera_fb_get();

  if (!fb) {
    Serial.println("Error: no se pudo capturar foto");
    httpd_resp_send_500(req);
    return ESP_FAIL;
  }

  httpd_resp_set_type(req, "image/jpeg");
  httpd_resp_set_hdr(req, "Content-Disposition", "inline; filename=capture.jpg");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");

  esp_err_t res = httpd_resp_send(req, (const char *)fb->buf, fb->len);

  esp_camera_fb_return(fb);
  return res;
}

static esp_err_t stream_handler(httpd_req_t *req) {
  camera_fb_t *fb = NULL;
  esp_err_t res = ESP_OK;
  char part_buf[80];

  res = httpd_resp_set_type(req, STREAM_CONTENT_TYPE);
  if (res != ESP_OK) return res;

  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");

  while (true) {
    fb = esp_camera_fb_get();

    if (!fb) {
      Serial.println("Error: frame no capturado");
      res = ESP_FAIL;
      break;
    }

    size_t hlen = snprintf(part_buf, sizeof(part_buf), STREAM_PART, fb->len);

    res = httpd_resp_send_chunk(req, STREAM_BOUNDARY, strlen(STREAM_BOUNDARY));
    if (res == ESP_OK) {
      res = httpd_resp_send_chunk(req, part_buf, hlen);
    }
    if (res == ESP_OK) {
      res = httpd_resp_send_chunk(req, (const char *)fb->buf, fb->len);
    }

    esp_camera_fb_return(fb);

    if (res != ESP_OK) {
      Serial.println("Cliente desconectado del stream");
      break;
    }

    delay(STREAM_DELAY_MS);
  }

  return res;
}

void startCameraServer() {
  // Objetivo de esta version:
  // - Puerto 80: pagina principal + video en vivo para que cargue mejor en celular.
  // - Puerto 81: solo datos del sensor, para que el stream no bloquee el JSON.

  httpd_config_t video_config = HTTPD_DEFAULT_CONFIG();
  video_config.server_port = 80;
  video_config.ctrl_port = 32768;
  video_config.max_uri_handlers = 8;
  video_config.stack_size = 8192;
  video_config.max_open_sockets = 4;
  video_config.lru_purge_enable = true;

  httpd_uri_t index_uri = {};
  index_uri.uri = "/";
  index_uri.method = HTTP_GET;
  index_uri.handler = index_handler;
  index_uri.user_ctx = NULL;

  httpd_uri_t stream_uri = {};
  stream_uri.uri = "/stream";
  stream_uri.method = HTTP_GET;
  stream_uri.handler = stream_handler;
  stream_uri.user_ctx = NULL;

  httpd_uri_t capture_uri = {};
  capture_uri.uri = "/capture";
  capture_uri.method = HTTP_GET;
  capture_uri.handler = capture_handler;
  capture_uri.user_ctx = NULL;

  if (httpd_start(&video_httpd, &video_config) == ESP_OK) {
    httpd_register_uri_handler(video_httpd, &index_uri);
    httpd_register_uri_handler(video_httpd, &stream_uri);
    httpd_register_uri_handler(video_httpd, &capture_uri);
    Serial.println("Servidor de pagina/video iniciado en puerto 80");
  } else {
    Serial.println("Error iniciando servidor de pagina/video");
  }

  httpd_config_t sensor_config = HTTPD_DEFAULT_CONFIG();
  sensor_config.server_port = 81;
  sensor_config.ctrl_port = 32769;
  sensor_config.max_uri_handlers = 4;
  sensor_config.stack_size = 6144;
  sensor_config.max_open_sockets = 4;
  sensor_config.lru_purge_enable = true;

  httpd_uri_t sensor_uri = {};
  sensor_uri.uri = "/sensor";
  sensor_uri.method = HTTP_GET;
  sensor_uri.handler = sensor_handler;
  sensor_uri.user_ctx = NULL;

  if (httpd_start(&sensor_httpd, &sensor_config) == ESP_OK) {
    httpd_register_uri_handler(sensor_httpd, &sensor_uri);
    Serial.println("Servidor de sensor iniciado en puerto 81");
  } else {
    Serial.println("Error iniciando servidor de sensor");
  }
}

// =====================================================
// SETUP Y LOOP
// =====================================================

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println();
  Serial.println("Iniciando XIAO ESP32S3 Sense CAM + BME688...");
  Serial.print("Equipo: ");
  Serial.println(DEVICE_ID);

  bool cameraOk = startCamera();

  // Aunque la camara falle, intentamos levantar WiFi y sensor para diagnostico.
  startBME688();

  // Primera lectura antes de abrir la pagina.
  lastData = readBME688();
  printSensorData(lastData);
  lastSensorReadMillis = millis();

  startWiFiFixed();

  startCameraServer();

  Serial.println();
  Serial.println("========== SISTEMA LISTO ==========");
  Serial.print("Camara: ");
  Serial.println(cameraOk ? "OK" : "ERROR");
  Serial.print("BME688: ");
  Serial.println(bmeDetected ? "DETECTADO" : "NO DETECTADO");
  Serial.print("URL principal: http://");
  Serial.println(getCurrentIP());
  Serial.print("JSON sensor: http://");
  Serial.print(getCurrentIP());
  Serial.println(":81/sensor");
  Serial.print("Stream camara: http://");
  Serial.print(getCurrentIP());
  Serial.println("/stream");
  Serial.println("===================================");
  Serial.println();
}

void loop() {
  updateSensorIfNeeded();

  // El servidor esp_http_server trabaja en su propia tarea.
  // No usamos server.handleClient().
  delay(50);
}
