r"""
SCRIPT DE ANÁLISIS NDVI - MÚLTIPLES WAYPOINTS (v2 Refactorizado)
Permite analizar varios puntos sin reiniciar aprovechando GEE Server-Side
"""

import ee
import os
import pandas as pd
from datetime import datetime
import logging
import configparser

# ==========================================
# CONFIGURACIÓN GLOBAL (Lectura de config.ini)
# ==========================================
# Cargar configuración
config = configparser.ConfigParser()
config_file = os.path.join(os.path.dirname(__file__), 'config.ini')

if not os.path.exists(config_file):
    print(f"❌ Archivo {config_file} no encontrado. Por favor crearlo.")
    exit(1)

config.read(config_file, encoding='utf-8')

# Asignar variables globales desde archivo
PROYECTO_GEE = config.get('EarthEngine', 'proyecto_id', fallback='imagenes-satelitales-490002')
_carpeta_raw = config.get('Rutas', 'carpeta_salida', fallback='~/Desktop/imagenes_satelitales/analisis_ndvi_multiple')
CARPETA_SALIDA = os.path.expanduser(_carpeta_raw)

DEFAULT_LAT = config.getfloat('Defaults', 'latitud_default', fallback=-34.652483699)
DEFAULT_LON = config.getfloat('Defaults', 'longitud_default', fallback=-61.362346398)
DEFAULT_INI = config.get('Defaults', 'fecha_inicio_default', fallback='2025-04-02')
DEFAULT_FIN = config.get('Defaults', 'fecha_fin_default', fallback='2025-11-11')

logging.getLogger('googleapiclient').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('oauth2client').setLevel(logging.WARNING)

# ==========================================
# FUNCIONES DE UTILIDAD PARA USUARIO
# ==========================================
def ingresar_con_default(prompt, default):
    valor = input(f"{prompt} [default: {default}]: ").strip()
    return default if valor == "" else valor

def ingresar_float_con_default(prompt, default):
    while True:
        try:
            return float(ingresar_con_default(prompt, default))
        except ValueError:
            print("❌ Error: Ingrese un número válido")

def ingresar_fecha_con_default(prompt, default):
    while True:
        try:
            valor = ingresar_con_default(prompt, default)
            datetime.strptime(valor, '%Y-%m-%d')
            return valor
        except ValueError:
            print("❌ Error: Use formato YYYY-MM-DD")

# ==========================================
# LÓGICA CORE: GOOGLE EARTH ENGINE
# ==========================================
def inicializar_ee():
    """Inicializa Earth Engine usando configuraciones globales"""
    try:
        ee.Initialize(project=PROYECTO_GEE)
        print(f"✅ Earth Engine inicializado con proyecto: {PROYECTO_GEE}")
        return True
    except Exception as e:
        print(f"⚠️ Aviso al inicializar: {e}. Intentando autenticar...")
        try:
            ee.Authenticate()
            ee.Initialize(project=PROYECTO_GEE)
            print(f"✅ Autenticación y configuración exitosas.")
            return True
        except Exception as auth_e:
            print(f"❌ Error crítico de Earth Engine: {auth_e}")
            return False

def obtener_serie_ndvi_gee(latitud, longitud, fecha_inicio, fecha_fin):
    """
    Descarga de GEE toda la serie de NDVI precalculada en el servidor,
    eliminando el bucle 'for' limitante de Python.
    """
    point = ee.Geometry.Point([longitud, latitud])
    
    def procesar_imagen(image):
        # Máscara de nubes
        qa = image.select('QA60')
        cloudBitMask = 1 << 10
        cirrusBitMask = 1 << 11
        mask = qa.bitwiseAnd(cloudBitMask).eq(0).And(qa.bitwiseAnd(cirrusBitMask).eq(0))
        img_masked = image.updateMask(mask)
        
        # Cálculo del NDVI mediante NormalizedDifference (Más rápido que matemáticas estandar)
        ndvi = img_masked.normalizedDifference(['B8', 'B4']).rename('NDVI')
        
        # Extraer valor del punto específico
        ndvi_val = ndvi.reduceRegion(
            reducer=ee.Reducer.first(),
            geometry=point,
            scale=10,
            maxPixels=1
        ).get('NDVI')
        
        # Retornar característica (Feature) con Fecha y Valor 
        fecha = ee.Date(image.get('system:time_start')).format('YYYY-MM-dd')
        return ee.Feature(None, {
            'fecha': fecha, 
            'NDVI': ndvi_val
        })

    print("⏳ Consultando servidores de Google Earth Engine (esto tomará pocos segundos)...")
    
    collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                 .filterBounds(point)
                 .filterDate(fecha_inicio, fecha_fin))
    
    total_imagenes = collection.size().getInfo()
    print(f"📸 Se encontraron {total_imagenes} imágenes en el período.")
    
    if total_imagenes == 0:
        return None

    # AQUÍ ESTÁ LA OPTIMIZACIÓN: Mapeamos en servidor y traemos TODO en un solo .getInfo()
    serie_features = collection.map(procesar_imagen).getInfo()['features']
    
    # Filtrar valores nulos (nubes) de manera local
    datos_limpios = []
    nubes = 0
    for f in serie_features:
        props = f['properties']
        if props.get('NDVI') is not None:
            datos_limpios.append({'fecha': props['fecha'], 'NDVI': props['NDVI']})
        else:
            nubes += 1
            
    print(f"☁️ Imágenes descartadas (nubes/fuera de escena): {nubes}")
    print(f"✅ Imágenes válidas procesadas: {len(datos_limpios)}")
    
    return datos_limpios

