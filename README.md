# TFM

## 26/02/2026 Cálculo y comparativa de índices

1. He calculado 6 índices usando spyndex y las bandas de la Micasense (p01_calcula_indices.py)

   - NDVI: típico como referencia
   - GNDVI: usa el verde
   - NDRE: usa también el NIR
   - OSAVI: índice de suelo
   - MSAVI: índice de suelo
   - MCARI2: absorción de clorofila

2. He hecho mosaicos para todas las fechas porque las bandas están separadas por bloques (02_mosaico_indices.py)

   - B1-4
   - B2-3

3. He calculado el histograma de cada índice (03_histograma_indices.py).

    - Están en: [entradas/dalias/indices/histogramas](entradas/indices/histogramas)

4. He hecho una comparación de todos los índices para todas las fechas (04_compara_indices.py)

    - [Comparación de índices](entradas/indices/histogramas/comparacion_indices_todos.png)

5. He hecho dos pruebas con Otsu usando (modulos.clasifica_imagen_otsu.py) con NDVI y con 2 y 3 clusters

   - 2 clusters: a simple vista no ha quedado muy bien
   - 3 clusters: se parece bastante al resultado del punto 8

6. He hecho una matriz de correlación (matriz_correlacion_indices.py) entre los 6 índices y he obtenido esto.

```
Matriz de correlación de Pearson
índice  ndvi   gndvi  ndre   msavi  osavi  mcari2
ndvi    1.000  0.932  0.972  0.834  0.941   0.923
gndvi   0.932  1.000  0.920  0.747  0.858   0.811
ndre    0.972  0.920  1.000  0.802  0.908   0.892
msavi   0.834  0.747  0.802  1.000  0.964   0.966
osavi   0.941  0.858  0.908  0.964  1.000   0.987
mcari2  0.923  0.811  0.892  0.966  0.987   1.000
```

7. He hecho una clasificación usando K-Means y un stack de los 2 índices que tenían menos correlación, pero había zonas donde vegetación verde las clasificaba como suelo

   - NDVI: por tomarlo como referencia
   - MSAVI: se diferencia 0,834 con NDVI y 0,747 con GNDVI

8. He añadido GNDVI al stack de índices por añadir la banda del verde y parece que se ajusta mejor (ver QGIS)

## 12/03/2026

1. He calculado el índice TVI2 con la ecuación del artículo de Jorge

$$
TVI2 = 0.5 \cdot (120 \cdot (NIR-G)-200 \cdot (R-G))
$$

2. He hecho la comparación por fechas del [índice TVI2](entradas/indices/histogramas/comparaciones/indices/comparacion_indices_TVI2.png)

3. He calculado la matriz de correlación de todos los índices incluyendno el TVI2.
    - Si cojo como referencia el NDVI los índices que menos correlación tienen son
        - msavi: 0.834
        - tvi2:  0.870
    - Si cojo como referencia TVI2 los índices de menos correlación son
        - ndvi:  0.870
        - gndvi: 0.766
        - ndre:  0.841

```
         ndvi  gndvi   ndre  msavi  osavi  mcari2   tvi2
ndvi    1.000  0.932  0.972  0.834  0.941   0.923  0.870
gndvi   0.932  1.000  0.920  0.747  0.858   0.811  0.766
ndre    0.972  0.920  1.000  0.802  0.908   0.892  0.841
msavi   0.834  0.747  0.802  1.000  0.964   0.966  0.984
osavi   0.941  0.858  0.908  0.964  1.000   0.987  0.972
mcari2  0.923  0.811  0.892  0.966  0.987   1.000  0.985
tvi2    0.870  0.766  0.841  0.984  0.972   0.985  1.000
```

4. He hecho la clasificación con Otsu para NDVI y TVI2

5. He reclasificado los resultados de Otsu en dos clases

    - 1: vegetación
    - 0: no vegetación