# Propuesta de Refactorización: Script de Análisis NDVI

Este documento detalla los puntos clave para refactorizar y mejorar el script `analisis_ndvi_mul.py`. El objetivo principal es optimizar el rendimiento (específicamente la comunicación con Google Earth Engine), mejorar la legibilidad del código y hacerlo más robusto para futuros cambios.

## 1. Optimización en la Comunicación con Google Earth Engine (Core)

**Problema Actual:**
El script actual utiliza un bucle `for` de Python para iterar sobre cada imagen de la colección satelital y llama a `.getInfo()` en cada iteración. `.getInfo()` es una operación sincrónica que transfiere datos desde los servidores de Google a la máquina local (Python). Hacer esto dentro de un bucle significa que por cada imagen se realiza una petición HTTP independiente, lo cual es ineficiente y muy lento para series temporales largas.

**Solución Propuesta:**
Trasladar todo el procesamiento al servidor de Google Earth Engine (Server-Side).
*   Utilizar `.map()` sobre la `ImageCollection` para calcular el NDVI y extraer el valor del punto para todas las imágenes de una sola vez.
*   Retornar una `FeatureCollection` desde GEE con las fechas y los valores de NDVI.
*   Realizar un **único** `.getInfo()` al final para traer la tabla de resultados a Python. Esto reducirá el tiempo de ejecución de minutos a apenas un par de segundos por waypoint.

## 2. Incorporación de Pandas para Análisis y Exportación de Datos

**Problema Actual:**
Se mezclan múltiples librerías (`csv`, `statistics`, `numpy`) y manipulaciones manuales de listas y diccionarios para calcular estadísticas (promedio, máximo, mínimo, mediana) y guardar los datos.

**Solución Propuesta:**
Utilizar la librería `pandas`.
*   Convertir el resultado de GEE directamente en un `DataFrame` de Pandas.
*   Aprovechar los métodos integrados de Pandas (`.mean()`, `.min()`, `.max()`, `.median()`) que están altamente optimizados.
*   Guardar los archivos usando el método `.to_csv()` de Pandas, lo que elimina la necesidad de manejar manualmente la escritura de filas y encabezados con el módulo `csv`.

## 3. Modularización (Separation of Concerns)

**Problema Actual:**
La función `analizar_waypoint` es una función monolítica (hace demasiadas cosas a la vez): consulta a GEE, procesa errores, calcula estadísticas y escribe archivos en disco.

**Solución Propuesta:**
Dividir la lógica en funciones más pequeñas con responsabilidades únicas:
*   `obtener_serie_ndvi_gee(lat, lon, fecha_ini, fecha_fin)`: Se encarga exclusivamente de interactuar con GEE y retornar los datos crudos.
*   `calcular_estadisticas_ndvi(df)`: Toma los datos (DataFrame) y retorna el diccionario con el resumen estadístico.
*   `guardar_resultados(df, estadisticas, carpeta, nombre_base)`: Se encarga exclusivamente de las operaciones de entrada/salida (guardar los CSV).

## 4. Gestión Segura de Directorios

**Problema Actual:**
El script intenta guardar archivos en la ruta `Desktop\imagenes_satelitales\analisis_ndvi_multiple`. Si esta carpeta no existe previamente en la computadora del usuario, el script fallará al intentar crear los archivos `.csv`.

**Solución Propuesta:**
Agregar una validación automática de la existencia del directorio antes de escribir usando la librería estándar `os` o `pathlib`:
```python
os.makedirs(carpeta_salida, exist_ok=True)
```

## 5. Gestión de Configuraciones y "Magic Strings"

**Problema Actual:**
Existen valores "quemados" en el código (hardcoded), como el ID del proyecto de GEE (`'imagenes-satelitales-490002'`), o las rutas de las carpetas a la mitad del script.

**Solución Propuesta:**
Mover todas estas configuraciones al inicio del script como constantes globales (en mayúsculas) o utilizar un archivo de configuración (ej. `.env`). Esto facilita que cualquier usuario modifique el script sin tener que hurgar en la lógica interna del código.
