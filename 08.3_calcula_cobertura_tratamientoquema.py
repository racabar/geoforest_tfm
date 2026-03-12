import warnings
from pathlib import Path
import math

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask
from sklearn.metrics import mean_squared_error

# Ocultar advertencias menores de pandas/geopandas si es necesario
warnings.filterwarnings("ignore", category=UserWarning)


def calcular_superficie_vegetacion(ruta_tif, gdf_parcelas, id_columna="id_parcela", col_tratamiento="tratamiento"):
    """
    Calcula el área de vegetación (píxeles = 1) extrayendo además el grupo/tratamiento.
    """
    resultados = []
    ruta_tif = Path(ruta_tif)

    with rasterio.open(ruta_tif) as src:
        crs_raster = src.crs
        crs_vector = gdf_parcelas.crs

        if crs_raster != crs_vector:
            print(f"  [!] Reproyectando vector al vuelo para que coincida con {ruta_tif.name}...")
            gdf_parcelas = gdf_parcelas.to_crs(crs_raster)

        res_x, res_y = src.res
        area_pixel = res_x * res_y

        for _, row in gdf_parcelas.iterrows():
            geom = row["geometry"]
            id_parc = row[id_columna]

            # Extraer el valor del tratamiento (usando "Desconocido" como fallback si la celda está vacía)
            valor_tratamiento = row[col_tratamiento] if col_tratamiento in row else "Desconocido"

            try:
                out_image, out_transform = mask(src, [geom], crop=True)

                conteo_veg = np.sum(out_image == 1)
                conteo_no_veg = np.sum(out_image == 0)
                conteo_total = conteo_veg + conteo_no_veg

                cobertura_quadrat_valor_absoluto = conteo_veg * area_pixel

                if conteo_total > 0:
                    porcentaje_cobertura = (conteo_veg / conteo_total) * 100.0
                else:
                    porcentaje_cobertura = 0.0

                resultados.append({
                    id_columna: id_parc,
                    "Tratamiento": valor_tratamiento,
                    "Porcentaje_Calculado_%": porcentaje_cobertura,
                    "cobertura_quadrat_valor_absoluto": cobertura_quadrat_valor_absoluto
                })
            except ValueError:
                resultados.append({
                    id_columna: id_parc,
                    "Tratamiento": valor_tratamiento,
                    "Porcentaje_Calculado_%": np.nan,
                    "cobertura_quadrat_valor_absoluto": np.nan
                })

    return pd.DataFrame(resultados)


def procesar_serie_temporal(dir_tif, dir_csv, ruta_gpkg, capa_gpkg=None, id_columna="id_parcela",
                            col_area_csv="area_vegetacion", col_trat="tratamiento"):
    """
    Procesa todas las fechas cruzando los datos e incluyendo la columna de tratamiento.
    """
    ruta_gpkg = Path(ruta_gpkg)
    dir_tif = Path(dir_tif)
    dir_csv = Path(dir_csv)

    print(f"Cargando capa vectorial desde: {ruta_gpkg.name}")

    if capa_gpkg:
        gdf_parcelas = gpd.read_file(ruta_gpkg, layer=capa_gpkg)
    else:
        gdf_parcelas = gpd.read_file(ruta_gpkg)

    if col_trat not in gdf_parcelas.columns:
        raise ValueError(f"La columna de tratamiento '{col_trat}' no existe en el GeoPackage.")

    archivos_tif = list(dir_tif.glob("*.tif"))
    if not archivos_tif:
        raise FileNotFoundError("No se encontraron archivos .tif.")

    lista_comparaciones = []

    for ruta_tif in archivos_tif:
        nombre_base = ruta_tif.stem
        fecha_str = nombre_base.split("_")[0]
        ruta_csv = dir_csv / f"{fecha_str}.csv"

        if not ruta_csv.exists():
            continue

        # Pasamos el nombre de la columna de tratamiento a la función extractora
        df_calculado = calcular_superficie_vegetacion(ruta_tif, gdf_parcelas, id_columna, col_tratamiento=col_trat)
        df_csv = pd.read_csv(ruta_csv)

        if id_columna not in df_csv.columns or col_area_csv not in df_csv.columns:
            continue

        df_comparacion = pd.merge(df_calculado, df_csv[[id_columna, col_area_csv]], on=id_columna, how="inner")
        df_comparacion = df_comparacion.rename(columns={col_area_csv: "Cobertura_CSV_%"})
        df_comparacion["Diferencia_%"] = df_comparacion["Porcentaje_Calculado_%"] - df_comparacion["Cobertura_CSV_%"]
        df_comparacion["Fecha_ID"] = nombre_base

        lista_comparaciones.append(df_comparacion)
        print(f"Procesado: {nombre_base} ({len(df_comparacion)} parcelas agrupadas por '{col_trat}')")

    if lista_comparaciones:
        return pd.concat(lista_comparaciones, ignore_index=True)
    else:
        return pd.DataFrame()


