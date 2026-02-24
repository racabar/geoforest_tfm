library(tidyverse)
library(ggrepel)
library(broom)
library(here)
library(glue)
library(stringr)

#### CONFIGURACIÓN INICIAL ####
setwd(here())

# Experiencia piloto
ep <- "dalias"

# Datos
datos_calculados <- "250519_NDVI_sin_sombras_reclasificado.csv"
datos_campo <- "datos_2025_05_19.csv"

# Nombre de columnas de tratamientos y cobertura
columna_agrupa1 <- "tratamientos"  # Columna de agrupación de subplots
columna_agrupa2 <- "bloque"  # Columna de agrupación de subplots solo si es necesaria
columna_cobertura <- "REC_VEG_VERDE"  # Columna de cobertura en campo (base de datos)

# Datos de entrada
tabla_datos_calculados <- here("datosEntrada", ep, "datos_calculados", datos_calculados)
tabla_datos_campo <- here("datosEntrada", ep, "datos_campo", datos_campo)

# Fecha de vuelo a partir del nombre del archivo de datos calculados
fecha <- as.Date(substr(datos_calculados, 1, 6), format = "%y%m%d")

# Nombre del índice, cogido del nombre del archivo de datos calculados
nombre_indice <- str_split(datos_calculados, "_")[[1]][2]

# crea una variable llamada indice que cuyo valor sea lo que hay entre el primer y el segundo carácter _ del valor de la variable datos_calculados

# Directorio de salida
dir_salida <- here("datosSalida", ep, columna_cobertura)
# Creo el directorio si no existe para evitar errores
if (!dir.exists(dir_salida)) {
  dir.create(dir_salida, recursive = TRUE)
}


#### CARGO Y LIMPIO LOS DATOS ####

# Leo los datos
df_datos_observados <- read_csv(tabla_datos_campo)
df_datos_calculados <- read_csv(tabla_datos_calculados)

# Elimino la columna 'COB_TOTAL' del dataframe 'datos_calculados' si existe
# Para que no se haga un lío con dos columnas del mismo nombre (una de cada tabla)
if("COB_TOTAL" %in% names(df_datos_calculados)) {
  df_datos_calculados <- select(df_datos_calculados, -COB_TOTAL)
  cat("Se ha eliminado la columna 'COB_TOTAL' del dataframe de datos calculados.\n")
}

#### UNO LAS TABLAS ####

# Uno las dos tablas usando la columna en común 'ID_QUADRAT'
# haciendo un inner_join para que se mantengan solo los registros que estén en las dos tablas
df_datos_unidos <- inner_join(df_datos_observados,
                              df_datos_calculados,
                              by = "ID_QUADRAT"
)

#### ANÁLISIS DE REGRESIÓN Y CÁLCULO DE MÉTRICAS ####

# Agrupo los datos por la columna de 'tratamientos' y se aplica un modelo lineal
# a cada grupo. broom::glance() extrae las métricas de cada modelo (R^2, RMSE...)
metricas_regresion <- df_datos_unidos %>%
  nest_by(.data[[columna_agrupa1
]]) %>%  # Agrupa y anida los datos para cada tratamiento
  mutate(modelo = list(lm(
    as.formula(paste0(columna_cobertura, " ~ cobertura_calculada")), data = data))) %>%  # Crea el modelo para cada set de datos anidado
  summarise(glance(modelo)) %>%  # Aplica glance a cada modelo y extrae las métricas
  ungroup() %>%  # Desagrupa el resultado final
  select(  # Selecciono y renombro las métricas de interés (como ya tenías)
    all_of(columna_agrupa1
  ),
    r.squared,
    r2_ajustado = adj.r.squared,
    rmse = sigma, 
    p_valor = p.value
  )

# Se imprimen las métricas en la consola
print("Métricas de la regresión por tratamiento:")
print(as.data.frame(metricas_regresion))


#### CREACIÓN DEL GRÁFICO ####

# Preparo las etiquetas de texto con las métricas para añadirlas al gráfico
etiquetas_metricas <- metricas_regresion %>%
  mutate(
    etiqueta = paste0(
      "R² = ", round(r.squared, 2), "\n",
      "RMSE = ",
      round(rmse, 2), "%"
    )
  )

# Añado las etiquetas al data frame principal para usarlas en el gráfico
datos_grafico <- left_join(df_datos_unidos, etiquetas_metricas, by = columna_agrupa1)

