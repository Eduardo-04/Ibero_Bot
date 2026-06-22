import pandas as pd
from io import BytesIO

def clean_text(s: str) -> str:
    """
    Limpia un texto reemplazando caracteres especiales (como micro, cubo, grados, etc.)
    por sus equivalentes más estándar en ASCII.
    """
    if not s:
        return ""
    return (
        s.replace("µ", "u")
         .replace("³", "3")
         .replace("°", "")
         .replace("₂", "2")
         .replace("₃", "3")
         .replace("–", "-")
         .replace("—", "-")
    )

def clean_unit(u: str) -> str:
    """
    Limpia la unidad de medida y estandariza casos específicos como ug/m3 y C.
    """
    u = clean_text(u)
    # estandariza unos casos
    u = u.replace("ug/m3", "ug/m3")
    u = u.replace("C", "C")
    return u.strip()


def build_full_csv(sensor_data: dict, labels: dict, units: dict) -> bytes:
    """
    Construye un archivo CSV a partir de los datos de múltiples sensores.
    
    sensor_data: Diccionario con listas de datos por ID de sensor.
        {
            9: rows_pm25,
            8: rows_pm10,
            6: rows_no2,
            3: rows_rh,
            12: rows_temp
        }

    labels: Nombres de los sensores por ID.
        {9: "PM2.5", ...}

    units: Unidades de medida por ID.
        {9: "µg/m³", ...}
        
    Retorna los bytes del archivo CSV generado.
    """

    dfs = []

    # Itera sobre los datos de cada sensor
    for sid, rows in sensor_data.items():
        df = pd.DataFrame(rows)

        if df.empty:
            continue

        # Convierte los valores y las marcas de tiempo a los tipos adecuados
        df["Value"] = pd.to_numeric(df["Data"], errors="coerce")
        df["TimeStamp"] = pd.to_datetime(df["TimeStamp"], errors="coerce")

        # Elimina filas con valores o fechas nulas y selecciona solo esas dos columnas
        df = df.dropna(subset=["TimeStamp", "Value"])
        df = df[["TimeStamp", "Value"]]

        # Obtiene y limpia las etiquetas y unidades
        lab = clean_text(labels[sid])
        uni = clean_unit(units[sid])
        col_name = f"{lab} ({uni})" if uni else lab
        
        # Renombra la columna de valor para incluir la etiqueta y unidad
        df = df.rename(columns={"Value": col_name})

        dfs.append(df)

    # Si no hay DataFrames, devuelve un DataFrame vacío con la columna FechaHora
    if not dfs:
        final_df = pd.DataFrame(columns=["FechaHora"])
    else:
        # Une todos los DataFrames usando 'TimeStamp' como clave, con unión externa (outer join)
        final_df = dfs[0]
        for df in dfs[1:]:
            final_df = pd.merge(final_df, df, on="TimeStamp", how="outer")

        # Ordena cronológicamente
        final_df = final_df.sort_values("TimeStamp")

    # Renombra la columna TimeStamp a FechaHora
    final_df = final_df.rename(columns={"TimeStamp": "FechaHora"})

    # Guarda el DataFrame resultante en un buffer de memoria como CSV
    buf = BytesIO()
    final_df.to_csv(buf, index=False, encoding="utf-8-sig")
    return buf.getvalue()
