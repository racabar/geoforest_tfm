import rasterio
from rasterio.warp import reproject, Resampling
from pathlib import Path
import numpy as np


def resta_rasters(ruta_raster_pre, ruta_raster_post, ruta_salida):
    """
    Realiza la resta de dos rásters (A - B) y guarda el resultado en un nuevo archivo GeoTIFF.

    Si los rásters no están alineados, el segundo ráster (B) se reproyectará
    para que coincida con el sistema de referencia de coordenadas (CRS), transformación,
    dimensiones y extensión del primero (A).

    Args:
        ruta_raster_pre (str): Ruta al primer ráster (minuendo, A).
        ruta_raster_post (str): Ruta al segundo ráster (sustraendo, B).
        ruta_salida (str): Ruta donde se guardará el ráster de diferencia.
    """

    try:
        # Abrir el primer ráster (A) y leer sus datos y metadatos
        with rasterio.open(ruta_raster_pre) as src_a:
            array_a = src_a.read(1, masked=True)
            meta = src_a.meta.copy()
            nodata_a = src_a.nodata

        # Abrir el segundo ráster (B)
        with rasterio.open(ruta_raster_post) as src_b:
            nodata_b = src_b.nodata

            # Comprobar si es necesario reproyectar el ráster B
            if src_a.shape != src_b.shape or src_a.transform != src_b.transform or src_a.crs != src_b.crs:
                print("Advertencia: Los rásters no coinciden. Reproyectando el segundo ráster para que coincida con el primero.")
                print(f"  Ráster de referencia (A): {ruta_raster_pre} (Shape: {src_a.shape}, CRS: {src_a.crs})")
                print(f"  Ráster a reproyectar (B): {ruta_raster_post} (Shape: {src_b.shape}, CRS: {src_b.crs})")

                # Crear un array vacío con la forma y tipo de dato del ráster de referencia (A)
                array_b_reprojected = np.empty_like(array_a.data)

                # Reproyectar
                reproject(
                    source=rasterio.band(src_b, 1),
                    destination=array_b_reprojected,
                    src_transform=src_b.transform,
                    src_crs=src_b.crs,
                    dst_transform=src_a.transform,
                    dst_crs=src_a.crs,
                    resampling=Resampling.bilinear
                )

                # Crear un array enmascarado a partir del resultado reproyectado
                # Usar el valor nodata del ráster B si existe, sino, usar el de A.
                nodata_val_for_mask = nodata_b if nodata_b is not None else nodata_a
                if nodata_val_for_mask is not None:
                    mask = (array_b_reprojected == nodata_val_for_mask)
                    array_b = np.ma.masked_array(array_b_reprojected, mask=mask)
                else:
                    # Si no hay valor nodata, no se enmascara nada.
                    array_b = np.ma.masked_array(array_b_reprojected)

                print("Reproyección completada.")

            else:
                # Si no es necesario reproyectar, simplemente leer el ráster B
                print("Los rásters ya están alineados.")
                array_b = src_b.read(1, masked=True)


        print(f"Leyendo Ráster A: {ruta_raster_pre} (NoData: {nodata_a})")
        print(f"Leyendo Ráster B: {ruta_raster_post} (NoData: {nodata_b})")

        # --- Realizar la resta ---

        # Convertir a float32 para la operación y evitar desbordamiento
        array_a = array_a.astype(rasterio.float32)
        array_b = array_b.astype(rasterio.float32)

        # La resta entre arrays enmascarados (MaskedArrays) propaga la máscara.
        diff_array = array_a - array_b

        print("Cálculo de la diferencia completado.")

        # --- Guardar el resultado ---

        # Actualizar los metadatos para el archivo de salida
        meta.update({
            'dtype': 'float32',
            'nodata': diff_array.fill_value
        })

        # Asegurarse de que el directorio de salida exista
        Path(ruta_salida).parent.mkdir(parents=True, exist_ok=True)

        with rasterio.open(ruta_salida, 'w', **meta) as dst:
            dst.write(diff_array.filled(diff_array.fill_value), 1)

        print(f"Resta completada. Resultado guardado en: {ruta_salida}")

    except rasterio.errors.RasterioIOError as e:
        print(f"Error de E/S al abrir o guardar archivos: {e}")
    except Exception as e:
        print(f"Ha ocurrido un error inesperado: {e}")


# --- Ejemplo de uso ---
if __name__ == "__main__":
    # Ruta de rasters de entrada
    EP = "dalias"

    # Años de comparación
    ANO_PRE = "231010"
    ANO_POST = "250523"

    # Bloques de Dalías
    BLOQUES_DALIAS = "B1-4"

    # Ruta al ráster pre
    raster_pre = Path("../entradas") / EP / "indices" / ANO_PRE / BLOQUES_DALIAS / "NDVI.tif"

    # Ruta al ráster post
    raster_post = Path("../entradas") / EP / "indices" / ANO_POST / BLOQUES_DALIAS / "NDVI.tif"

    # Ruta para el archivo de salida
    RASTER_RESULTADO = Path("../salidas") / EP / ANO_POST / f"dNDVI/dNDVI_{BLOQUES_DALIAS}_{ANO_PRE}-{ANO_POST}.tif"

    resta_rasters(raster_pre, raster_post, RASTER_RESULTADO)
