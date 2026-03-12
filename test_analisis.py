import pytest
from unittest.mock import patch
import os

# Importamos el módulo a probar
import analisis_ndvi_v2_refac as g script

# ==========================================
# PRUEBAS UNITARIAS
# ==========================================
def test_ingresar_con_default():
    """Prueba que los defaults se mantienen si el usuario presiona Enter vacio"""
    with patch('builtins.input', return_value=''):
        assert script.ingresar_con_default('Prompt', 'valor_test') == 'valor_test'
    
    with patch('builtins.input', return_value='nuevo_valor'):
        assert script.ingresar_con_default('Prompt', 'valor_test') == 'nuevo_valor'

def test_ingresar_float_con_default():
    """Prueba que el casting a float se hace correctamente"""
    # Si devuelve '' toma el default (int casteado a float u float original)
    with patch('builtins.input', return_value=''):
        assert script.ingresar_float_con_default('Latitud', -34.5) == -34.5

    # Si devuelve ' -33.1 ', tira los espacios extras y castea a float
    with patch('builtins.input', return_value=' -33.1 '):
        assert script.ingresar_float_con_default('Latitud', -34.5) == -33.1


# ==========================================
# PRUEBAS FUNCIONALES
# ==========================================
@patch('analisis_ndvi_v2_refac.obtener_serie_ndvi_gee')
def test_procesar_waypoint_flujo_completo(mock_gee, tmp_path):
    """
    Simula una respuesta del servidor de Google (para no gastar red ni auth)
    y prueba que Pandas devuelva estadísticas y guarde resultados correctamente
    """
    
    # 1. Preparación (Mocking y Setup)
    # Configuramos el mock para que devuelva datos ficticios perfectos
    mock_gee.return_value = [
        {'fecha': '2025-04-02', 'NDVI': 0.2000},
        {'fecha': '2025-04-12', 'NDVI': 0.6000},
        {'fecha': '2025-04-22', 'NDVI': 0.8000},
        {'fecha': '2025-05-02', 'NDVI': 0.4000},
        {'fecha': '2025-05-12', 'NDVI': 0.5000}
    ]

    # Cambiamos temporalmente el path de guardado al directorio fantasma de Pytest
    script.CARPETA_SALIDA = str(tmp_path)
    
    # 2. Ejecución
    stats = script.procesar_waypoint(-34.0, -61.0, '2025-04-01', '2025-05-31')
    
    # 3. Verificaciones de Procesamiento Matemático
    assert stats is not None
    assert stats['imagenes_validas'] == 5
    assert stats['NDVI_maximo'] == 0.8000
    assert stats['NDVI_minimo'] == 0.2000
    assert stats['NDVI_promedio'] == 0.5000
    assert stats['mediana'] == 0.5000
    assert stats['fecha_maximo'] == '2025-04-22'
    
    # 4. Verificaciones de I/O (Exportación a disco)
    archivos_generados = os.listdir(tmp_path)
    assert len(archivos_generados) == 2  # Debe haber dos CVS
    
    assert any("serie.csv" in a for a in archivos_generados)
    assert any("resumen.csv" in a for a in archivos_generados)
