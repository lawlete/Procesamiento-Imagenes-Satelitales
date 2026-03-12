"""
SCRIPT DE ANÁLISIS NDVI - MÚLTIPLES WAYPOINTS
Permite analizar varios puntos sin reiniciar
Guardar en: E:\Alfredo Lawler\Pacho\analisis_ndvi_multiple.py
"""

import ee
import os
import csv
import statistics
import datetime
from datetime import datetime

###############################################
###############################################
# Lineas de prueba:
#import ssl
#import socket
#import logging
#logging.basicConfig(level=logging.DEBUG)
#socket.setdefaulttimeout(60)
#print("Versión OpenSSL:", ssl.OPENSSL_VERSION)
###############################################
###############################################

# Silenciar logs de depuración de librerías externas
import logging
logging.getLogger('googleapiclient').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('oauth2client').setLevel(logging.WARNING)


# ==========================================
# FUNCIONES DE UTILIDAD
# ==========================================

def ingresar_con_default(prompt, default):
    valor = input(f"{prompt} [default: {default}]: ").strip()
    return default if valor == "" else valor

def ingresar_float_con_default(prompt, default):
    while True:
        try:
            valor = ingresar_con_default(prompt, default)
            return float(valor)
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

def inicializar_ee():
    """Inicializa Earth Engine una sola vez"""
    PROYECTO = 'imagenes-satelitales-490002'
    try:
        ee.Initialize(project=PROYECTO)
        print(f"✅ Earth Engine inicializado con proyecto: {PROYECTO}")
        return True
    except Exception as e:
        print(f"❌ Error al inicializar: {e}")
        try:
            ee.Authenticate()
            ee.Initialize(project=PROYECTO)
            print(f"✅ Autenticación exitosa")
            return True
        except:
            return False

