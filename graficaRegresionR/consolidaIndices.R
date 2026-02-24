# Cargar las librerías necesarias del Tidyverse
library(dplyr)
library(tidyr)
library(readr)
library(stringr)
library(purrr)

# --- 1. Configuración de Rutas ---
# Define el directorio donde están tus archivos CSV
directorio_entrada <- "datosSalida"

# Define el directorio donde quieres guardar los archivos combinados
directorio_salida <- "datosSalida/indicesUnidos"

# Creamos el directorio de salida si no existe
dir.create(directorio_salida, showWarnings = FALSE, recursive = TRUE)

# --- 2. Definición del Patrón (Regex) ---
# Este regex buscará archivos que coincidan con tu estructura y capturará la fecha y el índice.
# ^(inicio) ... (\d{6})_(.*?)_verde_seco_metricas\.csv$
# Grupo 1: (\d{6})       -> Captura los 6 dígitos de la fecha (ej. 231010)
# Grupo 2: (.*?)         -> Captura "cualquier cosa" (sin ser 'greedy') entre el guion bajo de la fecha
#                          y el guion bajo de "_verde_seco...". Esto es el ÍNDICE (ej. ndvi)
patron_regex <- "^regresion_cobertura_(\\d{6})_(.*?)_verde_seco_metricas\\.csv$"
print(patron_regex)


# --- 3. Listar, Agrupar y Procesar Archivos ---

# Usamos un pipeline de Tidyverse para todo el proceso:
archivos_procesados <- tibble(
  # Obtenemos solo el nombre del archivo (sin la ruta completa)
  filename = list.files(directorio_entrada, full.names = FALSE)
) %>%
  # Filtramos solo los archivos que coinciden EXACTAMENTE con nuestro patrón regex
  filter(str_detect(filename, patron_regex)) %>%
  # Extraemos los grupos de captura del regex
  mutate(
    matches = str_match(filename, patron_regex),
    fecha = matches[, 2],  # El segundo elemento capturado (Grupo 1)
    indice = matches[, 3], # El tercer elemento capturado (Grupo 2)
    # Reconstruimos la ruta completa al archivo original
    ruta_completa = file.path(directorio_entrada, filename)
  ) %>%
  # Seleccionamos solo las columnas que necesitamos
  select(ruta_completa, fecha, indice) %>%
  
  # --- Agrupación clave ---
  # Agrupamos por el 'indice' extraído
  group_by(indice) %>%
  # "Anidamos" los datos: esto crea un data.frame donde cada 'indice' tiene
  # una columna "data" que es un tibble con TODAS sus fechas y rutas
  nest() %>%
  
  # --- 4. Lectura y Combinación ---
  mutate(
    # Creamos una nueva columna "df_combinado"
    # Usamos map() para iterar sobre la columna "data" (los tibbles anidados)
    df_combinado = map(data, function(df_anidado) {
      
      # Dentro de CADA grupo de índice:
      # Usamos map2_dfr para iterar sobre dos columnas a la vez:
      # .x = df_anidado$ruta_completa
      # .y = df_anidado$fecha
      # y "_dfr" significa que unirá los resultados por filas (como rbind)
      map2_dfr(df_anidado$ruta_completa, df_anidado$fecha, function(path_csv, fecha_csv) {
        
        # Leemos el CSV. Usamos col_types para asegurar que todo se lea como caracter
        # y evitar errores al unir CSVs que puedan tener tipos de columna diferentes.
        read_csv(path_csv, col_types = cols(.default = "c")) %>%
          # ¡Añadimos la columna de fecha que extrajimos del nombre del archivo!
          mutate(fecha_adquisicion = format(as.Date(fecha_csv, format = "%y%m%d"), "%Y-%m-%d"))
      })
    })
  )

# --- 5. Guardar Archivos Consolidados ---

# Ahora tenemos un dataframe (archivos_procesados) que contiene el 'indice'
# y el 'df_combinado' (el dataframe gigante ya unido).

# Usamos pwalk (parallel walk) para iterar sobre las filas del resultado
# y ejecutar una función (guardar el archivo).
pwalk(
  list(
    indice_out = archivos_procesados$indice,
    datos_out = archivos_procesados$df_combinado
  ),
  function(indice_out, datos_out) {
    # Creamos el nombre del archivo de salida
    nombre_salida <- file.path(directorio_salida, paste0("consolidado_total_", indice_out, ".csv"))
    
    # Escribimos el dataframe combinado en el nuevo CSV
    write_csv(datos_out, nombre_salida)
    
    print(paste("Creado archivo consolidado para el índice:", indice_out, "en", nombre_salida))
  }
)

print("--- Proceso completado ---")