# ==========================================
# MANEJO DE DATOS Y ARCHIVOS (PANDAS)
# ==========================================
def generar_reporte_agronomico(df, stats, ruta_txt):
    """
    Genera un informe descriptivo y estadístico narrativo de las fases de la pastura
    basado en el comportamiento temporal del NDVI.
    """
    # Cálculos adicionales para el reporte
    mean = stats['NDVI_promedio']
    std = df['NDVI'].std()
    cv = (std / mean) * 100 if mean > 0 else 0
    
    stats['NDVI_std'] = round(std, 4)
    stats['NDVI_cv'] = round(cv, 2)
    
    with open(ruta_txt, 'w', encoding='utf-8') as f:
        f.write("RESUMEN ESTADÍSTICO DESCRIPTIVO Y EVOLUCIÓN TEMPORAL\n")
        f.write("="*60 + "\n\n")
        
        f.write("1. Comportamiento Global del Índice\n")
        f.write("-" * 40 + "\n")
        f.write(f"El comportamiento global del índice durante el periodo analizado muestra los siguientes valores clave:\n")
        f.write(f"• Valor Promedio: El NDVI medio fue de {stats['NDVI_promedio']:.4f}, lo que indica el vigor general de la cobertura vegetal.\n")
        f.write(f"• Valores Extremos: El mínimo ({stats['NDVI_minimo']:.4f}) se registró el {stats['fecha_minimo']}, "
                f"probablemente reflejando el momento de menor cobertura, estado de suelo desnudo o post-siembra. "
                f"El máximo ({stats['NDVI_maximo']:.4f}) se alcanzó el {stats['fecha_maximo']}, señalando el pico máximo de biomasa.\n")
        f.write(f"• Variabilidad: El coeficiente de variación temporal es del {stats['NDVI_cv']:.2f}%, "
                f"un indicador de cómo fluctuó la cobertura a lo largo del ciclo.\n\n")

        f.write("2. Análisis de la Evolución Temporal por Fases o Estaciones\n")
        f.write("-" * 40 + "\n")
        f.write("La serie temporal permite observar distintas fases en el desarrollo de la pastura:\n")

        # Separar por meses las etapas de crecimiento (Hemisferio Sur)
        # Otoño (Mar, Abr, May) - Invierno (Jun, Jul, Ago) - Primavera (Sep, Oct, Nov) - Verano (Dic, Ene, Feb)
        etapas = {
            'Otoño (Fase Inicial / Establecimiento)': [3, 4, 5],
            'Invierno (Crecimiento Lento / Sostenido)': [6, 7, 8],
            'Primavera (Explosión Primaveral / Alta Actividad)': [9, 10, 11],
            'Verano (Ciclo Tardío / Estrés)': [12, 1, 2]
        }
        
        for nombre_etapa, meses in etapas.items():
            df_etapa = df[df['fecha'].dt.month.isin(meses)]
            if not df_etapa.empty:
                val_min = df_etapa['NDVI'].min()
                val_max = df_etapa['NDVI'].max()
                val_mean = df_etapa['NDVI'].mean()
                f.write(f"• Fase {nombre_etapa}: Se registraron fluctuaciones entre {val_min:.4f} y {val_max:.4f}. "
                        f"En esta etapa, el promedio sostenido fue de {val_mean:.4f}.\n")

        f.write("\n" + "="*60 + "\n")
    
    print("\n📝 REPORTE GENERADO AUTOMÁTICAMENTE:")
    # Imprimimos un extracto al usuario en consola
    with open(ruta_txt, 'r', encoding='utf-8') as f:
        print(f.read())


