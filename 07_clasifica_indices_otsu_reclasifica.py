from pathlib import Path
import rasterio
import numpy as np
from modulos.clasifica_imagen_otsu import clasifica_imagen_otsu


def reclasificar_otsu_a_binario(ruta_entrada_3c, ruta_salida_binaria):
    try:
        with rasterio.open(ruta_entrada_3c) as src:
            meta = src.profile.copy()
            data = src.read(1)

        # ÁLGEBRA DE MAPAS: Reclasificamos la matriz
        # np.where(condicion, valor_si_verdadero, valor_si_falso)
        # Todo lo que sea estrictamente mayor a 0 (clases 1 y 2) pasará a ser 1.
        data_reclasificada = np.where(data > 0, 1, 0).astype(np.uint8)

        # Guardamos la imagen reclasificada con los mismos metadatos
        with rasterio.open(ruta_salida_binaria, 'w', **meta) as dst:
            dst.write(data_reclasificada, 1)
            dst.set_band_description(1, f"Otsu_Binario_Reclasificado")

        print(f"  -> Reclasificación binaria guardada en: {ruta_salida_binaria.name}")

    except Exception as e:
        print(f"Error al reclasificar la imagen {ruta_entrada_3c.name}: {e}")


def procesar_indices_otsu(ruta_entrada_indices, ruta_salida_otsu, nombre_indice, num_clases, banda):
    # Me quedo con los archivos que coincidan con el índice que me interesa
    archivos = list(ruta_entrada_indices.glob(f"*{nombre_indice}.tif"))

    if not archivos:
        print(f"No hay archivos del índice '{nombre_indice}.tif' en {ruta_entrada_indices}")
        return []

    rutas_generadas_3c = []

    # Iteramos sobre cada archivo encontrado
    for archivo in archivos:
        # Cojo la fecha (6 primeros caracteres del nombre del archivo)
        fecha = archivo.name[:6]

        # Creo el nombre y ruta de salida para la imagen de Otsu
        nombre_salida_3c = f"20{fecha}_{nombre_indice}_otsu_{num_clases}c.tif"
        ruta_salida_3c = ruta_salida_otsu / nombre_salida_3c

        print(f"\nProcesando Otsu (3 clases) para: {archivo.name}...")

        # 1. Llamo a la función original para clasificar con Otsu (no tocamos tu script original)
        clasifica_imagen_otsu(
            ruta_entrada=archivo,
            ruta_salida=ruta_salida_3c,
            banda=banda,
            clases_otsu=num_clases
        )

        # Si el archivo se creó correctamente, lo guardamos en nuestra lista de retorno
        if ruta_salida_3c.exists():
            rutas_generadas_3c.append(ruta_salida_3c)

    print("\nProcesamiento Otsu finalizado.")
    return rutas_generadas_3c


if __name__ == "__main__":
    ruta_base = Path(__file__).resolve().parent
    ruta_indices = ruta_base / "entradas" / "indices"
    directorio_salida = ruta_base / "salidas" / "segmentaciones" / "20260312_otsu_ndvi_tvi2"

    indice = "tvi2"
    clases_otsu = 3
    banda_procesamiento = 1

    # Clasifico los índices con Otsu
    archivos_procesados_3c = procesar_indices_otsu(
        ruta_entrada_indices=ruta_indices,
        ruta_salida_otsu=directorio_salida,
        nombre_indice=indice,
        num_clases=clases_otsu,
        banda=banda_procesamiento
    )

    # Reclasifico los resultados de Otsu en 2 clases
    if archivos_procesados_3c:
        print("\nIniciando fase de reclasificación binaria...")
        for ruta_3c in archivos_procesados_3c:
            # Construimos el nombre binario reemplazando el final de la cadena de texto
            nombre_binario = ruta_3c.name.replace(f"_{clases_otsu}c.tif", f"_{clases_otsu}c_binario.tif")
            ruta_binaria = ruta_3c.parent / nombre_binario

            reclasificar_otsu_a_binario(
                ruta_entrada_3c=ruta_3c,
                ruta_salida_binaria=ruta_binaria
            )

        print("\nFlujo de trabajo completo finalizado.")