library(ggplot2)
library(readr)
library(stringr)
library(RColorBrewer)

# (El código para definir las rutas de entrada y salida es el mismo)
ruta_fichero_entrada <- "datosSalida/comunidad/20231010/verde/20231010_verde.csv"

# Nombre del fichero sin ruta
nombre_fichero <- basename(ruta_fichero_entrada)

# Nombre del fichero sin extensión
nombre_sin_extension <- sub("\\.csv$", "", nombre_fichero)

# Partes del nombre del fichero separadas por _
partes <- strsplit(nombre_sin_extension, "_")[[1]]

fecha_texto <- partes[1]
tipo_vegetacion <- paste(partes[-1], collapse = "_")  # Tipo de vegetación (verde o verde_seco)

nombre_fichero_salida <- paste0(tipo_vegetacion, "_compara_indices_", fecha_texto, ".png")
ruta_fichero_salida <- file.path("datosSalida", nombre_fichero_salida)

# Formateo la fecha_texto cogida del nombre del archivo para usarla como subtítulo en el gráfico
fecha_date <- as.Date(fecha_texto, format= "%Y%m%d")  # Convierto la variable fecha_texto (texto) a formato fecha_texto (date)
fecha_formateada <- format(fecha_date, format = "%d-%m-%Y")  # Nueva variable de texto con el formato de la fecha_texto

datos <- read_csv(ruta_fichero_entrada)

# Genero 4 colores de la paleta "Dark2" de Color Brewer
paleta <- brewer.pal(n = 4, name = "Dark2")

# Asigno cada color a uno de los índices
colores_finales <- c(
  "ndvi" = paleta[1],
  "evi" = paleta[2],
  "mcari" = paleta[3],
  "endvi" = paleta[4]
)

# Creo la gráfica
grafico_regresion <- ggplot(datos, aes(x = comunidad, y = r.squared, color = indice, group = indice)) +
  geom_line(linewidth = 1) +  # en milímetros
  geom_point(size = 3) +  # en milímetros
  labs(
    title = bquote("Relación entre Índice y "*R^2*" por Comunidad"),
    subtitle = paste("Fecha:", fecha_formateada),
    x = "Índice",
    y = bquote("R-squared ("*R^2*")"),
    color = "Comunidad"
  ) +
  theme_minimal() +
  theme(
    plot.title = element_text(hjust = 0.5, size = 16, face = "bold"),
    axis.title = element_text(size = 12),
    axis.text = element_text(size = 10),
    legend.title = element_text(size = 12),
    legend.text = element_text(size = 10),
    plot.background = element_rect(fill = "white", color = NA)
  ) +
  scale_color_manual(values = colores_finales)  # Paleta de color basada en color brewer: paleta <- brewer.pal(n = 4, name = "Dark2")

# --- Guardado y visualización ---
# ggsave(ruta_fichero_salida, plot = grafico_regresion, width = 10, height = 6, dpi = 300)
print(grafico_regresion)