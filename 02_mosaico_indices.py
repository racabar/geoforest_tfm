from pathlib import Path
import rasterio
from rasterio.merge import merge
from collections import defaultdict
from datetime import datetime

# Define la ruta de tu proyecto
ruta_base = Path(__file__).resolve().parent

ruta_indices_bloques = ruta_base / "entradas" / "indices"
ruta_indices_unidos = ruta_base / "entradas" / "indices"


def une_indices(dir_entrada, dir_salida):
    dir_entrada = Path(dir_entrada)
    dir_salida = Path(dir_salida)

    # Validar que el directorio de entrada exista
    if not dir_entrada.exists():
        print(f"[Error] El directorio de entrada no existe: {dir_entrada}")
        return

    # Crear el directorio de salida si no existe
    dir_salida.mkdir(parents=True, exist_ok=True)
    print(f"Buscando archivos en: {dir_entrada}")
    print(f"Guardando mosaicos en: {dir_salida}\n")

    # 1. Agrupar los archivos por fecha e índice
    # Usaremos un diccionario de diccionarios: agrupaciones[fecha][indice] = [lista_de_rutas]
    agrupaciones = defaultdict(lambda: defaultdict(list))

    # Iterar solo sobre archivos en el directorio raíz (sin entrar a subcarpetas)
    for ruta_archivo in dir_entrada.iterdir():
        if ruta_archivo.is_file() and ruta_archivo.suffix.lower() == '.tif':

            # Analizar el nombre del archivo (ej: 230614_b1_4_msavi)
            nombre_sin_ext = ruta_archivo.stem
            partes = nombre_sin_ext.split('_')

            # Se asume formato estricto: fecha_bloque1_bloque2_indice
            if len(partes) >= 3:
                fecha = partes[0]
                indice = partes[-1]

                # Excluir archivos que ya hayan sido unidos (ej: 230614_msavi.tif)
                # Si un archivo solo tiene 2 partes separadas por '_', asumimos que ya es un mosaico
                if len(partes) > 2:
                    agrupaciones[fecha][indice].append(ruta_archivo)

    # 2. Procesar y mosaicar cada grupo
    if not agrupaciones:
        print("No se encontraron archivos válidos para unir en el directorio raíz.")
        return

    for fecha, indices in agrupaciones.items():
        for indice, lista_archivos in indices.items():
            print(f"Uniendo bloques para fecha: {fecha} | Índice: {indice.upper()}")
            hora_inicio_indice = datetime.now()

            nombre_salida = f"{fecha}_{indice}.tif"
            ruta_final = dir_salida / nombre_salida

            # Opcional: saltar si el mosaico ya existe
            # if ruta_final.exists():
            #     print(f"  -> El archivo {nombre_salida} ya existe. Saltando...")
            #     continue

            archivos_abiertos = []
            try:
                # Abrir todos los rasters de este grupo
                for ruta in lista_archivos:
                    src = rasterio.open(ruta)
                    archivos_abiertos.append(src)

                # Ejecutar el mosaico espacial
                # rasterio.merge calcula automáticamente las nuevas dimensiones y transformación
                mosaico, out_trans = merge(archivos_abiertos)

                # Copiar la metadata de uno de los archivos originales
                out_meta = archivos_abiertos[0].meta.copy()

                # Actualizar la metadata con las dimensiones y georreferencia del nuevo mosaico
                out_meta.update({
                    "driver": "GTiff",
                    "height": mosaico.shape[1],
                    "width": mosaico.shape[2],
                    "transform": out_trans
                })

                # Guardar el raster resultante
                with rasterio.open(ruta_final, "w", **out_meta) as dest:
                    dest.write(mosaico)

                print(f"  [OK] Guardado: {nombre_salida} (Unidos {len(lista_archivos)} bloques)")
                print(f"  Tiempo de procesado del índice {indice}: ", datetime.now() - hora_inicio_indice)

            except Exception as e:
                print(f"  [Error] Fallo al crear el mosaico para {fecha} {indice}: {e}")

            finally:
                # Buena práctica: cerrar todos los archivos fuente pase lo que pase
                for src in archivos_abiertos:
                    src.close()


if __name__ == "__main__":
    hora_inicio = datetime.now()

    une_indices(ruta_indices_bloques, ruta_indices_unidos)

    tiempo_total = datetime.now() - hora_inicio
    print(f"\nTiempo de procesado total de mosaicos: {tiempo_total}")
