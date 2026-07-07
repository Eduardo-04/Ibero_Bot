from telegram import ReplyKeyboardMarkup

# textos (para comparar exacto)
BTN_DEVICE_1 = "🌱 Invernadero"
BTN_DEVICE_2 = "🪴 Cama 1"
BTN_HOME = "🏠 Inicio"

BTN_TEMP = "🌡️ Temperatura"
BTN_HUM = "💧 Humedad"
BTN_PRESION = "🌤️ Presión"
BTN_GAS = "💨 Gas"
BTN_CAMARA = "📷 Cámara"
BTN_HUM_SUELO = "🌱 Humedad Suelo"

BTN_NOW  = "📍 Ahora"
BTN_PLOT = "📈 Gráfica"
BTN_CSV_ALL = "📥 CSV (todos)"
BTN_BACK = "⬅️ Atrás"

def kb_devices():
    """Genera el teclado para seleccionar un área de cultivo (Invernadero o Cama)."""
    return ReplyKeyboardMarkup(
        [[BTN_DEVICE_1], [BTN_DEVICE_2]],
        resize_keyboard=True,
        one_time_keyboard=False
    )

def kb_sensors(device_key: str = None):
    """Genera el teclado para elegir el sensor a consultar."""
    row2 = [BTN_PRESION]
    row3 = [BTN_GAS]
    if device_key != "huerto_1":
        row2.insert(0, BTN_HUM_SUELO)
    if device_key != "huerto_2":
        row3.append(BTN_CAMARA)
        
    return ReplyKeyboardMarkup(
        [
            [BTN_TEMP, BTN_HUM],
            row2,
            row3,
            [BTN_CSV_ALL],
            [BTN_BACK, BTN_HOME]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

def kb_actions():
    """Genera el teclado con las acciones a realizar (Valor actual o Gráfica)."""
    return ReplyKeyboardMarkup(
        [[BTN_NOW], [BTN_PLOT], [BTN_BACK, BTN_HOME]],
        resize_keyboard=True,
        one_time_keyboard=False
    )

BTN_R_8H  = "8 horas"
BTN_R_24H  = "24 horas"
BTN_R_7D  = "7 dias"
BTN_R_1M  = "1 mes"


RANGES = {BTN_R_8H, BTN_R_24H, BTN_R_7D, BTN_R_1M}

RANGE_MAP = {
    BTN_R_8H: "8h",
    BTN_R_24H: "24h",
    BTN_R_7D: "7d",
    BTN_R_1M: "1m",
}

def kb_ranges():
    """Genera el teclado para elegir el rango de tiempo de una gráfica o acción."""
    return ReplyKeyboardMarkup(
        [
            [BTN_R_8H, BTN_R_24H],
            [BTN_R_7D, BTN_R_1M],
            [BTN_BACK, BTN_HOME],
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )