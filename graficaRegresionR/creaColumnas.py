import pandas as pd
import os
import glob

ruta_del_directorio = "datosEntrada/dalias/231010/verde_seco"
columna_datos = 'tratamientos_prequema'

# Cojo todos los csv del directorio
patron_busqueda = os.path.join(ruta_del_directorio, "*.csv")

# Creo una lista con todos los csv
lista_csv = glob.glob(patron_busqueda)

# Mensajes de comprobación si no hay archivos
if not lista_csv:
    print(f"No se encontraron archivos .csv en el directorio: {ruta_del_directorio}")
else:
    print(f"Se encontraron {len(lista_csv)} archivos. Procesando...")

    # Ahora itero sobre cada archivo encontrado
    for nombre_archivo in lista_csv:
        # Creo una variable con el nombre del archivo sin ruta de nombre_archivo
        archivo = os.path.basename(nombre_archivo)

        print(f"\nProcesando archivo: {archivo}")
        try:
            # Cargo el archivo CSV
            df = pd.read_csv(nombre_archivo)
            
            # Verifico si la columna necesaria existe
            if columna_datos not in df.columns:
                print(f"  -> Omitido: La columna {columna_datos} no existe en este archivo.")
                continue # Salta al siguiente archivo

            # 1. Creo la columna 'tratamiento_quema'
            df['tratamiento_quema'] = df[columna_datos].str.split('/').str[1].str.strip()

            # 2. Creo la columna 'tratamiento_pastoreo'
            df['tratamiento_pastoreo'] = df[columna_datos].str.split('/').str[2].str.strip()

            # 3. Guardo el DataFrame modificado SOBREESCRIBIENDO el archivo original
            df.to_csv(nombre_archivo, index=False)
            
            print(f"El archivo ha sido actualizado.")

        except pd.errors.EmptyDataError:
            print(f"El archivo {archivo}está vacío.")
        except Exception as e:
            print(f"Error al procesar este archivo: {e}")

    print("\nProceso completado.")