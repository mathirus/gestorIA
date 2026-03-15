from services.alicuotas import ALICUOTAS_SELLOS, COSTO_VERIFICACION_POLICIAL, ARANCEL_DNRPA_PORCENTAJE


def calcular_costos(valuacion: int, provincia: str) -> dict:
    alicuota_sellos = ALICUOTAS_SELLOS.get(provincia, 2.5)

    arancel_dnrpa = int(valuacion * ARANCEL_DNRPA_PORCENTAJE / 100)
    sellos = int(valuacion * alicuota_sellos / 100)
    verificacion = COSTO_VERIFICACION_POLICIAL
    total = arancel_dnrpa + sellos + verificacion

    return {
        "valuacion_fiscal": valuacion,
        "arancel_dnrpa": arancel_dnrpa,
        "arancel_dnrpa_porcentaje": ARANCEL_DNRPA_PORCENTAJE,
        "sellos": sellos,
        "sellos_porcentaje": alicuota_sellos,
        "verificacion_policial": verificacion,
        "total": total,
        "provincia": provincia,
    }
