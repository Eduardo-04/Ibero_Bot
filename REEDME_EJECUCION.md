# Ibero Bot - Manual de Ejecución

Este documento explica los pasos necesarios para instalar y ejecutar el bot.

## 1. Requisitos previos
- Python 3 instalado en tu sistema.
- Un token de Telegram para tu bot (se obtiene desde BotFather en Telegram).

## 2. Entorno virtual

Se recomienda usar un entorno virtual para instalar las dependencias y aislar el proyecto. Ya se ha creado uno llamado `venv` en la raíz del proyecto.

Para activar el entorno virtual:

- **En Linux/MacOS**:
  ```bash
  source venv/bin/activate
  ```
- **En Windows**:
  ```bash
  venv\Scripts\activate
  ```

## 3. Instalación de dependencias

Una vez que el entorno virtual esté activado, instala las dependencias usando el archivo `requirements.txt`:

```bash
pip install -r requirements.txt
```

## 4. Configuración (.env)

El proyecto requiere variables de entorno para funcionar. Debes crear un archivo llamado `.env` en la raíz del proyecto. Puedes basarte en el archivo `.env.example`.

Ejemplo del archivo `.env`:

```env
TELEGRAM_TOKEN=tu_token_de_telegram_aqui
SMABILITY_BASE_URL=https://api.smability.com/v1
TZ=America/Mexico_City
```

Asegúrate de cambiar `tu_token_de_telegram_aqui` por el token real de tu bot.

## 5. Ejecución del Bot

Para arrancar el bot, asegúrate de estar en el entorno virtual activado y ejecuta:

```bash
cd src
python tg_bot.py
```

El bot debería mostrar el mensaje `Bot corriendo (polling). Ctrl+C para detener.` indicando que ya está funcionando y escuchando mensajes en Telegram.
