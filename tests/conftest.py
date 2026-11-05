"""Generadores de archivos de prueba con la misma estructura que los reales."""
import sys
from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest
from openpyxl import Workbook

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

FECHA = "13/10/2026"

# Columnas A..P del informe de servicios
# (E = Línea, I/J = Inicio/Fin de Servicio, L = Distancia, O/P = Inicio/Fin efectivo)
ENCABEZADOS_SERVICIOS = [
    "#", "Vehículos", "C", "D", "Línea", "F", "G", "H-T",
    "Inicio de Servicio", "Fin de Servicio", "K",
    "Distancia", "M", "N", "Inicio Servicio Efectivo", "Fin Servicio Efectivo",
]


def servicio(bus, linea, distancia_m, inicio, fin, fecha=FECHA, fecha_fin=None, numero=1,
             inicio_servicio=None, fin_servicio=None, ht=None):
    """Fila del informe. `inicio`/`fin` = efectivos (O/P); `inicio_servicio`/`fin_servicio`
    = Inicio/Fin de Servicio (I/J), por defecto iguales a los efectivos."""
    fin_fecha = fecha_fin or fecha
    return [numero, bus, None, None, linea, None, None, ht,
            f"{fecha} {inicio_servicio or inicio}", f"{fin_fecha} {fin_servicio or fin}", None,
            distancia_m, None, None, f"{fecha} {inicio}", f"{fin_fecha} {fin}"]


def excel_servicios(filas, encabezados=ENCABEZADOS_SERVICIOS, hoja="Hoja1") -> BytesIO:
    wb = Workbook()
    ws = wb.active
    ws.title = hoja
    for _ in range(3):
        ws.append([])
    ws.append(encabezados)
    for fila in filas:
        ws.append(fila)
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def excel_usos(registros, fecha="2026-10-13") -> BytesIO:
    """registros: [(bus, 'HH:MM:SS'), ...]"""
    df = pd.DataFrame({
        "Id": range(len(registros)),
        "Fecha": [fecha] * len(registros),
        "Hora": [h for _, h in registros],
        "Equipo": [b for b, _ in registros],
    })
    buffer = BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)
    return buffer


@pytest.fixture
def params():
    """Parámetros iniciales de las rutas (cuadro original)."""
    from src.parametros import parametros_iniciales
    return parametros_iniciales()


@pytest.fixture
def archivos_basicos():
    servicios = excel_servicios([
        servicio("SAO-001", 6023, 21000, "05:00:00", "06:10:00"),
        servicio("SAO-001", "6025B", 3000, "08:00:00", "08:30:00"),
        servicio("SAO-002", 6025, 500, "05:00:00", "05:20:00"),
    ])
    usos = excel_usos([
        ("SAO-001", "05:10:00"), ("SAO-001", "07:10:00"),
        ("SAO-002", "05:05:00"), ("SAO-002", "5:40:00 a. m."),
        ("SAO-002", "23:45:00"), ("SAO-099", "09:00:00"),
    ])
    return usos, servicios
