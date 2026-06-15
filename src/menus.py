from telegram import ReplyKeyboardMarkup

# textos (para comparar exacto)
BTN_DEVICE_1 = "🌱 Invernadero"
BTN_DEVICE_2 = "🪴 Cama 1"
BTN_HOME = "🏠 Inicio"

BTN_TEMP = "🌡️ Temperatura"
BTN_HUM = "💧 Humedad"
BTN_SUELO = "🌱 Hum. Suelo"
BTN_LUX = "☀️ Luz"

BTN_NOW  = "📍 Ahora"
BTN_PLOT = "📈 Gráfica"
BTN_CSV_ALL = "📥 CSV (todos)"
BTN_BACK = "⬅️ Atrás"

def kb_devices():
    return ReplyKeyboardMarkup(
        [[BTN_DEVICE_1], [BTN_DEVICE_2]],
        resize_keyboard=True,
        one_time_keyboard=False
    )

def kb_sensors():
    return ReplyKeyboardMarkup(
        [
            [BTN_TEMP, BTN_HUM],
            [BTN_SUELO, BTN_LUX],
            [BTN_CSV_ALL],
            [BTN_HOME]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

def kb_actions():
    return ReplyKeyboardMarkup(
        [[BTN_NOW], [BTN_PLOT], [BTN_HOME]],
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
    return ReplyKeyboardMarkup(
        [
            [BTN_R_8H, BTN_R_24H],
            [BTN_R_7D, BTN_R_1M],
            [BTN_HOME],
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )