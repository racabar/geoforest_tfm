# https://colab.research.google.com/drive/1JQpcVFFJYMrJCfodqP4Nc_B0_w6p5WOV?usp=sharing#scrollTo=--iMgC8OKmmU
# https://www.simonplanzer.com/articles/lidar-chm/

from datetime import datetime
import math
import numpy as np
import json
import laspy  # Para el cálculo de la distancia mínima media entre puntos
import pdal
from osgeo import gdal
import concurrent.futures  # Para ejecutar las dos funciones en paralelo
from scipy.spatial import KDTree

gdal.UseExceptions()  # Para evitar el error FutureWarning: Neither gdal.UseExceptions()...

inicioscript = datetime.now()


def distancia_minima_media(puntos):
    '''
    Teorema de Nyquist-Shannon para el tamaño de pixel: este teorema, aplicado al muestreo espacial, sugiere que
    para representar adecuadamente una señal, la resolución del ráster debería ser al menos la mitad de la distancia
    entre los puntos de muestreo.
    '''
    # Crear un KDTree para la búsqueda eficiente de vecinos más cercanos
    tree = KDTree(puntos)

    # Obtener las distancias al vecino más cercano para cada punto
    distancias, _ = tree.query(puntos, k=2)  # k=2 porque el primer vecino es el punto en sí mismo
    distancias_minimas = distancias[:, 1]  # Ignorar la distancia al propio punto

    # Calcular la distancia mínima media
    distancia_minima_media = np.mean(distancias_minimas)

    return distancia_minima_media

