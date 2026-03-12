import time

print("="*60)
print("🚀 INICIANDO MEDICIÓN DE RENDIMIENTO (BENCHMARK)")
print("="*60)

# 1. Medir importaciones
start_imports = time.time()
import analisis_ndvi_v2_refac as main_script
end_imports = time.time()
print(f"⏱️ [1] Importación de librerías (pandas, ee, etc): {end_imports - start_imports:.2f} segundos")

# 2. Medir inicialización de GEE
start_init = time.time()
main_script.inicializar_ee()
end_init = time.time()
print(f"⏱️ [2] Inicialización de API GEE (Conexión/Autenticación): {end_init - start_init:.2f} segundos")

print("\n⚙️  Procesando en servidores de Google...")
# 3. Medir procesamiento
start_process = time.time()
main_script.procesar_waypoint(
    main_script.DEFAULT_LAT, 
    main_script.DEFAULT_LON, 
    main_script.DEFAULT_INI, 
    main_script.DEFAULT_FIN
)
end_process = time.time()
print(f"\n⏱️ [3] Tiempo de Procesamiento GEE + Pandas + CSV (I/O): {end_process - start_process:.2f} segundos")

print("\n" + "="*60)
print(f"📊 TIEMPO TOTAL DE EJECUCIÓN: {(end_process - start_imports):.2f} segundos")
print("="*60)
