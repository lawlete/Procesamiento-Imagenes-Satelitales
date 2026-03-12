# Análisis NDVI - Múltiples Waypoints (v2)

Este script en Python utiliza Google Earth Engine (GEE) para extraer y analizar series temporales del Índice de Vegetación de Diferencia Normalizada (NDVI) a partir de imágenes satelitales Sentinel-2 para puntos geográficos específicos (Waypoints). Esta versión está optimizada, calculando en el servidor de Google para una mayor velocidad y usando Pandas para el manejo de datos.

## Características principales

*   **Extracción de datos satelitales optimizada:** Consulta la colección `COPERNICUS/S2_SR_HARMONIZED` y precalcula los valores en el servidor (Server-Side) para evadir las lentas llamadas de red en bucle.
*   **Procesamiento de imágenes:** Aplica automáticamente máscaras de nubes y cirros utilizando la banda `QA60` y calcula el NDVI combinando las bandas B8 (NIR) y B4 (Red).
*   **Análisis estadístico mejorado:** Mediante `Pandas`, calcula el NDVI promedio, máximo, mínimo y la mediana para la serie.
*   **Exportación de datos:** Genera automáticamente dos archivos CSV por cada análisis sin lanzar errores de ruta:
    *   `*_serie.csv`: Contiene la serie temporal limpia de fechas y valores de NDVI.
    *   `*_resumen.csv`: Contiene las estadísticas consolidadas.
*   **Ejecución continua:** Permite analizar múltiples waypoints consecutivamente.

## Requisitos previos

*   Python 3.x
*   Credenciales y cuenta activa en Google Earth Engine.
*   Librerías de Python requeridas en esta versión:
```bash
pip install earthengine-api pandas numpy
```

## Configuración y Setup (`config.ini`)

El proyecto incluye un archivo `config.ini` que se encarga de manejar variables sin tocar la lógica del script:

```ini
[EarthEngine]
proyecto_id = tu-proyecto-gee-aqui

[Rutas]
# Puedes usar ~ para reflejar tu carpeta local de usuario
carpeta_salida = ~/Desktop/imagenes_satelitales/analisis_ndvi_multiple

[Defaults]
# Estos valores aparecerán pre-escritos en la consola
latitud_default = -34.652483699
longitud_default = -61.362346398
fecha_inicio_default = 2025-04-02
fecha_fin_default = 2025-11-11
```
*(Asegúrate de configurar el `proyecto_id` de Google Cloud vinculado a tu cuenta de GEE si el original da un error).*

## Uso

1. Ejecuta el script:
   ```bash
   python analisis_ndvi_v2_refac.py
   ```
2. La consola te pedirá ingresar los datos para el análisis. Puedes presionar `Enter` para usar los valores por defecto configurados en tu `config.ini` o tipear tus propios valores.
3. Los resultados se guardarán en la ruta configurada en el archivo `.ini`.
4. El programa te preguntará si deseas analizar otro punto al finalizar cada ejecución.

## Notas
* Si es la primera vez que ejecutas procesos de Earth Engine en tu entorno o tu token expira, el script intentará abrir automáticamente una ventana de navegador para solicitar tu autenticación.
