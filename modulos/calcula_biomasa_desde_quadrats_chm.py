import geopandas as gpd
import rasterio
from rasterio.mask import mask
import pandas as pd
import numpy as np


def calcula_volumen(vector, raster, fecha):
    # 1. Procesar con Rasterio
    with rasterio.open(raster) as src:
        # Comprobar y unificar proyecciones
        if vector.crs != src.crs:
            print(f"Reproyectando vector de {vector.crs} a {src.crs}...")
            vector = vector.to_crs(src.crs)

        # --- CÁLCULO DEL ÁREA DEL PÍXEL ---
        # Opción A: Automática (Recomendada por seguridad)
        res_x, res_y = src.res
        area_pixel = res_x * res_y  # Si es 5cm, esto será 0.0025

        # Opción B: Forzada (según tu petición explícita)
        # area_pixel = 0.05 * 0.05

        print(f"Resolución detectada: {res_x:.2f}m x {res_y:.2f}m")
        print(f"Área por píxel usada para el cálculo: {area_pixel} m²")

        lista_dfs = []

        # 2. Iterar sobre polígonos
        for idx, row in vector.iterrows():
            geom = [row['geometry']]
            id_val = row['ID_QUADRAT']

            try:
                # Recortar el ráster a la geometría
                out_image, out_transform = mask(src, geom, crop=True)
                data = out_image[0]  # Banda 1 (CHM)

                # Filtrar NoData
                no_data_val = src.nodata
                if no_data_val is not None:
                    pixeles_validos = data[data != no_data_val]
                else:
                    pixeles_validos = data.flatten()

                if pixeles_validos.size > 0:
                    # Crear DataFrame temporal
                    df_temp = pd.DataFrame({
                        'ID_QUADRAT': np.full(pixeles_validos.shape, id_val),
                        'altura_chm': pixeles_validos
                    })

                    # --- AQUÍ AÑADIMOS LA NUEVA COLUMNA ---
                    # Multiplicamos la altura por el área del píxel
                    df_temp['volumen_m3'] = df_temp['altura_chm'] * area_pixel

                    lista_dfs.append(df_temp)

            except ValueError:
                continue

    # 3. Concatenar y mostrar resultado
    if lista_dfs:
        df_final = pd.concat(lista_dfs, ignore_index=True)
        print("\nProceso finalizado. Primeras filas:")
        print(df_final.head())

        # Opcional: Guardar
        # df_final.to_csv("chm_volumen_por_pixel.csv", index=False)
    else:
        print("No se encontraron datos dentro de los polígonos.")

    # 4. Generar tabla resumen por quadrat
    # Agrupamos por ID y calculamos la suma del volumen y el promedio de la altura
    df_resumen = df_final.groupby('ID_QUADRAT').agg(
        volumen_total_m3=('volumen_m3', 'sum'),
        altura_media_m=('altura_chm', 'mean'),
        area_medida_m2=('volumen_m3', 'count')  # Cantidad de píxeles * (no es área directa, pero proporcional)
    ).reset_index()

    # Corregir el área medida multiplicando el conteo por el tamaño del pixel
    df_resumen['area_medida_m2'] = df_resumen['area_medida_m2'] * area_pixel

    print("\n--- Tabla Resumen po"
          "r Quadrat ---")
    print(df_resumen)

    # Opcional: Exportar a CSV
    df_resumen.to_csv(f"../salidas/dalias/{fecha}/biomasa/{fecha}_fitovolumen_dron.csv", index=False)

    return df_final, df_resumen

if __name__ == "__main__":
    fecha_muestreo = "250123"
    ruta_gpkg = "../entradas/infoVectorial.gpkg"
    capa = "daliasBiomasa"
    ruta_raster = "../salidas/dalias/250123/fitovolumen/chm_completo.tif"

    # Cargar la capa vectorial
    gdf = gpd.read_file(ruta_gpkg, layer=capa)

    calcula_volumen(gdf, ruta_raster, fecha_muestreo)