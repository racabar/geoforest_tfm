import os
import re
from datetime import datetime
import matplotlib.pyplot as plt
import statsmodels.api as sm
from sklearn.metrics import mean_squared_error
from adjustText import adjust_text
import pandas as pd
import numpy as np


def regresion_por_categoria(df, archivo_figura, indice, col_x, col_y, unidades, calculo, tratamiento, rutametricas, regresion='1', mostrar_figura=False):
    metricas_regresion = pd.DataFrame({
        'indice': pd.Series(dtype='string'),
        'categoria': pd.Series(dtype='string'),
        'r2': pd.Series(dtype='float'),
        'mse': pd.Series(dtype='float'),
        'rmse': pd.Series(dtype='float')
    })

    categorias = df[tratamiento].unique()
    num_categorias = len(categorias)

    # Crear subplots según el número de categorías
    # Defino el número de columnas
    num_columnas = 2
    # Calculo el número de filas necesario
    num_filas = (num_categorias + num_columnas - 1) // num_columnas

    # Organizo los subplots en 2 columnas
    fig, axes = plt.subplots(
        nrows=num_filas,
        ncols=num_columnas,
        figsize=(20, 6 * num_categorias),
        sharex=False,
    )

    # Si solo hay una categoría, ajustar `axes` para que sea iterable
    if num_categorias == 1:
        axes = np.array([axes])
    # Aplano el array de ejes para facilitar la iteración
    axes = axes.flatten()

    # En la columna quema de pyriclabsquadrats
    # colores = {
    #     'Control': 'blue',
    #     'Quema': 'red'
    # }

    # En la columna tratamiento de pyriclabsquadrats
    # Usar verde por ejemplo si se usa otra categoría. Otras opciones: morado o naranja
    colores = {
        'Control': 'blue',
        'Quema - Pastoreo': 'red',
        'Quema - Excluido': 'green',
        'Prequema': 'blue',
        'Control / No pastoreo': 'blue',  # A partir de aquí los clores para Dalías
        'Control / Pastoreo': 'red',
        'Quema otoño / Pastoreo': 'green',
        'Quema otoño / No pastoreo': 'orange',
        'Quema primavera / No pastoreo': 'cyan',
        'Quema primavera / Pastoreo': 'purple'
    }

    for ax, (categoria, df_categoria) in zip(axes, df.groupby(tratamiento)):
        # Ordenar valores
        df_categoria = df_categoria.sort_values(col_x)
        x = df_categoria[col_x]
        y = df_categoria[col_y]

        # Tipo de regresión
        if regresion == '1':
            nombre_regresion = 'lineal'
            x_const = sm.add_constant(x)
        elif regresion == '2':
            nombre_regresion = 'logarítmica'
            x_log = np.log(x)
            x_const = sm.add_constant(x_log)
        elif regresion == '3':
            nombre_regresion = 'polinómica de grado 2'
            x_poly = np.column_stack((x, x ** 2))
            x_const = sm.add_constant(x_poly)
        elif regresion == '4':
            nombre_regresion = 'exponencial'
            y_log = np.log(y)
            x_const = sm.add_constant(x)
            y = y_log
        elif regresion == '5':
            nombre_regresion = 'potencial'
            x_log = np.log(x)
            y_log = np.log(y)
            x_const = sm.add_constant(x_log)
            y = y_log

        # Ajustar modelo
        model = sm.OLS(y, x_const).fit()
        predictions = model.predict(x_const)

        # #Filtro los NaN de y y de predictions
        # if len(y_clean) == 0 or len(predictions_clean) == 0:
        #     print(f"ADVERTENCIA: Se encontraron valores NaN en los datos de entrada de la regresión. Estos serán ignorados en el cálculo de métricas.")
        # mask = ~np.isnan(y) & ~np.isnan(predictions)
        # y_clean = y[mask]
        # predictions_clean = predictions[mask]

        # Calculo métricas del modelo
        mse = mean_squared_error(y, predictions)
        rmse = np.sqrt(mse)
        r2 = model.rsquared

        # Creo un diccionario de valores a añadir a metricas_regresion
        valores_regresion = {
            'indice': indice,
            'categoria': categoria,
            'r2': r2,
            'mse': mse,
            'rmse': rmse
        }

        # Añado las métricas al dataframe metricas regresion
        metricas_regresion = pd.concat([metricas_regresion, pd.DataFrame([valores_regresion])], ignore_index=True)

        # Obtengo pendiente y ordenada al origen para mostrar la recta de regresión
        # intercepto, pendiente = model.params

        print(f"\nRESULTADOS PARA {categoria.upper()}:")
        print(model.summary())
        # print(f"\nMSE: {mse}, \nRMSE: {rmse}, \nR²: {r2}, \nRecta de regresión: y = {pendiente:.2f}x + {intercepto:.2f}")

        # Creo el gráfico en el subplot correspondiente
        ax.scatter(x, y, label=f'Datos observados', color=colores[categoria])
        ax.plot(x, predictions, label=f'Regresión', color=colores[categoria])

        # Etiquetas R² y RMSE en el gráfico
        ax.text(
            0.01,
            0.85,
            f'R² = {round(r2, 2)}\nRMSE = {round(rmse, 2)} {unidades}',
            # f'R² = {round(r2, 2)}\nRMSE = {round(rmse, 2)} m³/ha\nRecta de regresión: y = {pendiente:.2f}x + {intercepto:.2f}',
            transform=ax.transAxes,
            fontsize=12,
            ha='left',
            color=colores[categoria]
        )

        # Intervalo de confianza
        intervalo_confianza = model.get_prediction(x_const).conf_int(alpha=0.05)
        ax.fill_between(
            x,
            intervalo_confianza[:, 0],
            intervalo_confianza[:, 1],
            color=colores[categoria],
            alpha=0.2,
            label=f'IC 95%'
        )

        # Etiquetas de puntos
        texts = [
            ax.text(
                row[col_x] + 0.5,
                row[col_y] + 0.5,
                int(row['ID_QUADRAT']),
                fontsize=8,
                ha='right',
                color=colores[categoria]
            )
            for _, row in df_categoria.iterrows()
        ]
        adjust_text(texts, ax=ax)

        # Etiquetas específicas para cada subplot
        ax.set_title(f'Regresión {nombre_regresion} {calculo}: {categoria} ({indice.upper()})')
        ax.set_xlabel(f'Datos calculados ({unidades})')
        ax.set_ylabel(f'Datos observados ({unidades})')
        ax.legend(loc='lower right')
    # Oculto los ejes no usados si el número de categorías es impar
    for i in range(num_categorias, num_filas * num_columnas):
        fig.delaxes(axes[i])

    plt.tight_layout()

    # Si se está ejecutando como módulo, se guarda la figura
    if not mostrar_figura:
        plt.savefig(archivo_figura.replace('tif', 'png'))
    # Si se está ejecutando directamente, se muestra la figura
    else:
        plt.show()

    # Guardo el dataframe con las métricas de la regresión
    # Luego se pueden unir todos los dataframes con el script concatenar_csv.py
    # metricas_regresion.to_csv(f'salidas/rasters_clasificados/metricas_regresion/{indice}_metricas_REGRESION.csv', sep=';', index=False)
    metricas_regresion.to_csv(os.path.join(rutametricas, f'{indice}_metricas_REGRESION.csv'), index=False)


