import os
import sys
import numpy as np
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
import spyndex

# Mapeo de parámetros Spyndex a nombres de archivo esperados
MAPA_BANDAS = {
    'B': 'blue.tif',
    'G': 'green_560.tif',
    'G1': 'green_531.tif',
    'R': 'red.tif',
    'N': 'nir.tif',
    'RE1': 'red_edge_705.tif',
    'RE2': 'red_edge_740.tif',
    # 'S2': 'swir2.tif'
}

# Constantes usadas por Spyndex
CONSTANTES_SPYNDEX = [
    'g', 'L', 'C1', 'C2', 'c', 'cexp', 'nexp', 'alpha', 'beta', 
    'epsilon', 'fdelta', 'gamma', 'omega', 'sla', 'slb', 'k', 'p', 'sigma'
]

CRS_SALIDA = 'EPSG:32630'
NODATA_VAL = -9999.0

def carga_bandas(ruta_entrada):
    print(f'Leyendo rasters del directorio {ruta_entrada}...')
    
    if not os.path.exists(ruta_entrada):
        raise FileNotFoundError(f"El directorio de entrada no existe: {ruta_entrada}")

    datos_bandas = {}
    info_referencia = None

    for param, archivo in MAPA_BANDAS.items():
        ruta_completa = os.path.join(ruta_entrada, archivo)
        if not os.path.exists(ruta_completa):
            # Opcional: Imprimir advertencia si falta alguna banda crítica
            # print(f"Advertencia: Archivo no encontrado: {archivo} (Para parámetro {param})")
            continue

        try:
            with rasterio.open(ruta_completa) as src:
                data = src.read(1)
                mask = src.read_masks(1) == 0  # True donde es nodata/masked
                datos_bandas[param] = {'data': data, 'mask': mask}
                
                # Usar la banda Roja como referencia, o la primera que encontremos
                if info_referencia is None or param == 'R':
                    info_referencia = {
                        'crs': src.crs,
                        'transform': src.transform,
                        'width': src.width,
                        'height': src.height,
                        'bounds': src.bounds
                    }
        except Exception as e:
            print(f'Error al leer el archivo {archivo}: {e}')

    if not datos_bandas:
        raise FileNotFoundError("No se encontraron bandas válidas en el directorio.")
    
    if info_referencia is None:
        raise FileNotFoundError("No se pudo obtener información de referencia espacial (falta banda roja u otras).")

    return datos_bandas, info_referencia

def procesa_indices(datos_bandas, info_ref, ruta_salida, lista_indices):
    os.makedirs(ruta_salida, exist_ok=True)

    # Preparar parámetros para spyndex (bandas + constantes)
    params = {k: v['data'] for k, v in datos_bandas.items()}
    
    for const in CONSTANTES_SPYNDEX:
        if const in spyndex.constants:
            params[const] = float(spyndex.constants[const].value)

    # Información espacial de origen
    src_crs = info_ref['crs']
    src_transform = info_ref['transform']
    src_width = info_ref['width']
    src_height = info_ref['height']
    src_bounds = info_ref['bounds']

    # Calcular transformación de salida
    dst_transform, dst_width, dst_height = calculate_default_transform(
        src_crs, CRS_SALIDA, src_width, src_height, *src_bounds
    )

    # Crear máscara combinada de todas las bandas cargadas
    # (Si un píxel es inválido en CUALQUIER banda cargada, se enmascara)
    combined_mask = None
    for info in datos_bandas.values():
        if combined_mask is None:
            combined_mask = info['mask'].copy()
        else:
            combined_mask |= info['mask']

    for indice in lista_indices:
        print(f'Calculando índice: {indice}')
        try:
            calculo = spyndex.computeIndex(index=indice, params=params)
        except Exception as e:
            print(f"Error calculando {indice}: {e}")
            continue

        # Asegurar tipo y aplicar máscara
        calculo = np.array(calculo, dtype=np.float32)
        
        if combined_mask is not None:
            # Asegurarse que las dimensiones coincidan (spyndex a veces devuelve formas distintas si inputs difieren)
            if calculo.shape == combined_mask.shape:
                calculo[combined_mask] = NODATA_VAL
            else:
                print(f"Advertencia: Dimensiones no coinciden para máscara en {indice}")

        print(f'Guardando índice: {indice}')
        
        destination = np.zeros((dst_height, dst_width), dtype=np.float32)

        reproject(
            source=calculo,
            destination=destination,
            src_transform=src_transform,
            src_crs=src_crs,
            dst_transform=dst_transform,
            dst_crs=CRS_SALIDA,
            resampling=Resampling.nearest,
            src_nodata=NODATA_VAL,
            dst_nodata=NODATA_VAL
        )

        archivo_salida = os.path.join(ruta_salida, f'{indice}.tif')
        with rasterio.open(
            archivo_salida,
            'w',
            driver='GTiff',
            height=dst_height,
            width=dst_width,
            count=1,
            dtype=rasterio.float32,
            crs=CRS_SALIDA,
            transform=dst_transform,
            nodata=NODATA_VAL,
        ) as dst:
            dst.write(destination, 1)

def calcula_indices(ruta_entrada, ruta_salida, lista_indices=None):
    if lista_indices is None:
        print("No se especificaron índices para calcular.")
        return

    datos_bandas, info_ref = carga_bandas(ruta_entrada)
    procesa_indices(datos_bandas, info_ref, ruta_salida, lista_indices)
    print(f'Proceso completado. Índices guardados en {ruta_salida}')

if __name__ == "__main__":
    if len(sys.argv) >= 4:
        ruta_in = sys.argv[1]
        ruta_out = sys.argv[2]
        # El tercer argumento se espera como una cadena separada por comas: "NDVI,GNDVI"
        indices = sys.argv[3].split(',')
        calcula_indices(ruta_in, ruta_out, indices)
    else:
        print("Uso: python 01_calcula_indices.py <ruta_entrada> <ruta_salida> <indice1,indice2,...>")
