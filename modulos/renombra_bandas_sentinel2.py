import os

# Diccionario qeu relaciona nombres de bandas de Sentinel 2 con bandas
bandas_sentinel2 = {
    "B01.tif": "aerosoles.tif",
    "B02.tif": "blue.tif",
    "B03.tif": "green_560.tif",
    "B04.tif": "red.tif",
    "B05.tif": "red_edge_705.tif",
    "B06.tif": "red_edge_740.tif",
    "B07.tif": "red_edge_780.tif",
    "B08.tif": "nir.tif",
    "B8A.tif": "nir2.tif",
    "B09.tif": "vapor_agua.tif",
    "B10.tif": "b10.tif",            # SWIR – Cirrus (Atmospheric Correction)
    "B11.tif": "swir1.tif",
    "B12.tif": "swir2.tif"
}

def renombra_imagenes(ruta_bandas: str, mapeo_bandas: dict):
    """
    Renombra archivos de bandas de Sentinel-2 según EL diccionario bandas_sentinel2_awi

    Args:
        ruta_bandas (str): La ruta al directorio que contiene los archivos de las bandas
        mapeo_bandas (dict): Un diccionario donde las claves son los nombres de archivo
                             originales y los valores son los nuevos nombres
    """
    print(f"Iniciando el proceso de renombrado en: '{ruta_bandas}'")
    # Recorre los archivos en el directorio
    for nombre_archivo in os.listdir(ruta_bandas):

        # Comprueba si el archivo debe ser renombrado verificando si está en el diccionario
        if nombre_archivo in mapeo_bandas:
            # Obtiene el nuevo nombre del diccionario
            nuevo_nombre = mapeo_bandas[nombre_archivo]

            # Construye la ruta del archivo antiguo y nuevo
            ruta_antigua = os.path.join(ruta_bandas, nombre_archivo)
            ruta_nueva = os.path.join(ruta_bandas, nuevo_nombre)

            # Renombra el archivo
            os.rename(ruta_antigua, ruta_nueva)

            print(f"  - Renombrado: '{nombre_archivo}' -> '{nuevo_nombre}'")
        # else:
        #     print(f"  - Ignorado: '{nombre_archivo}' (no encontrado en el mapeo)")

    print("\nArchivos renombrados.")

if __name__ == "__main__":
    # Define la ruta base para las bandas de Sentinel-2
    # Asegúrate de que esta ruta sea correcta para tu sistema
    ruta_directorio_bandas = "bandas_sentinel2/dalias_2023-10-07"

    # Llama a la función principal para renombrar las bandas
    renombra_imagenes(ruta_directorio_bandas, bandas_sentinel2)