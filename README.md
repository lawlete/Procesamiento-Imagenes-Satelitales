# Análisis NDVI - Múltiples Waypoints

Este script en Python utiliza Google Earth Engine (GEE) para extraer y analizar series temporales del Índice de Vegetación de Diferencia Normalizada (NDVI) a partir de imágenes satelitales Sentinel-2 para puntos geográficos específicos (Waypoints).

## Características principales

*   **Extracción de datos satelitales:** Consulta la colección `COPERNICUS/S2_SR_HARMONIZED` de Sentinel-2 dentro de un rango de fechas.
*   **Procesamiento de imágenes:** Aplica automáticamente máscaras de nubes y cirros utilizando la banda `QA60` y calcula el NDVI utilizando las bandas B8 (NIR) y B4 (Red).
*   **Análisis estadístico:** Calcula el NDVI promedio, máximo, mínimo y la mediana para la serie de tiempo válida de cada punto analizado.
*   **Exportación de datos:** Genera automáticamente dos archivos CSV por cada análisis:
    *   `*_serie.csv`: Contiene la serie temporal completa con fechas y valores de NDVI válidos.
    *   `*_resumen.csv`: Contiene las estadísticas consolidadas del análisis.
*   **Ejecución continua:** Permite analizar múltiples waypoints consecutivamente sin tener que reiniciar el script ni volver a inicializar/autenticar Earth Engine.

## Requisitos previos

*   Python 3.x
*   Credenciales y cuenta activa en Google Earth Engine.
*   Librerías de Python:
    *   `earthengine-api` (para interactuar con GEE)
    *   `numpy` (para el cálculo de percentiles/mediana)

Puedes instalar los requerimientos con:
```bash
pip install earthengine-api numpy
```

## Uso

1. Ejecuta el script:
   ```bash
   python analisis_ndvi_mul.py
   ```
2. La consola te pedirá ingresar los datos para el análisis. Puedes presionar `Enter` para usar los valores por defecto o ingresar tus propios valores:
   *   Latitud
   *   Longitud
   *   Fecha de inicio (YYYY-MM-DD)
   *   Fecha de fin (YYYY-MM-DD)
3. Los resultados se guardarán en tu escritorio dentro de la carpeta `imagenes_satelitales/analisis_ndvi_multiple`.
4. El programa te preguntará si deseas analizar otro punto al finalizar cada ejecución.

## Notas

* El proyecto configurado por defecto para GEE es `imagenes-satelitales-490002`. Asegúrate de tener acceso o modificarlo en la función `inicializar_ee()`.
* Si es la primera vez que ejecutas procesos de Earth Engine en tu entorno, puede que se abra una ventana del navegador para solicitar tu autenticación de Google.