def visualizar_resultados_subplots(df_resultados, col_tratamiento, dir_salida="graficos_salida_tratamientos"):
    """
    Genera una figura por fecha con múltiples subplots, uno por cada tratamiento.
    """
    if df_resultados.empty:
        print("No hay datos para visualizar.")
        return

    dir_salida = Path(dir_salida)
    dir_salida.mkdir(parents=True, exist_ok=True)

    # Límite global para que TODOS los subplots de todas las fechas tengan la misma escala
    max_global = max(df_resultados["Cobertura_CSV_%"].max(), df_resultados["Porcentaje_Calculado_%"].max())
    limite_eje = max(100.0, max_global * 1.05)

    fechas = df_resultados["Fecha_ID"].unique()
    print("\nGenerando gráficos multipanel por fecha...")

    for fecha in fechas:
        df_fecha = df_resultados[df_resultados["Fecha_ID"] == fecha]

        # Identificar los tratamientos únicos que hay en esta fecha concreta
        tratamientos = sorted(df_fecha["Tratamiento"].dropna().unique())
        n_plots = len(tratamientos)

        if n_plots == 0:
            continue

        # Calcular la cuadrícula (grid) óptima. Máximo 3 columnas de ancho.
        n_cols = min(n_plots, 3)
        n_rows = math.ceil(n_plots / n_cols)

        # Crear la figura matriz (squeeze=False asegura que 'axes' siempre sea una matriz 2D para iterar)
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(6 * n_cols, 6 * n_rows), squeeze=False)
        axes = axes.flatten()  # Aplanamos a 1D para iterar fácilmente con un bucle simple

        # Título principal de la figura
        fig.suptitle(f"Comparación Cobertura Vegetal - Fecha: {fecha}", fontsize=18, y=1.02)

        for i, trat in enumerate(tratamientos):
            ax = axes[i]
            df_trat = df_fecha[df_fecha["Tratamiento"] == trat]

            y_true = df_trat["Cobertura_CSV_%"]
            y_pred = df_trat["Porcentaje_Calculado_%"]

            if len(df_trat) > 1:
                matriz_corr = np.corrcoef(y_true, y_pred)
                r2 = matriz_corr[0, 1] ** 2 if not np.isnan(matriz_corr[0, 1]) else np.nan
                rmse = np.sqrt(mean_squared_error(y_true, y_pred))
                m, b = np.polyfit(y_true, y_pred, 1)
            else:
                r2, rmse, m, b = np.nan, np.nan, np.nan, np.nan

            # Gráfico de dispersión
            ax.scatter(y_true, y_pred, alpha=0.7, c="forestgreen", edgecolors="white", s=60)

            # Líneas
            ax.plot([0, limite_eje], [0, limite_eje], "r--", label="1:1 (Ideal)", linewidth=1.5)
            if len(df_trat) > 1:
                x_vals = np.array([0, limite_eje])
                y_vals = m * x_vals + b
                ax.plot(x_vals, y_vals, "b-", label=f"Tendencia ($y={m:.2f}x{b:+.2f}$)", linewidth=1.5)

            # Configuración de los ejes
            ax.set_xlim(0, limite_eje)
            ax.set_ylim(0, limite_eje)
            ax.set_aspect("equal", adjustable="box")

            # Textos
            texto_metricas = f"$R^2$: {r2:.3f}\nRMSE: {rmse:.2f} %"
            props = dict(boxstyle="round,pad=0.5", facecolor="white", alpha=0.9, edgecolor="lightgray")
            ax.text(0.05, 0.95, texto_metricas, transform=ax.transAxes, fontsize=11,
                    verticalalignment="top", bbox=props)

            # Etiqueta de cantidad de muestras
            ax.text(0.95, 0.05, f"n={len(df_trat)}", transform=ax.transAxes, fontsize=10,
                    verticalalignment="bottom", horizontalalignment="right")

            ax.set_title(f"Tratamiento: {trat}", fontsize=14, fontweight='bold', pad=10)
            ax.set_xlabel("Cobertura Campo (CSV) [%]", fontsize=10)
            ax.set_ylabel("Cobertura Ráster [%]", fontsize=10)
            ax.grid(True, linestyle="--", alpha=0.5)
            ax.legend(loc="lower right", fontsize=9)

        # Ocultar los subplots vacíos (si por ejemplo tenemos 5 tratamientos en una rejilla de 2x3=6 huecos)
        for j in range(len(tratamientos), len(axes)):
            fig.delaxes(axes[j])

        plt.tight_layout()
        ruta_grafico = dir_salida / f"grafico_paneles_{fecha}.png"
        plt.savefig(ruta_grafico, dpi=300, bbox_inches="tight")
        plt.close(fig)
        print(f"  -> Guardado: {ruta_grafico.name}")


