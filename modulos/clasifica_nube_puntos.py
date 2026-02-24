import os
import re
from pathlib import Path
import laspy
import rasterio
import numpy as np
from datetime import datetime

inicioscript = datetime.now()

# Información de entrada
lidar_entrada = 'entradas/lidar/220603_alcontar_lidar_CAAL_ppk.las'
# raster_clasificado = 'salidas/rasters_clasificados/veg_verde_seca/20241214-1507_NDVI_reclasificado.tif'
ruta_clasificados = 'salidas/rasters_clasificados'
# lidar_salida = 'salidas/lidar_clasificadas/alcontar_clasificada_NDVI.las'


def reclasifica_lidar(lidar_entrada, raster_entrada, nombre_indice, lidar_clasificado=None):
    try:
        # Comprobación de existencia de archivos
        if not os.path.exists(lidar_entrada):
            raise FileNotFoundError(f"Archivo LiDAR no encontrado: {lidar_entrada}")
        if not os.path.exists(raster_entrada):
            raise FileNotFoundError(f"Archivo raster no encontrado: {raster_entrada}")

        print(f'Leyendo la nube de puntos ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})')
        try:
          las = laspy.read(lidar_entrada)
        except laspy.LaspyException as e:
          raise RuntimeError(f"Error al leer el archivo LAS: {e}")

        print(f'Leyendo el raster ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})')
        try:
            with rasterio.open(raster_entrada) as src:
                transform = src.transform
                raster_data = src.read(1)
        except rasterio.RasterioIOError as e:
            raise RuntimeError(f"Error al leer el archivo raster: {e}")

        new_classification = np.zeros(len(las.points), dtype=np.uint8)

        print(f'Iterando sobre cada punto del LiDAR ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})')
        for i in range(len(las.points)):
            x, y = las.x[i], las.y[i]
            col, row = ~transform * (x, y)

            # Comprobación de límites más robusta con tipos enteros
            row_int = int(row)
            col_int = int(col)
            if 0 <= row_int < raster_data.shape[0] and 0 <= col_int < raster_data.shape[1]:
                new_classification[i] = raster_data[row_int, col_int]
            else:
                new_classification[i] = 0

        print(f'Asignando nueva clasifificación a la nube de puntos ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})')
        las.points.classification = new_classification

        nombre_lidar_clasificado = nombre_indice + '_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.las'

        if lidar_clasificado is None:
            # lidar_clasificado = lidar_entrada.replace('.las', f'_{nombre_indice}.las')
            lidar_clasificado = os.path.join('../salidas/lidar_clasificadas', nombre_lidar_clasificado)

        # Comprobación de la ruta de salida
        os.makedirs(os.path.dirname(lidar_clasificado), exist_ok=True)

        print(f'Guardando la nube de puntos ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})')
        las.write(lidar_clasificado)
        print(f"Archivo guardado correctamente en: {lidar_clasificado}")

    except FileNotFoundError as e:
        print(f"Error de archivo: {e}")
        return -1 # Devuelve un código de error
    except RuntimeError as e: # Captura errores de lectura de ficheros
        print(f"Error en tiempo de ejecución: {e}")
        return -1
    except Exception as e: # Captura cualquier otro error inesperado
        print(f"Error inesperado: {e}")
        return -1
    return 0 # Devuelve 0 si la función se ejecuta correctamente


if __name__ == "__main__":
    print(f'Inicio del script ({inicioscript.strftime('%Y-%m-%d %H:%M:%S')})')

    for raster_clasificado in Path(ruta_clasificados).glob('*_reclasificado.tif'):
        # Me quedo con el nombre del índice (lo que hay entre los dos _ en el nombre del raster reclasificado)
        nombre_indice = raster_clasificado.stem.split('_')[1]
        codigo_retorno = reclasifica_lidar(lidar_entrada, raster_clasificado, nombre_indice)
        if codigo_retorno == 0:
            print("Script ejecutado sin errores.")
        else:
            print("El script finalizó con errores.")

    print('Ejecución del script terminada en:', datetime.now() - inicioscript)
