library(tidyverse)
library(lubridate)
library(ggthemes)


tryCatch({
  datos <- readr::read_csv("datosSalida/alcontar/alcontar.csv")
}, error = function(e) {
  stop("Error: No se pudo encontrar o leer el archivo 'alcontar.csv'. 
       Asegúrate de que esté en tu directorio de trabajo. Detalle: ", e$message)
})


datos_procesados <- datos %>%
  mutate(
    fecha = ymd(fecha)
  )


grafico_final <- ggplot(
  data = datos_procesados,
  aes(
    x = fecha,     # Eje X
    y = r.squared  # Eje Y
  )
) +
  
  # Uso cobertura_ajuste para dar color y agrupar los puntos,
  # ya que hay varias mediciones por fecha y tratamiento.
  geom_point(aes(color = cobertura_ajuste), size = 2, alpha = 0.8) +
  
  # También añado líneas para ver la tendencia.
  # Es crucial agrupar (group) por 'cobertura_ajuste' para que
  # las líneas conecten los puntos correctos.
  geom_line(
    aes(
      color = cobertura_ajuste,
      group = cobertura_ajuste
    ),
    linewidth = 1.2
  ) +
  
  # Subplots
  facet_wrap(~ tratamientos) +
  
  # --- Control de las etiquetas del eje X ---
  # Forzamos a que se muestre una etiqueta para cada fecha única en los datos
  scale_x_date(
    breaks = unique(datos_procesados$fecha),
    date_labels = "%d %b %Y", # Formato: día-mes(abreviado)-año
    limits = c(min(datos_procesados$fecha), NA) # Forzar el inicio del eje en la primera fecha
  ) +
  labs(
    title = bquote("Evolución del" ~ R^2 ~ "por tratamiento de quema y pastoreo"),
    # subtitle = "Subplots por tratamiento de quema y pastoreo",
    x = "Fecha",
    y = bquote("Coeficiente de Determinación ("*R^2*")"),
    color = "Tipo de ajuste" # Título de la leyenda
  ) +
  theme_fivethirtyeight() +
  
  theme(
    # Roto las etiquetas del eje X para que no se solapen
    axis.text.x = element_text(angle = 45, hjust = 1, size = 8),
    # Muevo la leyenda a la parte inferior
    legend.position = "bottom",
    legend.title = element_text(face = "bold", size = 14), # Título de la leyenda
    legend.text = element_text(size = 12),                 # Etiquetas de la leyenda
    # Estilo del texto de la etiqueta del subplot
    strip.text = element_text(face = "bold", size = 12, color = "black"),
    # Estilo del fondo de la etiqueta del subplot
    # strip.background = element_rect(fill = "#2c3e50", color = "black", linewidth = 0.5)
  )

print(grafico_final)

# 7. (Opcional) GUARDAR EL GRÁFICO
# Puedes guardarlo como un archivo PNG o PDF.
# ggsave("evolucion_rsquared_por_tratamiento.png",
#        plot = grafico_final,
#        width = 12,
#        height = 8,
#        dpi = 300)