def calcula_mds(lidar, mds, resolucion_raster, radio_raster):
    # Obtengo las dimensiones de la nube de puntos para usar en writers.gdal
    # x_min, y_min, altura_pixeles, anchura_pixeles = datos_lidar(archivo_lidar)

    # Crear un pipeline PDAL para generar el DSM
    # writers.gdal: https://pdal.io/en/2.4.3/stages/writers.gdal.html
    pipeline_json = {
        "pipeline": [
            {
                "type":"readers.las",
                "filename":lidar
            },
            {
                "type":"filters.reprojection",
                "in_srs":"EPSG:32630",
                "out_srs":"EPSG:32630"
            },
            {
                "type":"filters.range",
                "limits":"Classification[2:3]"
            },
            {   "type":"writers.gdal",
                "filename":mds,
                "output_type":"max", # Busco el valor máximo para cada pixel
                "gdaldriver":"GTiff",
                "resolution":resolucion_raster,
                "radius":radio_raster,
                "data_type":"float32",
                "nodata":-99999
            }
        ]
    }

    print('Calculando el MDS...', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    # Ejecutar el pipeline
    pipeline = pdal.Pipeline(json.dumps(pipeline_json))
    pipeline.execute()

    # raster_dataset = rasterio.open(mds_calculado)
    # estadisticas_raster = raster_dataset.stats()

    print(f'MDS creado con éxito en {mds}\n', '  Duración:', datetime.now()-inicioscript)


def calcula_mdt(lidar, mdt, resolucion_raster, radio_raster, ventana):
    # Crear un pipeline PDAL para generar el DTM
    # filters.elm https://pdal.io/en/stable/stages/filters.elm.html
    # filters.outliers https://pdal.io/en/stable/stages/filters.outlier.html
    # filters.smrf https://pdal.io/en/stable/stages/filters.smrf.html
    # writers.gdal: https://pdal.io/en/stable/stages/writers.gdal.html
    pipeline_json = {
        "pipeline": [
            {
                "type": "readers.las",
                "filename": lidar
            },
            {
                "type": "filters.range",
                "limits": "Classification[2:2]"
            },
            {
                "type": "filters.smrf",  # Este filtro es más preciso para eliminar outliers aislados
                "slope": 0.15,  # Umbral de pendiente para considerar un punto como parte del terreno
                "threshold": 0.5,  # Diferencia máxima de elevación entre un punto y la superficie interpolada para que el punto se considere terreno
                "scalar": 1.2  # Sensibilidad del filtro a los cambios de elevación
            },
            {
                "type": "writers.gdal",
                "filename": mdt,
                "output_type": "idw",  # Para priorizar una superficie suave y continua que represente el terreno desnudo
                "window_size":ventana, # Cuántos de los puntos vecinos más cercanos se utilizarán para interpolar el valor de un píxel
                "resolution": resolucion_raster,
                "gdaldriver": "GTiff",
                "radius": radio_raster,
                "data_type": "float32",
                "nodata": -99999
            }
        ]
    }

    print('Calculando el MDT...', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    # Ejecutar el pipeline
    pipeline = pdal.Pipeline(json.dumps(pipeline_json))
    pipeline.execute()

    # raster_dataset = rasterio.open(mdt_calculado)
    # estadisticas_raster = raster_dataset.stats()

    print('Rellenando píxeles vacíos en el MDT...', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    # Relleno píxeles vacíos del MDT
    # Abro el raster. gdal.GA_Update abre el archivo como lectura/escritura para modificarlo
    mdt_relleno = gdal.Open(mdt, gdal.GA_Update)
    banda = mdt_relleno.GetRasterBand(1)

    # Relleno los huecos con GDAL
    gdal.FillNodata(
        targetBand=banda,
        maskBand=None,
        maxSearchDist=60,
        smoothingIterations=2
    )

    # Libera los recursos del sistema asociados al rater por GDAL
    print('Liberando recursos...', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    mdt_relleno = None

    print(f'MDT creado con éxito en {mdt}\n', '  Duración:', datetime.now() - inicioscript)


if __name__ == "__main__":
    print('Hora de inicio:', inicioscript)

    # Define los parámetros de entrada y salida
    archivo_lidar = 'salidas/lidar_clasificadas/alcontar_clasificada_NDVI.las'
    mds_calculado = 'salidas/chm/mds_NDVI.tif'
    mdt_calculado = 'salidas/chm/mdt_NDVI.tif'
    resolucion_mds_mdt = 0.05
    # Multiplico por 2 el cálculo del radio para evitar píxeles sin datos en el MDT
    radio = resolucion_mds_mdt * math.sqrt(2) * 2  # https://pdal.io/en/stable/stages/writers.gdal.html#radius
    tamano_ventana = 20

    # # Calcula la distancia mínima media entre puntos de la nube de puntos para el teorema de Nyquist-Shannon
    # # Primero convierte la nube de puntos LIDAR en un array de numpy con x, y, z
    # print('Calculando la distancia mínima media entre puntos para usar en el teorema de Nyquist-Shannon...',
    #       datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    # with laspy.open(archivo_lidar) as f:
    #     las = f.read()
    #     puntos = np.vstack((las.x, las.y, las.z)).transpose()
    # # Obtengo la distancia mínima media entre puntos
    # distancia_minima_puntos = distancia_minima_media(puntos)
    # print('Distancia mínima media entre puntos de la nube de puntos:', distancia_minima_puntos)
    # # Calculo la resolucion como la mitad de la distancia mínima entre puntos según el teorema de Nyquist-Shannon
    # resolucion = distancia_minima_puntos / 2
    # print('Resolución del raster resultante según el teorema de Nyquist-Shannon', resolucion)

    # Ejecuta las dos funciones en paralelo
    # with concurrent.futures.ThreadPoolExecutor() as executor:
    #     future_mds = executor.submit(calcula_mds)
    #     future_mdt = executor.submit(calcula_mdt)
    #
    #     # Espera a que las dos funciones hayan acabado
    #     concurrent.futures.wait([future_mds, future_mdt])

    calcula_mds(archivo_lidar, mds_calculado, resolucion_mds_mdt, radio)
    calcula_mdt(archivo_lidar, mdt_calculado, resolucion_mds_mdt, radio, tamano_ventana)

    print('MDS y MDT calculados con éxito', '\nDuración:', datetime.now() - inicioscript)
