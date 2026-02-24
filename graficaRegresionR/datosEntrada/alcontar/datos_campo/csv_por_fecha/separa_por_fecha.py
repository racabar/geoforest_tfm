import pandas as pd
import os

# --- Configuración ---
archivo_entrada = 'datosEdatosEntrada/alcontar/cobertura_db/csv_por_fecha/PARAMETROS_PARA_COMPARACION_DRON.csv'
columna_fecha = 'FECHA_MUESTREOS'
columna_filtro = 'TRAT_QUEMA'
valor_a_excluir = 'Biomasa'
directorio_salida = 'datosEntrada/alcontar/cobertura_db'

# --- Lógica del Script ---

def particionar_csv_por_fecha(archivo_entrada, columna_fecha, columna_filtro, valor_a_excluir, directorio_salida):
    """
    Lee un CSV, filtra registros no deseados, y guarda nuevos CSVs
    por cada fecha única en la columna especificada.
    """
    
    # 1. Buena práctica: Crear el directorio de salida si no existe
    # os.makedirs con exist_ok=True es idempotente (no falla si ya existe)
    try:
        os.makedirs(directorio_salida, exist_ok=True)
        print(f"Directorio de salida verificado/creado: '{directorio_salida}'")
    except OSError as e:
        print(f"Error crítico al crear el directorio: {e}")
        return

    # 2. Cargar los datos
    try:
        df = pd.read_csv(archivo_entrada)
        print(f"Archivo '{archivo_entrada}' cargado exitosamente.")
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo '{archivo_entrada}'. Asegúrate de que esté en el mismo directorio.")
        return
    except Exception as e:
        print(f"Error al leer el archivo CSV: {e}")
        return

    # 3. Aplicar el filtro (Metodología clave)
    # Usamos indexación booleana. Es la forma vectorizada y más eficiente en Pandas.
    df_filtrado = df[df[columna_filtro] != valor_a_excluir].copy()
    
    if df_filtrado.empty:
        print(f"Advertencia: El DataFrame está vacío después de excluir '{valor_a_excluir}'. No se generarán archivos.")
        return
        
    print(f"Datos filtrados. Se excluyeron los registros con '{columna_filtro}' == '{valor_a_excluir}'.")

    # 4. Obtener las fechas únicas
    fechas_unicas = df_filtrado[columna_fecha].unique()
    print(f"Se encontraron {len(fechas_unicas)} fechas únicas para procesar.")

    # 5. Iterar y guardar los archivos
    archivos_generados = 0
    for fecha in fechas_unicas:
        # Seleccionar el subconjunto de datos para la fecha actual
        df_fecha = df_filtrado[df_filtrado[columna_fecha] == fecha]
        
        # Construir un nombre de archivo limpio
        # (La fecha YYYY-MM-DD es segura, pero podríamos añadir limpieza si fueran formatos complejos)
        nombre_archivo = f"datos_{fecha}.csv"
        
        # Usar os.path.join para compatibilidad entre sistemas operativos (Windows/Linux/Mac)
        ruta_salida = os.path.join(directorio_salida, nombre_archivo)
        
        try:
            # Guardar el CSV. 
            # index=False es crucial para no incluir el índice de Pandas como una columna.
            df_fecha.to_csv(ruta_salida, index=False, encoding='utf-8')
            print(f" -> Guardado: {ruta_salida} ({len(df_fecha)} filas)")
            archivos_generados += 1
        except Exception as e:
            print(f"Error al guardar el archivo {ruta_salida}: {e}")

    print(f"\nProceso completado. Se generaron {archivos_generados} archivos CSV.")

# --- Ejecutar la función ---
if __name__ == "__main__":
    particionar_csv_por_fecha(
        archivo_entrada, 
        columna_fecha, 
        columna_filtro, 
        valor_a_excluir, 
        directorio_salida
    )