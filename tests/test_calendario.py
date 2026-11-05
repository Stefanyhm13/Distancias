from datetime import date

import pytest

from src.calendario import DOMINGO, HABIL, SABADO, festivos_calculados, tipo_de_dia


@pytest.mark.parametrize("fecha, tipo", [
    (date(2026, 10, 13), HABIL),      # martes
    (date(2026, 10, 3), SABADO),
    (date(2026, 10, 4), DOMINGO),
    (date(2026, 10, 12), DOMINGO),    # festivo: Día de la Raza (lunes)
    (date(2026, 11, 2), DOMINGO),     # festivo trasladado: Todos los Santos
    (date(2026, 4, 3), DOMINGO),      # Viernes Santo
    (date(2026, 7, 13), DOMINGO),     # Virgen de Chiquinquirá (Ley 2578 de 2026)
    (date(2026, 11, 3), HABIL),
])
def test_tipo_de_dia(fecha, tipo):
    assert tipo_de_dia(fecha)[0] == tipo


def test_festivo_dice_su_nombre():
    tipo, motivo = tipo_de_dia(date(2026, 12, 25))
    assert tipo == DOMINGO and motivo.startswith("Festivo")


def test_calculo_propio_coincide_con_calendario_oficial():
    holidays = pytest.importorskip("holidays")
    for anio in range(2000, 2041):
        oficial = set(holidays.country_holidays("CO", years=anio))
        assert set(festivos_calculados(anio)) == oficial, anio
