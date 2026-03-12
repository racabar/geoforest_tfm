import warnings
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask
from sklearn.metrics import r2_score, mean_squared_error

# Ocultar advertencias menores de pandas/geopandas si es necesario
warnings.filterwarnings("ignore", category=UserWarning)


def calcular_superficie_vegetacion(ruta_tif, gdf_parcelas, id_columna="id_parcela"):
    resultados = []
    ruta_tif = Path(ruta_tif)

    with rasterio.open(ruta_tif) as src:
        # ADVERTENCIA: Comprobación de CRS antes de operaciones espaciales
        crs_raster = src.crs
        crs_vector = gdf_parcelas.crs

        if crs_raster != crs_vector:
            print(f"  [!] ADVERTENCIA: Discrepancia de CRS detectada en {ruta_tif.name}.")
            print(f"      Ráster: {crs_raster} | Vector: {crs_vector}. Reproyectando vector al vuelo...")
            gdf_parcelas = gdf_parcelas.to_crs(crs_raster)

        # Calcular área de un píxel (en las unidades del CRS, usualmente m2)
        res_x, res_y = src.res
        area_pixel = res_x * res_y

        # Iterar sobre cada parcela
        for _, row in gdf_parcelas.iterrows():
            geom = row["geometry"]
            id_parc = row[id_columna]

            try:
                # Extraer los píxeles que caen dentro de la geometría de la parcela
                out_image, out_transform = mask(src, [geom], crop=True)

                # Conteo de píxeles para calcular el porcentaje
                conteo_veg = np.sum(out_image == 1)
                conteo_no_veg = np.sum(out_image == 0)
                conteo_total = conteo_veg + conteo_no_veg

                # Calcular área absoluta
                cobertura_quadrat_valor_absoluto = conteo_veg * area_pixel

                # Calcular porcentaje (evitar división por cero si la parcela es más pequeña que un píxel)
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
                # Ocurre si la parcela está fuera de los límites del ráster
                resultados.append({
                    id_columna: id_parc,
                    "Porcentaje_Calculado_%": np.nan,
                    "cobertura_quadrat_valor_absoluto": np.nan
                })

    return pd.DataFrame(resultados)


def procesar_serie_temporal(dir_tif, dir_csv, ruta_gpkg, capa_gpkg=None, id_columna="id_parcela",
                            col_area_csv="area_vegetacion"):
    ruta_gpkg = Path(ruta_gpkg)
    dir_tif = Path(dir_tif)
    dir_csv = Path(dir_csv)

    mensaje_capa = f" (Capa: {capa_gpkg})" if capa_gpkg else " (Capa por defecto)"
    print(f"Cargando capa vectorial desde: {ruta_gpkg}{mensaje_capa}")

    if capa_gpkg:
        gdf_parcelas = gpd.read_file(ruta_gpkg, layer=capa_gpkg)
    else:
        gdf_parcelas = gpd.read_file(ruta_gpkg)

    archivos_tif = list(dir_tif.glob("*.tif"))
    if not archivos_tif:
        raise FileNotFoundError("No se encontraron archivos .tif en el directorio especificado.")

    lista_comparaciones = []

    for ruta_tif in archivos_tif:
        nombre_base = ruta_tif.stem

        # Extraer la fecha del nombre del TIF (todo lo que va antes del primer '_')
        fecha_str = nombre_base.split("_")[0]

        # Buscar el CSV correspondiente usando solo la fecha extraída
        ruta_csv = dir_csv / f"{fecha_str}.csv"

        print(f"\nProcesando imagen: {nombre_base}")
        print(f"  -> Buscando datos de campo en: {ruta_csv.name}")

        if not ruta_csv.exists():
            print(f"  [!] No se encontró el CSV correspondiente: {ruta_csv}. Saltando validación para esta imagen.")
            continue

        # 1. Calcular área desde el TIF
        df_calculado = calcular_superficie_vegetacion(ruta_tif, gdf_parcelas, id_columna)

        # 2. Cargar datos del CSV
        df_csv = pd.read_csv(ruta_csv)

        # Validar que existan las columnas clave en el CSV
        if id_columna not in df_csv.columns or col_area_csv not in df_csv.columns:
            print(
                f"  [!] El CSV {nombre_base}.csv no contiene las columnas necesarias ('{id_columna}', '{col_area_csv}').")
            continue

        # 3. Cruzar datos (Inner join: ignora parcelas que no estén reportadas en el CSV para esta fecha)
        df_comparacion = pd.merge(df_calculado, df_csv[[id_columna, col_area_csv]], on=id_columna, how="inner")
        df_comparacion = df_comparacion.rename(columns={col_area_csv: "Cobertura_CSV_%"})

        # 4. Calcular métricas de error (ahora usando el porcentaje)
        df_comparacion["Diferencia_%"] = df_comparacion["Porcentaje_Calculado_%"] - df_comparacion["Cobertura_CSV_%"]

        # El error relativo ahora mide la desviación respecto al porcentaje real
        df_comparacion["Error_Relativo_%"] = np.where(
            df_comparacion["Cobertura_CSV_%"] > 0,
            (df_comparacion["Diferencia_%"] / df_comparacion["Cobertura_CSV_%"]) * 100,
            0
        )
        df_comparacion["Fecha_ID"] = nombre_base

        lista_comparaciones.append(df_comparacion)
        print(f"  -> {len(df_comparacion)} parcelas comparadas exitosamente.")

    # Consolidar todos los resultados en un único DataFrame
    if lista_comparaciones:
        df_final = pd.concat(lista_comparaciones, ignore_index=True)
        return df_final
    else:
        return pd.DataFrame()


