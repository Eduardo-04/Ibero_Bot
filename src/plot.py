from io import BytesIO
import pandas as pd
import matplotlib.pyplot as plt

def plot_png(rows: list[dict], title: str, unit: str = "") -> tuple[bytes, dict]:
    """
    Devuelve:
      - png bytes
      - stats dict con min/max/avg y timestamps
    """

    df = pd.DataFrame(rows)

    stats = {"min": None, "min_ts": None, "max": None, "max_ts": None, "avg": None}

    # ===== ESTILO CYBERPUNK =====
    bg_color = "#0B0F1A"        # fondo general
    panel_color = "#111827"     # fondo del eje
    grid_color = "#2A2F4A"      # grid tenue
    line_color = "#00F5FF"      # cian neón
    min_color = "#39FF14"       # verde neón
    max_color = "#FF007F"       # magenta neón
    text_color = "#E6E6FA"      # texto claro

    fig = plt.figure()
    ax = fig.add_subplot(111)

    # Fondo
    fig.patch.set_facecolor(bg_color)
    ax.set_facecolor(panel_color)

    # Grid retro
    ax.grid(True, color=grid_color, alpha=0.4, linestyle="--")

    # Color de textos
    ax.tick_params(colors=text_color)
    ax.xaxis.label.set_color(text_color)
    ax.yaxis.label.set_color(text_color)
    ax.title.set_color(text_color)

    if df.empty:
        ax.set_title(title)
        ax.text(0.5, 0.5, "Sin datos en este rango",
                ha="center", va="center", color=text_color)
    else:
        df["Data"] = pd.to_numeric(df["Data"], errors="coerce")
        df["TimeStamp"] = pd.to_datetime(df["TimeStamp"], errors="coerce")
        df = df.dropna(subset=["TimeStamp", "Data"]).sort_values("TimeStamp")

        if df.empty:
            ax.set_title(title)
            ax.text(0.5, 0.5, "Sin datos válidos",
                    ha="center", va="center", color=text_color)
        else:
            # Línea principal con efecto glow ligero (doble trazo)
            ax.plot(df["TimeStamp"], df["Data"],
                    linewidth=4.5, alpha=0.15, color=line_color)
            ax.plot(df["TimeStamp"], df["Data"],
                    linewidth=2.2, color=line_color)

            ax.set_title(title)
            ax.set_xlabel("Tiempo")
            ax.set_ylabel(f"Valor {unit}".strip())

            # Stats
            vmin = float(df["Data"].min())
            vmax = float(df["Data"].max())
            vavg = float(df["Data"].mean())

            imin = df["Data"].idxmin()
            imax = df["Data"].idxmax()

            tmin = df.loc[imin, "TimeStamp"]
            tmax = df.loc[imax, "TimeStamp"]

            stats["min"] = vmin
            stats["max"] = vmax
            stats["avg"] = vavg
            stats["min_ts"] = tmin.strftime("%Y-%m-%d %H:%M:%S")
            stats["max_ts"] = tmax.strftime("%Y-%m-%d %H:%M:%S")

            # Puntos neón
            ax.scatter([tmin], [vmin],
                       s=100, marker="o",
                       color=min_color,
                       edgecolors="white",
                       linewidths=0.6,
                       zorder=5)

            ax.scatter([tmax], [vmax],
                       s=100, marker="o",
                       color=max_color,
                       edgecolors="white",
                       linewidths=0.6,
                       zorder=5)

            # Etiquetas pequeñas
            ax.annotate("min", (tmin, vmin),
                        textcoords="offset points",
                        xytext=(6, -12),
                        color=min_color)

            ax.annotate("max", (tmax, vmax),
                        textcoords="offset points",
                        xytext=(6, 8),
                        color=max_color)

    fig.autofmt_xdate()

    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    return buf.getvalue(), stats
