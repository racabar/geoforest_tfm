import warnings
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask
from sklearn.metrics import mean_squared_error

# Ocultar advertencias menores de pandas/geopandas si es necesario
warnings.filterwarnings("ignore", category=UserWarning)


def calcular_superficie_vegetacion(ruta_tif, gdf_parcelas, id_columna="id_parcela"):
    """
    Calcula el área de vegetación (píxeles = 1) para cada parcela en una imagen TIF.
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
                    "Porcentaje_Calculado_%": porcentaje_cobertura,
                    "cobertura_quadrat_valor_absoluto": cobertura_quadrat_valor_absoluto
                })
            except ValueError:
                resultados.append({
                    id_columna: id_parc,
                    "Porcentaje_Calculado_%": np.nan,
                    "cobertura_quadrat_valor_absoluto": np.nan
                })

    return pd.DataFrame(resultados)


def procesar_serie_temporal(dir_tif, dir_csv, ruta_gpkg, capa_gpkg=None, id_columna="id_parcela",
                            col_area_csv="area_vegetacion"):
    """
    Procesa todas las fechas, cruza con los CSV y devuelve un DataFrame unificado.
    """
    ruta_gpkg = Path(ruta_gpkg)
    dir_tif = Path(dir_tif)
    dir_csv = Path(dir_csv)

    print(f"Cargando capa vectorial desde: {ruta_gpkg.name}")

    if capa_gpkg:
        gdf_parcelas = gpd.read_file(ruta_gpkg, layer=capa_gpkg)
    else:
        gdf_parcelas = gpd.read_file(ruta_gpkg)

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

        df_calculado = calcular_superficie_vegetacion(ruta_tif, gdf_parcelas, id_columna)
        df_csv = pd.read_csv(ruta_csv)

        if id_columna not in df_csv.columns or col_area_csv not in df_csv.columns:
            continue

        df_comparacion = pd.merge(df_calculado, df_csv[[id_columna, col_area_csv]], on=id_columna, how="inner")
        df_comparacion = df_comparacion.rename(columns={col_area_csv: "Cobertura_CSV_%"})
        df_comparacion["Fecha_ID"] = nombre_base

        lista_comparaciones.append(df_comparacion)
        print(f"Procesado: {nombre_base} ({len(df_comparacion)} parcelas)")

    if lista_comparaciones:
        return pd.concat(lista_comparaciones, ignore_index=True)
    else:
        return pd.DataFrame()


def mostrar_grafico_global(df_resultados, dir_salida):
    """
    Genera y muestra por pantalla un único gráfico de dispersión con todos los datos.
    """
    if df_resultados.empty:
        print("No hay datos para visualizar.")
        return

    print("\nGenerando gráfico global...")

    y_true = df_resultados["Cobertura_CSV_%"]
    y_pred = df_resultados["Porcentaje_Calculado_%"]

    # Determinar el máximo global para encuadrar la figura
    max_global = max(y_true.max(), y_pred.max())
    limite_eje = max(100.0, max_global * 1.05)

    # Calcular métricas estadísticas para TODO el conjunto de datos
    if len(df_resultados) > 1:
        matriz_corr = np.corrcoef(y_true, y_pred)
        r2 = matriz_corr[0, 1] ** 2 if not np.isnan(matriz_corr[0, 1]) else np.nan
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        m, b = np.polyfit(y_true, y_pred, 1)
    else:
        r2, rmse, m, b = np.nan, np.nan, np.nan, np.nan

    # Configurar figura cuadrada
    fig, ax = plt.subplots(figsize=(8, 8))

    # Dibujar todos los puntos
    ax.scatter(y_true, y_pred, alpha=0.5, c="forestgreen", edgecolors="white", s=60)

    # Línea 1:1
    ax.plot([0, limite_eje], [0, limite_eje], "r--", label="Línea 1:1 (Ajuste Perfecto)", linewidth=1.5)

    # Línea de tendencia global
    if len(df_resultados) > 1:
        x_vals = np.array([0, limite_eje])
        y_vals = m * x_vals + b
        ax.plot(x_vals, y_vals, "b-", label=f"Tendencia global ($y={m:.2f}x{b:+.2f}$)", linewidth=1.5)

    # Forzar escala idéntica y proporción cuadrada
    ax.set_xlim(0, limite_eje)
    ax.set_ylim(0, limite_eje)
    ax.set_aspect("equal", adjustable="box")

    # Añadir caja de texto
    texto_metricas = f"$R^2$ global: {r2:.3f}\nRMSE global: {rmse:.2f} %"
    props = dict(boxstyle="round,pad=0.5", facecolor="white", alpha=0.9, edgecolor="lightgray")
    ax.text(0.05, 0.95, texto_metricas, transform=ax.transAxes, fontsize=12,
            verticalalignment="top", bbox=props)

    # Añadir cuántos puntos hay en total
    total_puntos = len(df_resultados)
    ax.text(0.95, 0.05, f"n = {total_puntos} observaciones", transform=ax.transAxes, fontsize=10,
            verticalalignment="bottom", horizontalalignment="right",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", alpha=0.8, edgecolor="gray"))

    ax.set_title("Comparación Global de Cobertura Vegetal (Todas las fechas)", fontsize=14, pad=15)
    ax.set_xlabel("Cobertura Vegetal en Campo (CSV) [%]", fontsize=12)
    ax.set_ylabel("Cobertura Vegetal (Calculada Ráster) [%]", fontsize=12)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(loc="lower right", bbox_to_anchor=(1, 0.1))

    plt.tight_layout()
    ruta_grafico = dir_salida / f"grafico_global.png"
    plt.savefig(ruta_grafico, dpi=300, bbox_inches="tight")
    # plt.show()
    plt.close(fig)


if __name__ == "__main__":
    # RUTAS (Mantenidas idénticas al entorno anterior)
    ruta_clasificaciones = Path("salidas/segmentaciones/20260312_otsu_ndvi_tvi2/mascaras_vegetacion")
    ruta_datos_campo = Path("entradas/cobertura_campo")
    ruta_parcelas = Path("entradas/infoVectorial.gpkg")
    ruta_graficos = Path("salidas/segmentaciones/20260312_otsu_ndvi_tvi2/graficos_cobertura")

    # Asegúrate de que estos nombres coincidan con tus datos
    capa_quadrats = "daliasQuadrats_32630"
    id_quadrat = "ID_QUADRAT"
    columna_cobertura_campo = "REC_VEG_VERDE"

    try:
        df_resumen = procesar_serie_temporal(
            dir_tif=ruta_clasificaciones,
            dir_csv=ruta_datos_campo,
            ruta_gpkg=ruta_parcelas,
            capa_gpkg=capa_quadrats,
            id_columna=id_quadrat,
            col_area_csv=columna_cobertura_campo
        )

        if not df_resumen.empty:
            # Mostrar el gráfico directamente sin guardar nada
            mostrar_grafico_global(df_resumen, ruta_graficos)

    except Exception as e:
        print(f"\n[ERROR CRÍTICO] Ocurrió un fallo en el procesamiento: {str(e)}")