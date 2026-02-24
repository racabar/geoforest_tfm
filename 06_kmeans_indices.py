import rasterio
import numpy as np
from pathlib import Path
from sklearn.cluster import MiniBatchKMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score, calinski_harabasz_score

# ==========================================
# CONFIGURACIÓN DE RUTAS Y PARÁMETROS
# ==========================================
ruta_base = Path(Path(__file__).resolve().parent)
ruta_indices = ruta_base / "entradas" / "dalias" / "indices"

indices = {
    "ndvi": ruta_indices / "230614_ndvi.tif",
    # "gndvi": ruta_indices / "230614_gndvi.tif",
    # "ndre": ruta_indices / "230614_ndre.tif",
    "msavi": ruta_indices / "230614_msavi.tif",
    # "osavi": ruta_indices / "230614_osavi.tif",
    # "mcari2": ruta_indices / "230614_mcari2.tif"
}

# Clusters para K-Means
clusteres_kmeans = 3

# Definir explícitamente el valor NoData de entrada (común en GDAL/QGIS)
valor_nodata = -9999.0


def crea_stack_indices(diccionario_indices):
    stack = []
    meta = None

    for name, filepath in diccionario_indices.items():
        with rasterio.open(filepath) as src:
            if meta is None:
                meta = src.meta.copy()
            data = src.read(1).astype(np.float32)  # Leo la banda 1 como float
            stack.append(data)

    return np.array(stack), meta


if __name__ == "__main__":
    print("1. Cargando y apilando índices...")
    stack_data, metadata = crea_stack_indices(indices)
    n_features, rows, cols = stack_data.shape

    print(f"Dimensiones de la imagen:\n  {rows}x{cols} píxeles.\n  Índices activos: {n_features}")

    # Manejo de NoData EXPLÍCITO (-9999 y NaN)
    print("2. Enmascarando valores NoData...")
    valid_mask = (stack_data != valor_nodata) & (~np.isnan(stack_data))
    valid_mask = valid_mask.all(axis=0)

    # Extraer solo los píxeles válidos (shape: [n_valid_pixels, n_features])
    X_valid = stack_data[:, valid_mask].T
    print(f"Píxeles válidos: {X_valid.shape[0]} de {rows * cols}")

    if X_valid.shape[0] == 0:
        raise ValueError("Todos los píxeles se han marcado como NoData. Revisa las imágenes de entrada.")

    # ==========================================
    # PREPROCESAMIENTO Y CLUSTERING
    # ==========================================
    print("3. Estandarizando variables...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_valid)

    print(f"4. MiniBatchKMeans por lotes con {clusteres_kmeans} clústeres...")
    # batch_size=50000 evita la saturación de memoria RAM con imágenes masivas
    kmeans = MiniBatchKMeans(n_clusters=clusteres_kmeans, random_state=42, batch_size=50000, n_init="auto")
    labels_valid = kmeans.fit_predict(X_scaled)

    # ==========================================
    # RECONSTRUCCIÓN Y EXPORTACIÓN
    # ==========================================
    print("5. Reconstruyendo imagen espacial...")
    # Creamos una imagen base rellena de 255 (que será nuestro nuevo NoData para la clasificación)
    valor_nodata_salida = 255
    class_image = np.full((rows, cols), valor_nodata_salida, dtype=np.uint8)

    # Insertamos las etiquetas calculadas en las posiciones válidas
    class_image[valid_mask] = labels_valid

    print("6. Exportando clasificación...")
    metadata.update({
        "dtype": "uint8",
        "count": 1,
        "nodata": valor_nodata_salida
    })

    # Asegurarnos de que el directorio de salida existe
    ruta_indices.mkdir(parents=True, exist_ok=True)

    # El nombre del archivo se adapta al número de índices usados
    out_path = ruta_indices / f"230614_kmeans_{n_features}_indices.tif"

    with rasterio.open(out_path, "w", **metadata) as dst:
        dst.write(class_image, 1)

    print(f"¡Proceso finalizado! Clasificación guardada en: {out_path}")