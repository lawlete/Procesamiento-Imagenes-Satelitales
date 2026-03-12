r"""
SCRIPT DE ANÁLISIS NDVI - MÚLTIPLES WAYPOINTS (v2 Refactorizado)
Permite analizar varios puntos sin reiniciar aprovechando GEE Server-Side
"""

import ee
import os
import pandas as pd
from datetime import datetime
import logging

# ==========================================
# CONFIGURACIÓN GLOBAL
# ==========================================
PROYECTO_GEE = 'imagenes-satelitales-490002'
CARPETA_SALIDA = os.path.join(os.path.expanduser('~'), 'Desktop', 'imagenes_satelitales', 'analisis_ndvi_multiple')

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
    
    csv_resumen = os.path.join(CARPETA_SALIDA, f'{nombre_base}_resumen.csv')
    pd.DataFrame([stats]).to_csv(csv_resumen, index=False)
    
    print(f"\n📈 RESULTADOS:")
    print(f"   PROMEDIO: {stats['NDVI_promedio']}")
    print(f"   MÁXIMO: {stats['NDVI_maximo']} ({stats['fecha_maximo']})")
    print(f"   MÍNIMO: {stats['NDVI_minimo']} ({stats['fecha_minimo']})")
    print(f"📁 Archivos guardados exitosamente!")
    
    return stats

# ==========================================
# PROGRAMA PRINCIPAL
# ==========================================
def main():
    print("="*70)
    print("ANÁLISIS NDVI - MÚLTIPLES WAYPOINTS (REFACTORIZADO CON PANDAS)")
    print("="*70)
    
    if not inicializar_ee():
        return
    
    print(f"📁 Output de archivos será en: {CARPETA_SALIDA}")
    
    continuar = True
    while continuar:
        print("\n" + "-"*50 + "\nNUEVO ANÁLISIS\n" + "-"*50)
        
        # Recolección de inputs
        lat = ingresar_float_con_default("Latitud", -34.652483699)
        lon = ingresar_float_con_default("Longitud", -61.362346398)
        ini = ingresar_fecha_con_default("Fecha inicio", '2025-04-02')
        fin = ingresar_fecha_con_default("Fecha fin", '2025-11-11')
        
        procesar_waypoint(lat, lon, ini, fin)
        
        resp = input("\n¿Analizar otro waypoint? (s/n): ").strip().lower()
        continuar = resp in ['s', 'si', 'sí', 'y', 'yes']
    
    print("\n" + "="*70 + "\nPROGRAMA FINALIZADO\n" + "="*70)

if __name__ == "__main__":
    main()
    input("\nPresiona Enter para salir...")