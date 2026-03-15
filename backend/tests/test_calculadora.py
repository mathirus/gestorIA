import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.calculadora import calcular_costos

def test_costos_caba():
    resultado = calcular_costos(valuacion=15_000_000, provincia="caba")
    assert resultado["arancel_dnrpa"] == 150_000       # 1%
    assert resultado["sellos"] == 375_000               # 2.5% CABA
    assert resultado["verificacion_policial"] == 20_000
    assert resultado["total"] == 150_000 + 375_000 + 20_000

def test_costos_buenos_aires():
    resultado = calcular_costos(valuacion=15_000_000, provincia="buenos_aires")
    assert resultado["arancel_dnrpa"] == 150_000
    assert resultado["sellos"] == 450_000               # 3% PBA

def test_costos_provincia_desconocida_usa_default():
    resultado = calcular_costos(valuacion=10_000_000, provincia="chaco")
    assert resultado["sellos_porcentaje"] == 2.5  # default
    assert resultado["sellos"] == 250_000

def test_costos_incluye_desglose_completo():
    resultado = calcular_costos(valuacion=20_000_000, provincia="caba")
    assert "valuacion_fiscal" in resultado
    assert "arancel_dnrpa" in resultado
    assert "arancel_dnrpa_porcentaje" in resultado
    assert "sellos" in resultado
    assert "sellos_porcentaje" in resultado
    assert "verificacion_policial" in resultado
    assert "total" in resultado
    assert "provincia" in resultado