# Creo el gráfico
grafico_regresion <- ggplot(
  datos_grafico,
  aes(
    x = cobertura_calculada,
    y = .data[[columna_cobertura]],
    color = .data[[columna_agrupa1
  ]]
    )
  ) +
  
  # Nube de puntos
  geom_point(alpha = 0.8, size = 2) +
  
  # Línea de regresión lineal (lm) con intervalo de confianza del 95% (valor por defecto de geom_smooth)
  geom_smooth(
    method = "lm",
    se = TRUE,
    aes(fill = .data[[columna_agrupa1
  ]]),
    alpha = 0.1
  ) +
  
  # Etiquetas de texto para cada punto (ID_QUADRAT), con ggrepel para evitar solapamientos
  geom_text_repel(
    aes(label = ID_QUADRAT),
    size = 3,
    show.legend = FALSE,
    max.overlaps = Inf  # Fuerza a mostrar todas las etiquetas

  ) +
  
  # Añado las métricas R² y RMSE en cada subplot
  geom_text(
    aes(x = -Inf, y = Inf, label = etiqueta),
    hjust = -0.1, # Justificación horizontal (cerca del borde izquierdo)
    vjust = 1.5,  # Justificación vertical (debajo del borde superior)
    size = 4,
    check_overlap = TRUE # Evita que se escriban una encima de otra
  ) +
  
  # Separo el gráfico en subplots, uno por cada 'tratamiento'
  facet_wrap(
    vars(.data[[columna_agrupa1]]),
    # Esto hace que el eje Y tenga la misma escala en todos los subplots
    # Para que tengan escalas diferentes dejar free
    # Para que se mantenga solo la escala de x hay que usar free_y
    # Para que los dos ejes tengan la misma escala en todos los subplots hay que usar fixed
     scales = "free_x",
      ncol = 2
    ) +
  
  # Defino los títulos, etiquetas y tema del gráfico
  labs(
    title = glue("Cobertura Observada vs. Calculada: {nombre_indice}"),
    subtitle = glue("Fecha: {fecha}"),
    x = "Cobertura Calculada (%)",
    y = paste0("Cobertura Observada (", columna_cobertura, ", %)"),
    color = "Tratamiento",
    fill = "Intervalo de Confianza 95%"
  ) +
  theme_minimal() + # Un tema limpio para el gráfico
  
  # En estas tres líneas se eliminan las líneas de fondo de la cuadrícula
  theme(
    plot.title = element_text(size = 20, face = "bold"),  # Fuente del título del gráfico
    plot.subtitle = element_text(size = 16),  # Fuente del subtítulo del gráfico
    strip.text = element_text(size = 12),  # Fuente del título de los subplots
    panel.grid.major = element_blank(),  # Suprime las líneas de cuadrícula
    panel.grid.minor = element_blank(),  # Suprime las líneas de cuadrícula
    legend.position = "bottom",  # Posición de la leyenda
    panel.border = element_rect(color = "black", fill = NA, linewidth = 1), # Añade un borde a los subplots
    axis.ticks = element_line(color = "black") # Muestra las marcas (ticks) en los ejes
  )

# Muestro el gráfico
print(grafico_regresion)

#### GUARDO LOS RESULTADOS ####

# # Creo un nombre de fichero base único basado en la fecha y hora
# timestamp <- format(Sys.time(), "%Y%m%d_%H%M")
# nombre_base_fichero <- glue("regresion_cobertura_{timestamp}")

# Creo un nombre de fichero base a partir de la ruta de los datos
# Se coge el nombre del directorio padre 2 niveles por encima del fichero de datos calculados (fecha de muestreo)
# y el nombre del fichero de datos calculados sin extensión
dir_name_fecha <- basename(dirname(dirname(tabla_datos_calculados)))  # Fecha de muestreo (directorio 2 niveles superior)
dir_name_metodo_calculo <- basename(dirname(tabla_datos_calculados))  # Método de cálculo (verde / verde_seco) (directorio 1 nivel superior)
nombre_base_fichero <- glue("regresion_cobertura_{dir_name_fecha}_{nombre_indice}_{dir_name_metodo_calculo}")

# Guardo el gráfico y las métricas usando here() para asegurar la ruta correcta
ggsave(
  filename = here(dir_salida, glue("{nombre_base_fichero}_{fecha}.png")),
  plot = grafico_regresion,
  width = 12, height = 8, dpi = 300, bg = "white"
)

# MODIFICACIÓN: Añado la columna 'indice' con el valor de la variable nombre_indice
metricas_regresion <- metricas_regresion %>%
  mutate(indice = nombre_indice)

write_csv(
  metricas_regresion,
  file = here(dir_salida, glue("{nombre_base_fichero}_metricas_{fecha}.csv"))
)

cat(glue("\n\nANÁLISIS COMPLETADO\n\nEl gráfico y las métricas se han guardado en la carpeta '{dir_salida}'\n"))