"""
Script para descargar imágenes True Color (RGB) de Sentinel-2 para un área
de interés (AOI) y una fecha específicas utilizando sentinelhub-py.

Página para visualizar datos y fechas de paso:
https://browser.dataspace.copernicus.eu/
"""

from pathlib import Path
from typing import Tuple

# Importaciones clave de sentinelhub-py
from sentinelhub import (
    SHConfig,
    CRS,
    BBox,
    DataCollection,
    MimeType,
    SentinelHubRequest,
    bbox_to_dimensions,
)

# Este script de Javascript (evalscript) le dice a Sentinel Hub
# qué bandas procesar (B04=Rojo, B03=Verde, B02=Azul) y cómo devolverlas.
EVALSCRIPT_TRUE_COLOR = """
    //VERSION=3
    function setup() {
        return {
            input: [{
                bands: ["B02", "B03", "B04"]
            }],
            output: {
                bands: 3
            }
        };
    }
    function evaluatePixel(sample) {
        return [sample.B04, sample.B03, sample.B02];
    }
"""


def setup_sentinelhub_config() -> SHConfig:
    """
    Configura y devuelve el objeto de configuración de Sentinel Hub.

    ADVERTENCIA: Es una mala práctica de seguridad escribir credenciales
    directamente en el código. Es preferible usar variables de entorno
    o un fichero de configuración gestionado por sentinelhub-py.

    Returns:
        Un objeto SHConfig configurado.
    """
    config = SHConfig()
    config.sh_client_id = "sh-53449810-cc07-4fce-a2fc-627997583bef"
    config.sh_client_secret = "8PYxgQx9NmuLd9Vp8ChN7XmyI4L6QwwT"
    config.sh_token_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    config.sh_base_url = "https://sh.dataspace.copernicus.eu"
    return config


def define_area_of_interest(
    user_coords: Tuple[float, float, float, float],
    target_crs: CRS,
    resolution: int,
) -> Tuple[BBox, Tuple[int, int]]:
    """
    Define el área de interés (AOI) a partir de coordenadas, la reproyecta
    y calcula las dimensiones de la imagen de salida.

    Args:
        user_coords: Tupla de coordenadas en WGS84 con el formato
                     (lon_min, lat_min, lon_max, lat_max).
        target_crs: El sistema de coordenadas de referencia objetivo (ej. CRS.UTM_30N).
        resolution: La resolución espacial en metros.

    Returns:
        Una tupla conteniendo el BBox reproyectado y el tamaño (ancho, alto)
        de la imagen en píxeles.
    """
    # Crea el objeto Bounding Box original en WGS84
    bbox_wgs84 = BBox(bbox=user_coords, crs=CRS.WGS84)

    # Reproyecta el BBox al CRS objetivo
    bbox_utm = bbox_wgs84.transform(target_crs)

    # Calcula las dimensiones de la imagen usando el BBox en el CRS objetivo
    size = bbox_to_dimensions(bbox_utm, resolution=resolution)

    print(f"BBox original (WGS84): {bbox_wgs84}")
    print(f"BBox reproyectado ({target_crs.name}): {bbox_utm}")
    print(f"Dimensiones de la imagen a {resolution}m: {size} píxeles")

    return bbox_utm, size


def download_true_color_image(
    config: SHConfig,
    bbox: BBox,
    size: Tuple[int, int],
    time_interval: Tuple[str, str],
    output_folder: Path,
) -> None:
    """
    Configura y ejecuta la petición a Sentinel Hub para descargar una imagen.

    Args:
        config: El objeto de configuración de Sentinel Hub.
        bbox: El Bounding Box del área de interés.
        size: El tamaño de la imagen de salida en píxeles.
        time_interval: Tupla con fecha de inicio y fin en formato 'YYYY-MM-DD'.
        output_folder: La ruta (objeto Path) a la carpeta de salida.
    """
    # Define la colección de datos a usar (Sentinel-2 L1C)
    data_collection = DataCollection.SENTINEL2_L1C.define_from(
        "s2l1c", service_url=config.sh_base_url
    )

    # Crea el objeto de la petición
    request = SentinelHubRequest(
        data_folder=str(output_folder),
        evalscript=EVALSCRIPT_TRUE_COLOR,
        input_data=[
            SentinelHubRequest.input_data(
                data_collection=data_collection,
                time_interval=time_interval,
            )
        ],
        responses=[SentinelHubRequest.output_response("default", MimeType.TIFF)],
        bbox=bbox,
        size=size,
        config=config,
    )

    # Ejecuta la descarga
    print(f"\nDescargando imagen True Color para el intervalo {time_interval}...")
    request.save_data()

    # Muestra los archivos guardados
    try:
        filename_list = request.get_filename_list()
        print("¡Descarga completada! Archivo(s) guardado(s) en:")
        for filename in filename_list:
            full_path = output_folder / filename
            print(full_path)
    except Exception as e:
        print(f"Se produjo un error al obtener los nombres de archivo: {e}")
        print("La descarga pudo haberse completado, revisa la carpeta de salida.")


def main():
    """Función principal para ejecutar el script de descarga."""
    # --- PARÁMETROS DE ENTRADA ---
    # Coordenadas en formato (lon_oeste, lat_sur, lon_este, lat_norte)
    alcontar_coords_wgs84 = (-2.8483638, 36.8275869, -2.7957783, 36.8587230)
    fecha = "2025-05-19"
    resolution = 10  # Resolución espacial en metros
    output_folder = Path("../descargas_sentinel")
    target_crs = CRS.UTM_30N  # EPSG:32630

    print(f"Descargando imagen True Color para {fecha} en la carpeta '{output_folder}'...")

    # Crea la carpeta de salida si no existe
    output_folder.mkdir(parents=True, exist_ok=True)

    # 1. Configuración de Sentinel Hub
    config = setup_sentinelhub_config()

    # 2. Definición del Área de Interés (AOI)
    bbox, size = define_area_of_interest(
        user_coords=alcontar_coords_wgs84,
        target_crs=target_crs,
        resolution=resolution,
    )

    # 3. Ejecución de la descarga
    # Se usa la misma fecha para inicio y fin para buscar en un solo día.
    time_interval = (fecha, fecha)
    download_true_color_image(
        config=config,
        bbox=bbox,
        size=size,
        time_interval=time_interval,
        output_folder=output_folder,
    )


if __name__ == "__main__":
    main()