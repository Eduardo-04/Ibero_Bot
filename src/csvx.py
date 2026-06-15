import pandas as pd
from io import BytesIO

def clean_text(s: str) -> str:
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
    u = clean_text(u)
    # estandariza unos casos
    u = u.replace("ug/m3", "ug/m3")
    u = u.replace("C", "C")
    return u.strip()


def build_full_csv(sensor_data: dict, labels: dict, units: dict) -> bytes:
    """
    sensor_data:
        {
            9: rows_pm25,
            8: rows_pm10,
            6: rows_no2,
            3: rows_rh,
            12: rows_temp
        }

    labels:
        {9: "PM2.5", ...}

    units:
        {9: "µg/m³", ...}
    """

    dfs = []

    for sid, rows in sensor_data.items():
        df = pd.DataFrame(rows)

        if df.empty:
            continue

        df["Value"] = pd.to_numeric(df["Data"], errors="coerce")
        df["TimeStamp"] = pd.to_datetime(df["TimeStamp"], errors="coerce")

        df = df.dropna(subset=["TimeStamp", "Value"])
        df = df[["TimeStamp", "Value"]]

        lab = clean_text(labels[sid])
        uni = clean_unit(units[sid])
        col_name = f"{lab} ({uni})" if uni else lab
        df = df.rename(columns={"Value": col_name})

        dfs.append(df)

    if not dfs:
        final_df = pd.DataFrame(columns=["FechaHora"])
    else:
        final_df = dfs[0]
        for df in dfs[1:]:
            final_df = pd.merge(final_df, df, on="TimeStamp", how="outer")

        final_df = final_df.sort_values("TimeStamp")

    final_df = final_df.rename(columns={"TimeStamp": "FechaHora"})

    buf = BytesIO()
    final_df.to_csv(buf, index=False, encoding="utf-8-sig")
    return buf.getvalue()
