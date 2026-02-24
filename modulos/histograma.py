import rasterio
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path


def histograma(ruta_raster, ruta_salida_histograma, banda):
    ruta_raster = Path(ruta_raster)
    ruta_salida_histograma = Path(ruta_salida_histograma)

    # Si el directorio de salida no existe lo creo
    ruta_salida_histograma.parent.mkdir(parents=True, exist_ok=True)

    if not ruta_raster.exists():
        print(f"No existe el archivo {ruta_raster}")
        return

    try:
        with rasterio.open(ruta_raster) as src:
            # Lweo la primera banda de la imagen, aunque en este caso solo hay una
            data = src.read(banda)
            nodata_val = src.nodata

        # Aplano el array para el histograma
        data_flat = data.flatten()

        # Filtro celdas nulas, NoData y NaNs
        if nodata_val is not None:
            data_flat = data_flat[data_flat != nodata_val]

        # Elimino los pixeles nulos
        data_flat = data_flat[~np.isnan(data_flat)]

        # Cálculo de estadísticas básicas para referencia
        media = np.mean(data_flat)
        mediana = np.median(data_flat)
        std_dev = np.std(data_flat)

        # Configuración del gráfico
        plt.figure(figsize=(10, 6))
        plt.hist(data_flat, bins=100, color="skyblue", edgecolor="black", alpha=0.7, label="Frecuencia")

        # Líneas de referencia
        plt.axvline(media, color="red", linestyle="dashed", linewidth=1.5, label=f"Media: {media:.2f}")
        plt.axvline(mediana, color="green", linestyle="dashed", linewidth=1.5, label=f"Mediana: {mediana:.2f}")

        # Etiquetas y estilo
        # Uso el nombre del archivo sin extensión para el título
        titulo = f"Histograma {ruta_raster.stem}"
        plt.title(titulo, fontsize=14)
        plt.xlabel("Valor del Píxel (Índice)", fontsize=12)
        plt.ylabel("Frecuencia (Nº Píxeles)", fontsize=12)
        plt.legend()
        plt.grid(axis="y", alpha=0.5)

        # Guardar o mostrar
        plt.savefig(ruta_salida_histograma, dpi=300, bbox_inches="tight")
        print(f"Histograma guardado en: {ruta_salida_histograma}")
        plt.show()
        plt.close()  # Cerrar para liberar memoria

    except Exception as e:
        print(f"Error al generar el histograma: {e}")
