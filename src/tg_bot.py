import os
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
from typing import Optional
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import MessageHandler, filters
from state import UIState
import menus
from datetime import datetime
from dateutil.relativedelta import relativedelta

from api import LocalESP32API
from cfg import Cfg
from norm import Norm
from dt import parse_range, fmt_api
from dev import DevCfg
from plot import plot_png
from csvx import build_full_csv



load_dotenv(BASE_DIR / ".env")

TG_TOKEN = os.getenv("TELEGRAM_TOKEN")
BASE_URL = os.getenv("SMABILITY_BASE_URL")
TZ_NAME = os.getenv("TZ", "America/Mexico_City")

def kb_main():
    """Retorna el teclado principal (InlineKeyboardMarkup) con las acciones principales del bot."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📍 Ahora", callback_data="act:now")],
        [InlineKeyboardButton("📈 Gráfica", callback_data="act:plot")],
        [InlineKeyboardButton("📥 CSV", callback_data="act:csv")],
        [InlineKeyboardButton("📡 Sensores", callback_data="act:sensors")],
    ])

def kb_sensors(cfg: Cfg, action: str):
    # action: now | plot | csv
    # mostramos solo sensores "útiles" (puedes ajustar)
    order = ["temp_ambiente", "hum_ambiente", "hum_suelo", "lux"]
    rows = []
    for sid in order:
        label = cfg.label(sid)
        rows.append([InlineKeyboardButton(label, callback_data=f"pick:{action}:{sid}")])
    rows.append([InlineKeyboardButton("⬅️ Menú", callback_data="act:menu")])
    return InlineKeyboardMarkup(rows)

def kb_ranges(action: str, sid: str):
    # rangos comunes
    opts = ["8h", "24h", "7d", "1m"]
    rows = []
    for r in opts:
        rows.append([InlineKeyboardButton(r, callback_data=f"run:{action}:{sid}:{r}")])
    rows.append([InlineKeyboardButton("⬅️ Sensores", callback_data=f"act:{action}")])
    rows.append([InlineKeyboardButton("⬅️ Menú", callback_data="act:menu")])
    return InlineKeyboardMarkup(rows)

def fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def avg_from_rows(rows: list[dict]) -> Optional[float]:
    vals = []
    for r in rows:
        try:
            data = r.get("Data")
            if data is not None:
                vals.append(float(data))
        except Exception:
            continue
    if not vals:
        return None
    return sum(vals) / len(vals)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador para el comando /start. Inicializa el estado del bot para el usuario e inicia la interacción."""
    if not update.effective_chat or not update.message: return
    # inicializa estado por chat si no existe
    chat_id = update.effective_chat.id
    st_map = context.application.bot_data.setdefault("state", {})
    st_map[chat_id] = UIState(device_key=None, sensor_id=None)

    welcome_msg = (
        "👋 ¡Hola! Soy BotIbero, tu asistente para el cuidado del huerto.\n\n"
        "Estoy aquí para ayudarte a monitorear la salud de tus plantas.\n"
        "Selecciona el área de cultivo que deseas revisar:"
    )
    await update.message.reply_text(
        welcome_msg,
        reply_markup=menus.kb_devices()
    )
    