# Esto solo se usa si se ejecuta el script directamente a mano
if __name__ == "__main__":
    # input_file = 'salidas/rasters_clasificados/20250120-1359_MCARI_reclasificado.csv'
    # columna_x = 'cobertura'
    # columna_y = 'COB_TOTAL'
    input_file = '../salidas/dalias/250523/B1-4/verde_COB_TOTAL/20250908-1243_EVI_sin_sombras_reclasificado.csv'
    columna_x = 'cobertura_calculada'
    columna_y = 'COB_TOTAL'
    # Cojo el nombre del archivo de input_file
    nombre_archivo = os.path.basename(input_file)
    # y me quedo solo con el nombre del índice
    nombre_indice = re.search(r'_(.*?).', nombre_archivo).group(1)

    unidades_cobertura = '%'

    # Pregunta qué regresión se va a hacer
    pregunta_regresion = '¿Qué regresión quieres aplicar? \n  1: Lineal \n  2: Logarítmica \n  3: Polinómica de grado 2 \n  4: Exponencial \n  5: Potencial \n  c: Cancelar \nRespuesta (1): '
    regresion = input(pregunta_regresion)
    while regresion.lower() not in ['1', '2', '3', '4', '5', '']:
        print('Por favor, selecciona "1", "2", "3", "4" o "5".')
        regresion = input(pregunta_regresion)

    if regresion.lower() == 'c':
        print('Has detenido el script')
        exit()

    # La respuesta por defecto es 1
    if regresion == '':
        regresion = '1'

    # Pregunta si se quieren quitar los outliers
    pregunta_menu = '¿Quieres quitar los outliers? \n  1: No \n  2: Sí \n  c: Cancelar\nRespuesta (1): '
    outliers = input(pregunta_menu)
    while outliers.lower() not in ['1', '2', 'c', '']:
        print('Por favor, selecciona "1", "2" o "c".')
        outliers = input(pregunta_menu)

    if outliers.lower() == 'c':
        print('Has detenido el script')
        exit()

    df_unidos = pd.read_csv(input_file)

    if outliers == '2':
        quadrats_outliers = input('Introduce los quadrats a obviar separados por comas: ')
        df_unidos = df_unidos.query(f'ID_QUADRAT not in [{quadrats_outliers}]')  # Cobertura: 3, 54

    regresion_por_categoria(df_unidos, input_file, nombre_indice, columna_x, columna_y, unidades_cobertura, 'cobertura', 'tratamientos_quema_primavera', 'salidas/alcontar/241120/cobertura/COB_TOTAL_verde_seco/metricas_regresion', regresion, mostrar_figura=True)
