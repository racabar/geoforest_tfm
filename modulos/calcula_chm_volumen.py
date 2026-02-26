from datetime import datetime
import pandas as pd
import geopandas as gpd
import rasterio
from rasterstats import zonal_stats
import numpy as np
from osgeo import gdal

from modulos.graficaRegresion import regresion_por_categoria

inicioscript = datetime.now()


def alinear_raster_gdal(raster_maestro_path, raster_a_alinear_path, raster_alineado_output_path):
    """
    NUEVA FUNCIÓN:
    Alinea un ráster a la rejilla (extent, CRS, resolución) de un ráster maestro usando gdal.Warp.
    Esto es crucial para asegurar que las operaciones de álgebra de mapas sean espacialmente correctas.
    """
    maestro = gdal.Open(raster_maestro_path, gdal.GA_ReadOnly)
    if not maestro:
        raise Exception(f"No se pudo abrir el ráster maestro: {raster_maestro_path}")

    # Obtener la información geoespacial del maestro
    proyeccion_maestro = maestro.GetProjection()
    geotransform_maestro = maestro.GetGeoTransform()
    x_min = geotransform_maestro[0]
    y_max = geotransform_maestro[3]
    x_max = x_min + geotransform_maestro[1] * maestro.RasterXSize
    y_min = y_max + geotransform_maestro[5] * maestro.RasterYSize

    maestro = None  # Liberar el objeto

    print(f"Alineando {raster_a_alinear_path} a la rejilla de {raster_maestro_path}...")

    # Usar gdal.Warp para alinear el ráster. Esto replica la alineación automática de un SIG
    gdal.Warp(raster_alineado_output_path,
              raster_a_alinear_path,
              outputBounds=[x_min, y_min, x_max, y_max],
              xRes=geotransform_maestro[1],
              yRes=geotransform_maestro[5],
              dstSRS=proyeccion_maestro,
              resampleAlg='bilinear',  # 'bilinear' es una buena opción para datos continuos como la elevación
              outputType=gdal.GDT_Float32,
              creationOptions=['COMPRESS=LZW'])

    print(f"Alineación completada. Archivo guardado en: {raster_alineado_output_path}")