async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador de mensajes de texto (interacción de los menús normales y botones)."""
    if not update.effective_chat or not update.message: return
    chat_id = update.effective_chat.id
    text = (update.message.text or "").strip()

    # estado por chat
    st_map = context.application.bot_data.setdefault("state", {})
    st = st_map.get(chat_id) or UIState()
    st_map[chat_id] = st

    cfg: Cfg = context.application.bot_data["cfg"]
    norm: Norm = context.application.bot_data["norm"]

    # 1) Selección de equipo
    if text == menus.BTN_DEVICE_1:
        st.device_key = "huerto_1"
        st.sensor_id = None
        await update.message.reply_text("Elige sensor:", reply_markup=menus.kb_sensors())
        return

    if text == menus.BTN_DEVICE_2:
        st.device_key = "huerto_2"
        st.sensor_id = None
        await update.message.reply_text("Elige sensor:", reply_markup=menus.kb_sensors())
        return

    # Home (regresa a equipos)
    if text == menus.BTN_HOME:
        st.device_key = None
        st.sensor_id = None
        await update.message.reply_text("Selecciona el área de cultivo:", reply_markup=menus.kb_devices())
        return

    # 2) Selección de sensor (solo si ya hay equipo)
    if st.device_key and text in {menus.BTN_TEMP, menus.BTN_HUM, menus.BTN_SUELO, menus.BTN_LUX}:
        st.sensor_id = {menus.BTN_TEMP: "temp_ambiente", menus.BTN_HUM: "hum_ambiente", menus.BTN_SUELO: "hum_suelo", menus.BTN_LUX: "lux"}[text]
        st.mode = None
        await update.message.reply_text("Elige acción:", reply_markup=menus.kb_actions())
        return

    # 3) Acción: Ahora (solo si ya hay equipo y sensor)
    if text == menus.BTN_NOW:
        if not st.device_key:
            await update.message.reply_text("Primero elige el área de cultivo.", reply_markup=menus.kb_devices())
            return
        if not st.sensor_id:
            await update.message.reply_text("Primero elige el sensor.", reply_markup=menus.kb_sensors())
            return

        dev: DevCfg = context.application.bot_data["dev"]
        dev_label = dev.label(st.device_key)
        ip_addr = dev.ip(st.device_key)

        api = LocalESP32API(ip_addr)
        cfg: Cfg = context.application.bot_data["cfg"]
        norm: Norm = context.application.bot_data["norm"]

        label = cfg.label(st.sensor_id)
        unit = cfg.unit(st.sensor_id)
        alias = cfg.alias(st.sensor_id)

        # 1) Último valor (últimos 10 minutos)
        last = api.get_current_data(st.sensor_id)

        if not last:
            await update.message.reply_text(f"[{dev_label}] {label}: sin datos recientes.", reply_markup=menus.kb_actions())
            return

        raw_last = last.get("Data")
        ts_last = last.get("TimeStamp")

        # 2) Promedio normativo
        rng_norm = "1h"
        unit_in_for_norm = None

        start_norm, end_norm = parse_range(rng_norm, TZ_NAME)
        rows_norm = api.get_history_data(st.sensor_id, fmt_api(start_norm), fmt_api(end_norm))

        # promedio simple
        vals = []
        for r in rows_norm:
            try:
                data = r.get("Data")
                if data is not None:
                    vals.append(float(data))
            except Exception:
                continue
        avg_norm = (sum(vals) / len(vals)) if vals else None

        sem = norm.check(alias, avg_norm, unit_in=unit_in_for_norm)

        # 3) Mensaje
        lines = []
        lines.append(f"[{dev_label}] {sem.emoji} {label}")
        lines.append(f"Último: {raw_last} {unit}".strip())
        lines.append(f"Hora último: {ts_last}")

        if avg_norm is None:
            lines.append("Promedio 1h: sin datos")
        else:
            lines.append(f"Promedio 1h: {avg_norm:.2f} {unit}".strip())

        lines.append(f"Estado del Huerto: {sem.name}")

        await update.message.reply_text("\n".join(lines), reply_markup=menus.kb_actions())
        return

    
    # 4) Grafica
    if text == menus.BTN_PLOT:
        await update.message.reply_text("⚠️ El código actual en el ESP32 no guarda historial, por lo que las gráficas no están disponibles en este momento.", reply_markup=menus.kb_actions())
        return
    
    # 5) Rangos de graficas
    if text in menus.RANGES:
        if st.mode != "plot":
            await update.message.reply_text("Elige una acción primero.", reply_markup=menus.kb_actions())
            return
        if not st.device_key or not st.sensor_id:
            await update.message.reply_text("Falta equipo o sensor.", reply_markup=menus.kb_devices())
            return

        rng = menus.RANGE_MAP[text]

        dev: DevCfg = context.application.bot_data["dev"]
        ip_addr = dev.ip(st.device_key)
        api = LocalESP32API(ip_addr)

        start_dt, end_dt = parse_range(rng, TZ_NAME)
        rows = api.get_history_data(st.sensor_id, fmt_api(start_dt), fmt_api(end_dt))
        
        # === Promedio normativo para semáforo ===
        alias = cfg.alias(st.sensor_id)

        win = relativedelta(hours=1)
        unit_in_for_norm = None
        label_avg = "Promedio 1h"

        end_norm = datetime.now()
        start_norm = end_norm - win

        rows_norm = api.get_history_data(st.sensor_id, fmt_api(start_norm), fmt_api(end_norm))
        avg_norm = avg_from_rows(rows_norm)

        sem = norm.check(alias, avg_norm, unit_in=unit_in_for_norm)

        label = cfg.label(st.sensor_id)
        unit = cfg.unit(st.sensor_id)
        dev_label = dev.label(st.device_key)

        title = f"[{dev_label}] {label} ({rng})"
        png, stats = plot_png(rows, title=title, unit=unit)
        await update.message.reply_photo(photo=png, caption=title, reply_markup=menus.kb_actions())

        # === Promedio normativo para estado actual ===
        alias = cfg.alias(st.sensor_id)

        win = relativedelta(hours=1)
        unit_in_for_norm = None
        label_avg = "Promedio 1h"

        end_norm = datetime.now()
        start_norm = end_norm - win

        rows_norm = api.get_history_data(st.sensor_id, fmt_api(start_norm), fmt_api(end_norm))

        # promedio simple (datos ~cada minuto)
        vals = []
        for r in rows_norm:
            try:
                data = r.get("Data")
                if data is not None:
                    vals.append(float(data))
            except Exception:
                continue
        avg_norm = (sum(vals) / len(vals)) if vals else None

        sem = norm.check(alias, avg_norm, unit_in=unit_in_for_norm)

        # Mensaje de resumen (min/max)
        if stats["min"] is not None:

            if avg_norm is None:
                avg_line = f"{label_avg}: sin datos"
            else:
                avg_line = f"{label_avg}: {avg_norm:.1f} {unit}"

            msg = (
                f"📌 Resumen ({rng})\n"
                f"Máximo: {stats['max']:.1f} {unit}  | {stats['max_ts']}\n"
                f"Mínimo: {stats['min']:.1f} {unit}  | {stats['min_ts']}\n"
                f"Promedio ({rng}): {stats['avg']:.1f} {unit}\n"
                f"{avg_line}\n"
                f"Estado: {sem.emoji} {sem.name}"
            )
        else:
            msg = "📌 Resumen: sin datos válidos en este rango."

        await update.message.reply_text(msg, reply_markup=menus.kb_actions())

        st.mode = None
        return

    # 6) CSV
    if text == menus.BTN_CSV_ALL:
        await update.message.reply_text("⚠️ El código actual en el ESP32 no guarda historial, por lo que las exportaciones CSV no están disponibles en este momento.", reply_markup=menus.kb_sensors())
        return



    # fallback: si el usuario escribe cualquier otra cosa
    await update.message.reply_text(
        "Usa los botones 🙂",
        reply_markup=menus.kb_devices() if not st.device_key else (menus.kb_sensors() if not st.sensor_id else menus.kb_actions())
    )

    
async def cmd_sensores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    cfg: Cfg = context.application.bot_data["cfg"]

    # cfg.sensors puede traer keys como int o str; normalizamos
    items = []
    for k, alias in cfg.sensors.items():
        sid = k
        items.append((sid, alias))

    items.sort(key=lambda x: x[0])

    lines = ["Sensores disponibles:"]
    for sid, alias in items:
        lines.append(f"- {sid}: {cfg.labels.get(alias, alias)}")

    lines.append("\nEjemplo: /ahora 9")
    await update.message.reply_text("\n".join(lines))


async def cmd_ahora(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    if not context.args:
        await update.message.reply_text("Uso: /ahora <idSensor>\nEjemplo: /ahora 9")
        return

    sid = context.args[0]

    dev: DevCfg = context.application.bot_data["dev"]
    ip_addr = dev.ip("huerto_1") # Default a huerto 1
    api = LocalESP32API(ip_addr)
    cfg: Cfg = context.application.bot_data["cfg"]
    norm: Norm = context.application.bot_data["norm"]

    last = api.get_current_data(sid)

    label = cfg.label(sid)
    unit = cfg.unit(sid)
    alias = cfg.alias(sid)

    if not last:
        await update.message.reply_text(f"{label}: sin datos en los últimos 10 minutos.")
        return

    raw = last.get("Data")
    ts = last.get("TimeStamp")

    try:
        val = float(raw)
    except Exception:
        val = None

    s = norm.check(alias, val)

    text = (
        f"{s.emoji} {label}\n"
        f"Valor: {raw} {unit}".strip() + "\n"
        f"Hora: {ts}\n"
        f"Estado: {s.msg}"
    )
    await update.message.reply_text(text)

async def on_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador de eventos en línea (callbacks), como la selección de botones interactivos debajo de los mensajes."""
    q = update.callback_query
    if not q: return
    await q.answer()

    cfg: Cfg = context.application.bot_data["cfg"]
    # Nota: la API ya no se inicializa globalmente ya que depende del dispositivo elegido.
    norm: Norm = context.application.bot_data["norm"]

    data = q.data or ""

    # acciones principales
    if data == "act:menu":
        await q.edit_message_text("Menú:", reply_markup=kb_main())
        return

    if data == "act:sensors":
        # lista simple
        items = []
        for k, alias in cfg.sensors.items():
            sid = k
            items.append((sid, alias))
        items.sort(key=lambda x: x[0])
        lines = ["Sensores disponibles:"]
        for sid, alias in items:
            lines.append(f"- {sid}: {cfg.labels.get(alias, alias)}")
        await q.edit_message_text("\n".join(lines), reply_markup=kb_main())
        return

    if data == "act:now":
        await q.edit_message_text("Elige sensor:", reply_markup=kb_sensors(cfg, "now"))
        return

    if data == "act:plot":
        await q.answer("⚠️ Gráficas no disponibles con la versión actual del ESP32.", show_alert=True)
        return

    if data == "act:csv":
        await q.answer("⚠️ CSV no disponible con la versión actual del ESP32.", show_alert=True)
        return

    # selección de sensor
    if data.startswith("pick:"):
        _, action, sid = data.split(":")
        if action == "now":
            # ejecuta "ahora" directo (10m)
            dev: DevCfg = context.application.bot_data["dev"]
            st_map = context.application.bot_data.setdefault("state", {})
            st = st_map.get(q.message.chat_id) or UIState()
            ip_addr = dev.ip(st.device_key) if st.device_key else "127.0.0.1"
            api = LocalESP32API(ip_addr)
            last = api.get_current_data(sid)

            label = cfg.label(sid)
            unit = cfg.unit(sid)
            alias = cfg.alias(sid)

            if not last:
                await q.edit_message_text(f"{label}: sin datos en los últimos 10 minutos.", reply_markup=kb_main())
                return

            raw = last.get("Data")
            ts = last.get("TimeStamp")
            try:
                val = float(raw)
            except Exception:
                val = None

            s = norm.check(alias, val)
            text = (
                f"{s.emoji} {label}\n"
                f"Valor: {raw} {unit}".strip() + "\n"
                f"Hora: {ts}\n"
                f"Estado: {s.msg}"
            )
            await q.edit_message_text(text, reply_markup=kb_main())
            return

        # plot/csv requieren rango
        if action in ("plot", "csv"):
            await q.answer("⚠️ Función no disponible con la versión actual del ESP32.", show_alert=True)
            return
            
        await q.edit_message_text("Elige rango:", reply_markup=kb_ranges(action, sid))
        return

    # ejecución con rango
    if data.startswith("run:"):
        _, action, sid, rng = data.split(":")
        
        if action in ("plot", "csv"):
            await q.answer("⚠️ Función no disponible con la versión actual del ESP32.", show_alert=True)
            return

    # fallback
    await q.edit_message_text("Opción no reconocida.", reply_markup=kb_main())


def main():
    """Función principal que arranca el bot y define los manejadores (handlers)."""
    if not TG_TOKEN or TG_TOKEN == "TO_BE_DEFINED":
        raise RuntimeError("Falta TELEGRAM_TOKEN real en .env")

    app = Application.builder().token(TG_TOKEN).build()

    # objetos compartidos
    app.bot_data["cfg"] = Cfg("cfg/sensors.yaml")
    app.bot_data["norm"] = Norm("cfg/norms.yaml")
    app.bot_data["dev"] = DevCfg("cfg/devices.yaml")

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("sensores", cmd_sensores))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))


    print("Bot corriendo (polling). Ctrl+C para detener.")
    app.run_polling()


if __name__ == "__main__":
    main()
