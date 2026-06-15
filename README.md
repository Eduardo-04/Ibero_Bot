# BotIbero (Huerto Urbano)

Bot de Telegram para monitoreo del Huerto Urbano. Basado en la arquitectura de `botviejo` (telegram-air-quality-bot-template).

## Características
- Consulta de Temperatura, Humedad Ambiental, Humedad del Suelo y Luz.
- Gráficas históricas.
- Exportación CSV.
- Clasificación de estado (Óptimo, Crítico, etc.).

## Instalación
Sigue las mismas instrucciones de configuración de entorno y YAML que en el template original.
```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python src/tg_bot.py
```