def calcula_chm(mds_tif, mdt_tif, chm_calculado, volumen_calculado, cuadrados, fitovolumenBd,
                columna_x=None, columna_y=None, indice=None, columna_tratamiento=None,
                tipo_calculo=None, unidades_volumen=None, ruta_metricas=None):
    try:
        # --- PASO 1: ALINEAR EL MDT AL MDS ---
        # Se crea un nuevo archivo temporal para el MDT alineado para no modificar el original.
        # Esto soluciona el problema de los valores negativos causados por la resta de píxeles no alineados.
        mdt_alineado_tif = mdt_tif.replace('.tif', '_alineado.tif')
        alinear_raster_gdal(mds_tif, mdt_tif, mdt_alineado_tif)

        # --- PASO 2: LECTURA DE RÁSTERES ALINEADOS ---
        # Ahora abrimos el MDS original y el NUEVO MDT alineado.
        with rasterio.open(mds_tif) as mds_entrada, rasterio.open(mdt_alineado_tif) as mdt_entrada:
            # Verificación (opcional pero recomendada): nos aseguramos de que las propiedades espaciales coinciden
            assert mds_entrada.shape == mdt_entrada.shape, "Error: Las dimensiones no coinciden después de alinear."
            assert mds_entrada.crs == mdt_entrada.crs, "Error: Los CRS no coinciden después de alinear."
            assert mds_entrada.transform == mdt_entrada.transform, "Error: Las transformaciones afines no coinciden."

            # Lee los datos de las bandas como arrays
            mds_data = mds_entrada.read(1)
            mdt_data = mdt_entrada.read(1)

        # Me quedo con el tamaño y la superficie del pixel de mds_data por ejemplo
        # para usarlo al calcular el volumen a partir del CHM
        # mdt y mds deben tener el mismo tamaño de pixel
        with rasterio.open(mds_tif) as mds_para_pixeles:
            transform = mds_para_pixeles.transform
            pixel_size_x = transform[0]
            pixel_size_y = -transform[4]
            superficie_pixel = pixel_size_x ** 2  # Lado x del pixel al cuadrado

        # --- PASO 3: CÁLCULO DEL CHM ---
        # Hace el cálculo de chm. La resta ahora es espacialmente correcta.
        # Se usa np.maximum para convertir a 0 cualquier valor negativo residual producto de ruido
        chm = np.maximum(mds_data - mdt_data, 0)

        # Guarda el chm en un tif
        with rasterio.open(
                chm_calculado,
                'w',
                driver='GTiff',
                height=chm.shape[0],
                width=chm.shape[1],
                count=1,
                dtype=rasterio.float32,
                crs=rasterio.open(mds_tif).crs,  # Se toma el CRS del maestro
                transform=rasterio.open(mds_tif).transform,  # y su transformación
                nodata=-9999,
                metadata={
                    'CREATOR': 'Servicio de Evaluación, Restauración y Protección de Agrosistemas Mediterráneos (SERPAM)',
                    'DESCRIPTION': 'Canopy Height Model (CHM) calculado a partir de MDS y MDT alineados'
                }
        ) as dst:
            dst.write(chm, 1)

        # Calcula el fitovolumen a partir del CHM
        with rasterio.open(chm_calculado) as chm_entrada:
            chm_data = chm_entrada.read(1)
            vol = chm_data * superficie_pixel
            with rasterio.open(
                    volumen_calculado,
                    'w',
                    driver='GTiff',
                    height=vol.shape[0],
                    width=vol.shape[1],
                    count=1,
                    dtype=rasterio.float32,
                    crs=chm_entrada.crs,
                    transform=chm_entrada.transform,
                    nodata=-9999,
                    metadata={
                        'CREATOR': 'Servicio de Evaluación, Restauración y Protección de Agrosistemas Mediterráneos (SERPAM)',
                        'DESCRIPTION': 'Volumen de biomasa calculado a partir del CHM'
                    }
            ) as dst:
                dst.write(vol, 1)

        # Calcula las estadísticas zonales por quadrat
        estadisticas_zonales = zonal_stats(cuadrados, volumen_calculado, stats='sum', nodata=0, geojson_out=True)

        # Guardo las estadísticas zonales en un dataframe de pandas
        df_estadisticas_zonales = pd.DataFrame([feature['properties'] for feature in estadisticas_zonales])

        # Renombro la columna sum procedente de zonal_stats para llamarla fitovolumen_m2
        df_estadisticas_zonales = df_estadisticas_zonales.rename(columns={'sum': 'fitovolumen_m2'})

        # Creo una nueva columna para expresar el fitovolumen por ha
        df_estadisticas_zonales['fitovolumen_ha'] = df_estadisticas_zonales['fitovolumen_m2'] * 10000

        # Limpio el dataframe para quedarme solo con las columnas que me interesan (ID_QUADRAT, quema, fitovolumen_m2 y fitovolumen_ha)
        columnas_eliminar = [
            'NOMBRE',
            'TIPO_VEG',
            'TRAT_QUEMA',
            'TRAT_PASTO',
            'TIPO_COB',
            'NOM_ESTADI',
            'NOMGPS',
            'OBSERVACIO',
            'areaquadrat'
        ]
        # COMENTAR ESTA LÍNEA EN EL CASO DEL FITOVOLUMEN
        # df_estadisticas_zonales = df_estadisticas_zonales.drop(columns=columnas_eliminar)

        # Uno el dataframe de estadísticas zonales con el de fitovolumen procedente de la base de datos
        df_unidos = pd.merge(fitovolumenBd, df_estadisticas_zonales, on='ID_QUADRAT', how='inner')
        print(df_unidos.to_string())

        # NO TENGO EN CUENTA EL QUADRAT 54 QUE NO SE QUEMÓ EN SU MOMENTO Y SOLO METE RUIDO
        # COMENTAR ESTA LÍNEA EN DALÍAS
        # df_unidos = df_unidos.query(f'ID_QUADRAT not in [54]')

        # Guardo el dataframe df_unidos en un csv
        df_unidos.to_csv(volumen_calculado.replace('tif', 'csv'), index=False)

        # Asigno las columnas a las variables de la regresión
        # columna_x = 'fitovolumen_ha'
        # columna_y = columna_fitovolumen_bd

        # Hago la regresión por categoría
        # regresion_por_categoria(df_unidos, volumen_calculado, indice, columna_x, columna_y, unidades_volumen, tipo_calculo, columna_tratamiento, ruta_metricas)

    except Exception as e:
        print(f'Error al calcular el CHM: {e}')
        raise


if __name__ == "__main__":
    print('Hora de inicio:', inicioscript)

    # Rutas a los archivos de entrada y salida
    mds_tif = '../salidas/dalias/250523/fitovolumen/B2-3/verde_COB_TOTAL/NDVI_mds.tif'
    mdt_tif = '../salidas/dalias/250523/fitovolumen/B2-3/verde_COB_TOTAL/NDVI_mdt.tif'
    chm_calculado = '../salidas/dalias/250523/fitovolumen/B2-3/verde_COB_TOTAL/NDVI_chm.tif'
    volumen_calculado = '../salidas/dalias/250523/fitovolumen/B2-3/verde_COB_TOTAL/NDVI_vol.tif'
    quadrats = gpd.read_file('../entradas/infoVectorial.gpkg', layer='daliasQuadratsDespuesDesbroce')
    fitovolumen_bd = pd.read_csv('../entradas/fitovolumen/fitovolumen_compas_250523.csv')

    # Llamando a la función como estaba en tu script original
    calcula_chm(mds_tif, mdt_tif, chm_calculado, volumen_calculado, quadrats, fitovolumen_bd)

    print('CHM creado con éxito\n', '  Duración:', datetime.now() - inicioscript)