def analizar_waypoint(latitud, longitud, fecha_inicio, fecha_fin, carpeta_salida):
    """Analiza un waypoint y retorna los resultados"""
    
    # Crear nombre base para archivos
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    lat_str = str(latitud).replace('-', 'neg').replace('.', '_')
    lon_str = str(longitud).replace('-', 'neg').replace('.', '_')
    nombre_base = f'NDVI_{lat_str}_{lon_str}_{fecha_inicio}_{fecha_fin}_{timestamp}'
    
    print(f"\n{'='*70}")
    print(f"📍 ANALIZANDO: {latitud}, {longitud}")
    print(f"📅 PERÍODO: {fecha_inicio} a {fecha_fin}")
    print(f"{'='*70}")
    
    point = ee.Geometry.Point([longitud, latitud])
    
    try:
        # Cargar imágenes
        collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                     .filterBounds(point)
                     .filterDate(fecha_inicio, fecha_fin))
        
        total = collection.size().getInfo()
        print(f"📸 Imágenes totales: {total}")
        
        if total == 0:
            print("❌ No hay imágenes")
            return None
        
        # Procesar imágenes
        image_list = collection.toList(total)
        datos = []
        imagenes_con_nubes = 0
        
        for i in range(total):
            try:
                image = ee.Image(image_list.get(i))
                
                # Máscara de nubes
                qa = image.select('QA60')
                cloud = 1 << 10
                cirrus = 1 << 11
                mask = qa.bitwiseAnd(cloud).eq(0).And(qa.bitwiseAnd(cirrus).eq(0))
                image_masked = image.updateMask(mask)
                
                # NDVI
                scaled = image_masked.divide(10000)
                nir = scaled.select('B8')
                red = scaled.select('B4')
                ndvi = nir.subtract(red).divide(nir.add(red)).rename('NDVI')
                
                # Extraer valor
                ndvi_value = ndvi.reduceRegion(
                    reducer=ee.Reducer.first(),
                    geometry=point,
                    scale=10,
                    maxPixels=1
                ).get('NDVI').getInfo()
                
                fecha = ee.Date(image.get('system:time_start')).format('YYYY-MM-dd').getInfo()
                
                if ndvi_value is not None:
                    datos.append({'fecha': fecha, 'NDVI': ndvi_value})
                    print(f"   ✓ {i+1}/{total}: NDVI={ndvi_value:.4f} ({fecha})")
                else:
                    imagenes_con_nubes += 1
                    print(f"   ⚠️ {i+1}/{total}: Con nubes ({fecha})")
                    
            except Exception as e:
                print(f"   ⚠️ Error imagen {i+1}")
                continue
        
        if len(datos) == 0:
            print("❌ Sin imágenes válidas")
            return None
        
        # Estadísticas
        datos.sort(key=lambda x: x['fecha'])
        valores = [d['NDVI'] for d in datos]
        fechas = [d['fecha'] for d in datos]
        
        mean = statistics.mean(valores)
        min_val = min(valores)
        max_val = max(valores)
        std = statistics.stdev(valores) if len(valores) > 1 else 0
        
        idx_min = valores.index(min_val)
        idx_max = valores.index(max_val)
        
        # Guardar archivos
        csv_serie = os.path.join(carpeta_salida, f'{nombre_base}_serie.csv')
        with open(csv_serie, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['fecha', 'NDVI'])
            writer.writerows([[d['fecha'], d['NDVI']] for d in datos])
        
        resultados = {
            'latitud': latitud,
            'longitud': longitud,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'imagenes_totales': total,
            'imagenes_validas': len(datos),
            'NDVI_promedio': round(mean, 4),
            'NDVI_minimo': round(min_val, 4),
            'NDVI_maximo': round(max_val, 4),
            'fecha_minimo': fechas[idx_min],
            'fecha_maximo': fechas[idx_max]
        }
        
        if len(valores) >= 5:
            import numpy as np
            p = np.percentile(valores, [50])
            resultados['mediana'] = round(p[0], 4)
        
        csv_resumen = os.path.join(carpeta_salida, f'{nombre_base}_resumen.csv')
        with open(csv_resumen, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=resultados.keys())
            writer.writeheader()
            writer.writerow(resultados)
        
        print(f"\n✅ RESULTADOS:")
        print(f"   PROMEDIO: {resultados['NDVI_promedio']}")
        print(f"   MÁXIMO: {resultados['NDVI_maximo']} ({resultados['fecha_maximo']})")
        print(f"   MÍNIMO: {resultados['NDVI_minimo']} ({resultados['fecha_minimo']})")
        print(f"📁 Archivos: {csv_serie}")
        
        return resultados
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

# ==========================================
# PROGRAMA PRINCIPAL
# ==========================================

def main():
    print("="*70)
    print("ANÁLISIS NDVI - MÚLTIPLES WAYPOINTS")
    print("="*70)
    
    # Inicializar Earth Engine (una sola vez)
    if not inicializar_ee():
        print("❌ No se pudo inicializar Earth Engine")
        return
    
    carpeta = os.path.join(os.path.expanduser('~'), 'Desktop')
    print(f"📁 Los archivos se guardarán en: {carpeta}")
    
    continuar = True
    while continuar:
        print("\n" + "-"*50)
        print("NUEVO ANÁLISIS")
        print("-"*50)
        
        # Valores por defecto
        default_lat = -34.652483699
        default_lon = -61.362346398
        default_ini = '2025-04-02'
        default_fin = '2025-11-11'
        
        lat = ingresar_float_con_default("Latitud", default_lat)
        lon = ingresar_float_con_default("Longitud", default_lon)
        ini = ingresar_fecha_con_default("Fecha inicio", default_ini)
        fin = ingresar_fecha_con_default("Fecha fin", default_fin)
        
        analizar_waypoint(lat, lon, ini, fin, carpeta)
        
        resp = input("\n¿Analizar otro waypoint? (s/n): ").strip().lower()
        continuar = resp in ['s', 'si', 'sí', 'y', 'yes']
    
    print("\n" + "="*70)
    print("PROGRAMA FINALIZADO")
    print("="*70)

if __name__ == "__main__":
    main()
    input("\nPresiona Enter para salir...")