def procesar_waypoint(latitud, longitud, fecha_inicio, fecha_fin):
    """Controlador que une GEE, análisis estadístico y exportación"""
    print(f"\n{'='*70}\n📍 ANALIZANDO: {latitud}, {longitud}\n📅 PERÍODO: {fecha_inicio} a {fecha_fin}\n{'='*70}")
    
    # 1. Obtener datos satelitales crudos
    datos = obtener_serie_ndvi_gee(latitud, longitud, fecha_inicio, fecha_fin)
    
    if not datos:
        print("❌ Análisis abortado: Sin imágenes válidas.")
        return None
    
    # 2. Análisis y Limpieza con Pandas
    df = pd.DataFrame(datos)
    df['fecha'] = pd.to_datetime(df['fecha'])
    df = df.sort_values('fecha').reset_index(drop=True)
    
    # 3. Cálculo de Estadísticas Unificadas
    stats = {
        'latitud': latitud,
        'longitud': longitud,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'imagenes_validas': len(df),
        'NDVI_promedio': round(df['NDVI'].mean(), 4),
        'NDVI_minimo': round(df['NDVI'].min(), 4),
        'NDVI_maximo': round(df['NDVI'].max(), 4),
        'fecha_minimo': df.loc[df['NDVI'].idxmin(), 'fecha'].strftime('%Y-%m-%d'),
        'fecha_maximo': df.loc[df['NDVI'].idxmax(), 'fecha'].strftime('%Y-%m-%d'),
        'mediana': round(df['NDVI'].median(), 4) if len(df) >= 5 else None
    }
    
    # 4. Exportación a disco de manera segura
    os.makedirs(CARPETA_SALIDA, exist_ok=True) # Crea la carpeta si no existe
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    lat_str = str(latitud).replace('-', 'neg').replace('.', '_')
    lon_str = str(longitud).replace('-', 'neg').replace('.', '_')
    nombre_base = f'NDVI_{lat_str}_{lon_str}_{fecha_inicio}_{fecha_fin}_{timestamp}'
    
    # Convertimos nuevamente las fechas a string corto para el CSV
    csv_serie = os.path.join(CARPETA_SALIDA, f'{nombre_base}_serie.csv')
    df.to_csv(csv_serie, index=False, date_format='%Y-%m-%d')
    
    # Generar el reporte automatizado (Esto también nos nutrirá `stats` con CV y STD)
    txt_reporte = os.path.join(CARPETA_SALIDA, f'{nombre_base}_reporte.txt')
    generar_reporte_agronomico(df, stats, txt_reporte)

    csv_resumen = os.path.join(CARPETA_SALIDA, f'{nombre_base}_resumen.csv')
    pd.DataFrame([stats]).to_csv(csv_resumen, index=False)
    
    print(f"📁 Archivos guardados exitosamente en: {CARPETA_SALIDA}")
    
    return stats

# ==========================================
# PROGRAMA PRINCIPAL Y MENÚ
# ==========================================
def procesar_desde_archivo(ruta_archivo):
    """Procesa un lote de puntos y fechas a partir de un archivo CSV"""
    try:
        df_puntos = pd.read_csv(ruta_archivo)
        requeridos = {'latitud', 'longitud', 'fecha_inicio', 'fecha_fin'}
        
        # Validar formato del archivo
        if not requeridos.issubset(set(df_puntos.columns)):
            print(f"❌ Error: El archivo debe contener exactamente estas columnas:")
            print("   latitud, longitud, fecha_inicio, fecha_fin")
            return
            
        print(f"✅ Archivo cargado. Se encontraron {len(df_puntos)} puntos a procesar.")
        
        # Iterar cada punto
        for index, row in df_puntos.iterrows():
            print(f"\n[{index + 1}/{len(df_puntos)}] Procesando lote...")
            procesar_waypoint(row['latitud'], row['longitud'], str(row['fecha_inicio']), str(row['fecha_fin']))
        
        print("\n✅ PROCESAMIENTO POR LOTE FINALIZADO.")
        
    except Exception as e:
        print(f"❌ Error al intentar leer el archivo: {e}")

def main():
    print("="*70)
    print("ANÁLISIS NDVI - MÚLTIPLES WAYPOINTS (REFACTORIZADO CON PANDAS)")
    print("="*70)
    
    if not inicializar_ee():
        return
    
    print(f"📁 Output de archivos será en: {CARPETA_SALIDA}")
    
    print("\n¿Cómo desea ingresar los datos de análisis?")
    print(" 1 - Carga Manual (Interactivo por consola)")
    print(" 2 - Desde Archivo CSV (Procesamiento por lote)")
    modo = input("\nSeleccione opción [1/2]: ").strip()
    
    if modo == '2':
        print("\n--- MODO LOTE DESDE ARCHIVO ---")
        print("Asegúrese de proveer un archivo delimitado por comas con este formato en la cabecera:")
        print("latitud,longitud,fecha_inicio,fecha_fin")
        
        ruta_archivo = ingresar_con_default("\nIngrese la ruta y nombre del archivo", "waypoints.csv")
        
        if os.path.exists(ruta_archivo):
            procesar_desde_archivo(ruta_archivo)
        else:
            print(f"❌ No se pudo encontrar el archivo provisto: {ruta_archivo}")
    else:
        continuar = True
        while continuar:
            print("\n" + "-"*50 + "\nNUEVO ANÁLISIS (MANUAL)\n" + "-"*50)
            
            # Recolección de inputs
            lat = ingresar_float_con_default("Latitud", DEFAULT_LAT)
            lon = ingresar_float_con_default("Longitud", DEFAULT_LON)
            ini = ingresar_fecha_con_default("Fecha inicio", DEFAULT_INI)
            fin = ingresar_fecha_con_default("Fecha fin", DEFAULT_FIN)
            
            procesar_waypoint(lat, lon, ini, fin)
            
            resp = input("\n¿Analizar otro waypoint? (s/n): ").strip().lower()
            continuar = resp in ['s', 'si', 'sí', 'y', 'yes']
    
    print("\n" + "="*70 + "\nPROGRAMA FINALIZADO\n" + "="*70)

if __name__ == "__main__":
    main()
    input("\nPresiona Enter para salir...")