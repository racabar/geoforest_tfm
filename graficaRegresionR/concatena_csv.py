import os
import pandas as pd
import glob

ajuste_cobertura = "REC_VEG_VERDE"
rutabase = os.path.join("datosSalida/alcontar", ajuste_cobertura)
# Ruta donde están tus archivos CSV
ruta_archivos = os.path.join(rutabase, "*.csv")
lista_csv = glob.glob(ruta_archivos)

dataframes_procesados = []

for archivo_path in lista_csv:
    try:
        df = pd.read_csv(archivo_path)

        # Filtro para quitar los que están vacíos o tienen todas las columnas como NA
        if not df.empty and not df.isna().all().all():
            # Extraer el nombre del archivo sin extensión
            nombre_base = os.path.splitext(os.path.basename(archivo_path))[0]
            # Extraer la fecha (últimos 10 caracteres del nombre base)
            fecha = nombre_base[-10:]
            
            # Añadir la columna "fecha"
            df["fecha"] = fecha
            dataframes_procesados.append(df)
    except Exception as e:
        print(f"Error procesando el archivo {archivo_path}: {e}")

# Concatenar todos los dataframes en uno solo
df_concatenado = pd.concat(dataframes_procesados, ignore_index=True)

# Añadir la columna "cobertura_ajuste" con el nombre base del directorio
valor_cobertura_ajuste = os.path.basename(rutabase)
df_concatenado["cobertura_ajuste"] = valor_cobertura_ajuste

# --- Lógica para concatenar o crear el archivo de salida ---
nombre_archivo_salida_relativo = "../alcontar.csv"
ruta_archivo_salida = os.path.join(rutabase, nombre_archivo_salida_relativo)

# Normalizar la ruta para asegurar que sea correcta (ej. maneja '..')
ruta_archivo_salida = os.path.normpath(ruta_archivo_salida)

if os.path.exists(ruta_archivo_salida):
    print(f"El archivo de salida ya existe en '{ruta_archivo_salida}'. Se añadirán los nuevos datos.")
    # Leer el archivo existente
    df_existente = pd.read_csv(ruta_archivo_salida)
    # Combinar el dataframe existente con el nuevo
    df_final = pd.concat([df_existente, df_concatenado], ignore_index=True)
    # Opcional: eliminar duplicados por si se procesan los mismos archivos otra vez
    df_final.drop_duplicates(inplace=True)
    print(f"Datos añadidos. El archivo ahora tiene {len(df_final)} filas.")
else:
    print(f"Creando nuevo archivo de salida en '{ruta_archivo_salida}'.")
    df_final = df_concatenado

# Guardar el DataFrame final (sea nuevo o combinado)
df_final.to_csv(ruta_archivo_salida, index=False)
print(f"Proceso completado. Archivo guardado en {ruta_archivo_salida}")
