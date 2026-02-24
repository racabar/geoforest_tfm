from pathlib import Path
from modulos.histograma import histograma
from datetime import datetime

hora_inicio = datetime.now()

# Definir el directorio base
# Se asume que el script se ejecuta desde la raíz del proyecto
ruta_entrada = Path("entradas/dalias/indices/nuevos")


def histograma_imagen(ruta):

    if not ruta.exists():
        print(f"Error: El directorio {ruta} no existe.")
        return

    # Buscar recursivamente todos los archivos .tif en subdirectorios
    imagenes = list(ruta.rglob("*.tif"))

    if not imagenes:
        print(f"No se encontraron imágenes .tif en {ruta}")
        return

    print(f"Se han encontrado {len(imagenes)} imágenes. Generando histogramas...")

    for img_path in imagenes:
        hora_inicio_indice = datetime.now()
        # Definir la ruta de salida del histograma (mismo nombre, extensión .png)
        salida_histograma = img_path.with_suffix('.png')
        
        print(f"Procesando: {img_path.name}")
        
        # Generar el histograma
        # Se asume banda 1 ya que son índices espectrales
        histograma(str(img_path), str(salida_histograma), banda=1)
        print(f"Tiempo de procesado de {img_path.name}: ", datetime.now() - hora_inicio_indice)

if __name__ == "__main__":
    histograma_imagen(ruta_entrada)
    print(f"\nTiempo de procesado total: {datetime.now() - hora_inicio}")