if __name__ == "__main__":
    # RUTAS
    ruta_clasificaciones = Path("salidas/segmentaciones/20260312_otsu_ndvi_tvi2/mascaras_vegetacion")
    ruta_datos_campo = Path("entradas/cobertura_campo")
    ruta_parcelas = Path("entradas/infoVectorial.gpkg")
    ruta_graficos = Path("salidas/segmentaciones/20260312_otsu_ndvi_tvi2/graficos_cobertura/tratamiento_quema")

    # PARÁMETROS
    capa_quadrats = "daliasQuadrats_32630"
    id_quadrat = "ID_QUADRAT"
    columna_cobertura_campo = "REC_VEG_VERDE"

    # --- NUEVO PARÁMETRO ---
    COLUMNA_TRATAMIENTO = "tratamientoquema"  # Nombre de la columna en el GeoPackage

    try:
        df_resumen = procesar_serie_temporal(
            dir_tif=ruta_clasificaciones,
            dir_csv=ruta_datos_campo,
            ruta_gpkg=ruta_parcelas,
            capa_gpkg=capa_quadrats,
            id_columna=id_quadrat,
            col_area_csv=columna_cobertura_campo,
            col_trat=COLUMNA_TRATAMIENTO
        )

        if not df_resumen.empty:
            # Exportar el reporte general ahora con la columna 'Tratamiento' incluida
            ruta_salida_csv = ruta_graficos / "reporte_validacion_por_tratamiento.csv"
            ruta_graficos.mkdir(parents=True, exist_ok=True)
            df_resumen.to_csv(ruta_salida_csv, index=False)

            print(f"\n[OK] Reporte general guardado en: {ruta_salida_csv}")

            # Generar los gráficos de subpaneles
            visualizar_resultados_subplots(
                df_resultados=df_resumen,
                col_tratamiento=COLUMNA_TRATAMIENTO,
                dir_salida=ruta_graficos
            )

    except Exception as e:
        print(f"\n[ERROR CRÍTICO] Ocurrió un fallo en el procesamiento: {str(e)}")