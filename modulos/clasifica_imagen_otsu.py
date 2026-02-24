import rasterio
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from pathlib import Path
from skimage.filters import threshold_multiotsu

def clasifica_imagen_otsu(ruta_entrada, ruta_salida, banda, clases_otsu=2):
    ruta_entrada = Path(ruta_entrada)
    ruta_salida = Path(ruta_salida)

    if not ruta_entrada.exists():
        print(f"No existe el archivo de entrada: {ruta_entrada}")
        return

    # Creo el directorio de salida si no existe
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    try:
        with rasterio.open(ruta_entrada) as src:
            # Leo la banda donde está la información y me quedo con los metadatos
            data = src.read(banda)
            meta = src.profile.copy()
            nodata_val = src.nodata

            # Creo una máscara de datos válidos para calcular Otsu ignorando valores nulos
            if nodata_val is not None:
                mascara_validos = (data != nodata_val) & (~np.isnan(data))
            else:
                mascara_validos = ~np.isnan(data)

            # Me quedo con los píxeles válidos para calcular el umbral
            datos_validos = data[mascara_validos]

            if datos_validos.size == 0:
                print("La imagen no tiene datos válidos para calcular Otsu.")
                return

            # Calculo los umbrales de Otsu
            # threshold_multiotsu devuelve n_clases - 1 umbrales
            umbrales = threshold_multiotsu(datos_validos, classes=clases_otsu)
            
            print(f"Umbrales de Otsu calculados: {umbrales}")

            # Clasificación usando np.digitize
            # np.digitize devuelve los índices de los bins a los que pertenece cada valor
            # Si solo son dos umbrales, np.digitize asigna 0 por debajo del umbral y 1 por encima
            imagen_clasificada = np.digitize(data, bins=umbrales).astype(np.uint8)

            # Controlo los valores nulos si hay, asignándoles el valor 0
            # para que la imagen resultante solo tenga valores 0 y 1
            mask_nodata = np.isnan(data)
            if nodata_val is not None:
                mask_nodata = mask_nodata | (data == nodata_val)
            
            if mask_nodata.any():
                imagen_clasificada[mask_nodata] = 0

            # Actualizo los metadatos de la imagen de salida
            meta.update(
                dtype=rasterio.uint8,
                count=1,
                compress='lzw',
                nodata=None  # Eliminamos nodata para que sea 0 (valor válido)
            )
            
            # Formateo los umbrales para la descripción
            umbrales_str = "_".join([f"{u:.3f}" for u in umbrales])

            # Guardo la imagen reclasificada asingándole los metadatos de la original
            with rasterio.open(ruta_salida, 'w', **meta) as salida:
                salida.write(imagen_clasificada, 1)
                salida.set_band_description(1, f"Clasificacion_Otsu_Umbrales_{umbrales_str}")

            print(f"Clasificación Otsu guardada en: {ruta_salida}")

            # Visualización
            plt.figure(figsize=(10, 8))

            # Enmascarar NoData para visualización
            datos_plot = np.ma.masked_equal(imagen_clasificada, 255)

            # Si son 2 clases (quemado/no quemado) se ven solo dos colores (negro y blanco)
            if clases_otsu == 2:
                # Asumimos que la clase alta (1) es quemado
                datos_masked = np.ma.masked_where(imagen_clasificada != 1, imagen_clasificada)
                cmap = ListedColormap(['black'])
                plt.imshow(datos_masked, cmap=cmap, interpolation='nearest')
                plt.title(f"Área Quemada (Clase 1) - Otsu: {ruta_salida.name}")
            else:
                # Si son más clases se muestra usando una rampa de color (Viridis)
                plt.imshow(datos_plot, cmap='viridis', interpolation='nearest')
                plt.colorbar(ticks=range(clases_otsu), label='Clase')
                plt.title(f"Clasificación Multi-Otsu ({clases_otsu} clases): {ruta_salida.name}")

            plt.axis('off')
            plt.show()

    except Exception as e:
        print(f"Error en clasificación Otsu: {e}")
