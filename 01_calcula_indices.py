from pathlib import Path
from modulos.calcula_indices import calcula_indices
from datetime import datetime

hora_inicio = datetime.now()

ruta_base = Path(Path(__file__).resolve().parent)

ruta_bandas = ruta_base / "entradas" / "bandas"
ruta_indices = ruta_base / "entradas" / "indices"

indices_a_calcular = ["TriVI"]


def procesa_indices(ruta_bandas, ruta_indices, indices):
    if not ruta_bandas.exists():
        print(f"Error: No se encuentra el directorio de bandas en {ruta_bandas}")
        return

    ruta_indices.mkdir(parents=True, exist_ok=True)

    for ruta_fecha in ruta_bandas.iterdir():
        if not ruta_fecha.is_dir():
            continue

        fecha = ruta_fecha.name

        for ruta_bloque in ruta_fecha.iterdir():
            if not ruta_bloque.is_dir():
                continue

            bloque = ruta_bloque.name
            print(f"\n--- Procesando vuelo de fecha: {fecha}, bloque: {bloque} ---")

            # Formatear el prefijo (ej: 230614_b1_4)
            bloque_formateado = bloque.lower().replace("-", "_")

            try:
                # 1. El módulo guarda en la ruta final con nombres genéricos (ej: NDVI.tif)
                calcula_indices(
                    ruta_entrada=str(ruta_bloque),
                    ruta_salida=str(ruta_indices),
                    lista_indices=indices
                )

                # 2. Renombrado inmediato "al vuelo" en el mismo directorio
                for indice in indices:
                    archivo_original = ruta_indices / f"{indice}.tif"

                    if archivo_original.exists():
                        # Construir nombre final: ej. 230614_b1_4_ndvi.tif
                        nombre_final = f"{fecha}_{bloque_formateado}_{indice.lower()}.tif"
                        archivo_renombrado = ruta_indices / nombre_final

                        # Prevención de errores en Windows si el archivo ya existe de antes
                        if archivo_renombrado.exists():
                            archivo_renombrado.unlink()

                        archivo_original.rename(archivo_renombrado)
                        print(f"[OK] Renombrado a: {nombre_final}")
                    else:
                        print(f"[Aviso] No se encontró el archivo generado para {indice}")

            except Exception as e:
                print(f"[Error] Fallo al procesar {fecha}/{bloque}: {e}")


if __name__ == "__main__":
    procesa_indices(ruta_bandas, ruta_indices, indices_a_calcular)
    print("\nTiempo de procesado total: ", datetime.now() - hora_inicio)
