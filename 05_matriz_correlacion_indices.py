import rasterio
import numpy as np
import pandas as pd
from pathlib import Path

# ==========================================
# CONFIGURACIÓN DE RUTAS Y PARÁMETROS
# ==========================================
ruta_base = Path(Path(__file__).resolve().parent)
ruta_indices = ruta_base / "entradas" / "dalias" / "indices"

# Pon aquí los índices que quieras analizar
indices = {
    "ndvi": ruta_indices / "230614_ndvi.tif",
    "gndvi": ruta_indices / "230614_gndvi.tif",
    "ndre": ruta_indices / "230614_ndre.tif",
    "msavi": ruta_indices / "230614_msavi.tif",
    "osavi": ruta_indices / "230614_osavi.tif",
    "mcari2": ruta_indices / "230614_mcari2.tif"
}

valor_nodata = -9999.0

# ==========================================
# FUNCIONES
# ==========================================
def crea_stack_indices(diccionario_indices):
    """Carga múltiples rasters y los apila en un array 3D."""
    stack = []
    meta = None

    for name, filepath in diccionario_indices.items():
        with rasterio.open(filepath) as src:
            if meta is None:
                meta = src.meta.copy()
            data = src.read(1).astype(np.float32)
            stack.append(data)

    return np.array(stack), meta

# ==========================================
# FLUJO PRINCIPAL
# ==========================================
if __name__ == "__main__":
    print("1. Cargando y apilando índices para análisis de correlación...")
    stack_data, metadata = crea_stack_indices(indices)
    n_features, rows, cols = stack_data.shape

    print(f"Dimensiones de la imagen: {rows}x{cols} píxeles. Índices: {n_features}")

    # Manejo de NoData EXPLÍCITO (-9999 y NaN)
    print("2. Enmascarando valores NoData...")
    valid_mask = (stack_data != valor_nodata) & (~np.isnan(stack_data))
    valid_mask = valid_mask.all(axis=0)

    X_valid = stack_data[:, valid_mask].T

    if X_valid.shape[0] == 0:
        raise ValueError("Todos los píxeles son NoData. Revisa las rutas.")

    # ==========================================
    # ANÁLISIS OBJETIVO DE REDUNDANCIA
    # ==========================================
    print("\n--- ANÁLISIS DE CORRELACIÓN (REDUNDANCIA) ---")
    # Tomamos una muestra aleatoria de 100,000 píxeles para el cálculo estadístico rápido
    np.random.seed(42)
    n_muestras_corr = min(100000, X_valid.shape[0])
    indices_muestra_corr = np.random.choice(X_valid.shape[0], size=n_muestras_corr, replace=False)
    X_muestra_corr = X_valid[indices_muestra_corr, :]

    # Creamos un DataFrame de pandas para mostrar la tabla en consola
    nombres_indices = list(indices.keys())
    df_corr = pd.DataFrame(X_muestra_corr, columns=nombres_indices)
    matriz_corr = df_corr.corr().round(3) # Pearson por defecto

    print("Matriz de correlación de Pearson (Valores > 0.90 indican alta redundancia):")
    print(matriz_corr.to_string())
    print("---------------------------------------------\n")
    print("Recomendación: Descarta los índices altamente correlacionados comentándolos en el script de K-Means.")