def visualizar_resultados(df_resultados, dir_salida="graficos_salida"):
    if df_resultados.empty:
        print("No hay datos para visualizar.")
        return

    # Crear directorio de salida si no existe usando pathlib
    dir_salida = Path(dir_salida)
    dir_salida.mkdir(parents=True, exist_ok=True)

    # Determinar el máximo global para unificar la escala de todos los gráficos (suele ser 100 para porcentajes)
    max_global = max(df_resultados["Cobertura_CSV_%"].max(), df_resultados["Porcentaje_Calculado_%"].max())
    limite_eje = max(100.0, max_global * 1.05)  # Fijamos un mínimo visual de 100 para la gráfica de porcentajes

    fechas = df_resultados["Fecha_ID"].unique()
    print("\nGenerando gráficos individuales por fecha...")

    for fecha in fechas:
        df_fecha = df_resultados[df_resultados["Fecha_ID"] == fecha]

        # Calcular métricas estadísticas
        y_true = df_fecha["Cobertura_CSV_%"]
        y_pred = df_fecha["Porcentaje_Calculado_%"]

        # Control por si alguna fecha tiene menos de 2 parcelas (evita error en R2)
        if len(df_fecha) > 1:
            # Calcular R2 típico (Cuadrado del coeficiente de correlación de Pearson)
            matriz_corr = np.corrcoef(y_true, y_pred)
            # Evitar error si todos los valores son constantes (varianza cero)
            r2 = matriz_corr[0, 1] ** 2 if not np.isnan(matriz_corr[0, 1]) else np.nan

            rmse = np.sqrt(mean_squared_error(y_true, y_pred))

            # Calcular regresión lineal (m: pendiente, b: ordenada al origen)
            m, b = np.polyfit(y_true, y_pred, 1)
        else:
            r2 = np.nan
            rmse = np.nan
            m, b = np.nan, np.nan

        # Configurar figura cuadrada
        fig, ax = plt.subplots(figsize=(8, 8))

        ax.scatter(y_true, y_pred, alpha=0.7, c="forestgreen", edgecolors="white", s=60)

        # Línea 1:1
        ax.plot([0, limite_eje], [0, limite_eje], "r--", label="Línea 1:1 (Ajuste Perfecto)", linewidth=1.5)

        # Línea de tendencia (Regresión Lineal)
        if len(df_fecha) > 1:
            x_vals = np.array([0, limite_eje])
            y_vals = m * x_vals + b
            ax.plot(x_vals, y_vals, "b-", label=f"Tendencia lineal ($y={m:.2f}x{b:+.2f}$)", linewidth=1.5)

        # Forzar escala idéntica y proporción estrictamente cuadrada
        ax.set_xlim(0, limite_eje)
        ax.set_ylim(0, limite_eje)
        ax.set_aspect("equal", adjustable="box")

        # Añadir caja de texto con R2 y RMSE (Unidad del RMSE es ahora %)
        texto_metricas = f"$R^2$: {r2:.3f}\nRMSE: {rmse:.2f} %"
        props = dict(boxstyle="round,pad=0.5", facecolor="white", alpha=0.9, edgecolor="lightgray")
        ax.text(0.05, 0.95, texto_metricas, transform=ax.transAxes, fontsize=12,
                verticalalignment="top", bbox=props)

        ax.set_title(f"Comparación Cobertura Vegetal - Fecha: {fecha}", fontsize=14, pad=15)
        ax.set_xlabel("Cobertura Vegetal en Campo (CSV) [%]", fontsize=12)
        ax.set_ylabel("Cobertura Vegetal (Calculada Ráster) [%]", fontsize=12)
        ax.grid(True, linestyle="--", alpha=0.5)
        ax.legend(loc="lower right")

        plt.tight_layout()
        ruta_grafico = dir_salida / f"grafico_{fecha}.png"
        plt.savefig(ruta_grafico, dpi=300, bbox_inches="tight")
        # plt.show()
        plt.close(fig)  # Liberar memoria cerrando la figura
        print(f"  -> Guardado: {ruta_grafico}")


if __name__ == "__main__":
    ruta_clasificaciones = Path("salidas/segmentaciones/20260312_otsu_ndvi_tvi2/mascaras_vegetacion")
    ruta_datos_campo = Path("entradas/cobertura_campo")
    ruta_parcelas = Path("entradas/infoVectorial.gpkg")
    ruta_graficos = Path("salidas/segmentaciones/20260312_otsu_ndvi_tvi2/graficos_cobertura")

    # Asegúrate de que estos nombres coincidan con tus datos
    capa_quadrats = "daliasQuadrats_32630"  # Reemplaza con el nombre exacto de la capa, o pon None para la primera
    id_quadrat = "ID_QUADRAT"  # Nombre de la columna ID en el GPKG y en los CSVs
    columna_cobertura_campo = "REC_VEG_VERDE"  # Nombre de la columna de área en los CSVs

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
            # Exportar el reporte general
            ruta_salida = "reporte_validacion_vegetacion.csv"
            df_resumen.to_csv(ruta_salida, index=False)
            print(f"\n[OK] Proceso completado. Reporte general guardado en: {ruta_salida}")
            print(f"Resumen Estadístico del Error General:\n{df_resumen['Diferencia_%'].describe()}")

            # Generar gráficos estáticos por fecha
            visualizar_resultados(df_resumen, dir_salida=ruta_graficos)

    except Exception as e:
        print(f"\n[ERROR CRÍTICO] Ocurrió un fallo en el procesamiento: {str(e)}")
