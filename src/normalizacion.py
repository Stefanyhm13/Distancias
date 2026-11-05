"""Funciones puras para limpiar valores sueltos (buses, líneas, horas)."""
import re
import unicodedata
from datetime import datetime, time

import pandas as pd

from config import LINEAS_SAO


def normalizar_texto(texto) -> str:
    """'  Vehículos ' -> 'vehiculos'. Para comparar encabezados sin tildes ni mayúsculas."""
    texto = unicodedata.normalize("NFKD", str(texto))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.lower().split())


def normalizar_bus(valor) -> str | None:
    """'sao-001 ' -> 'SAO001'."""
    if pd.isna(valor):
        return None
    return str(valor).strip().upper().replace("-", "") or None


def numero_bus(valor) -> int:
    """'SAO-012' -> 12. Sirve para ordenar los buses de forma natural."""
    if pd.isna(valor):
        return 0
    m = re.search(r"\d+", str(valor))
    return int(m.group()) if m else 0


def normalizar_linea(valor) -> str | None:
    """6023.0 -> '6023', ' 6025b' -> '6025B'."""
    if pd.isna(valor):
        return None
    s = str(valor).strip().upper()
    if s.endswith(".0"):
        s = s[:-2]
    return s or None


def normalizar_circulacion(valor) -> str | None:
    """H-T del informe o circulación del PSO -> número de circulación.

    '0-503' -> '503', '0-053' -> '53', 461 -> '461', '461.0' -> '461'.
    """
    if pd.isna(valor):
        return None
    s = str(valor).strip()
    if "-" in s:
        s = s.rsplit("-", 1)[1].strip()
    if s.endswith(".0"):
        s = s[:-2]
    if s.isdigit():
        s = str(int(s))
    return s.upper() or None


def ordenar_lineas(lineas) -> list:
    """Orden natural (6002, 6002A, 6003...), primero las de LINEAS_SAO."""
    def clave(linea):
        m = re.match(r"(\d+)(.*)", linea)
        numero, sufijo = (int(m.group(1)), m.group(2)) if m else (0, linea)
        return (linea not in LINEAS_SAO, numero, sufijo)
    return sorted(set(lineas), key=clave)


_FORMATOS_HORA = ("%I:%M:%S %p", "%H:%M:%S", "%I:%M %p", "%H:%M")


def parsear_hora(valor) -> time | None:
    """Acepta time, datetime o texto ('5:05:00 a. m.', '17:40')."""
    if isinstance(valor, time):
        return valor
    if pd.isna(valor):          # None, NaN, NaT
        return None
    if isinstance(valor, datetime):
        return valor.time()
    texto = str(valor).strip().lower()
    for viejo, nuevo in (("a. m.", "AM"), ("p. m.", "PM"), ("a.m.", "AM"), ("p.m.", "PM")):
        texto = texto.replace(viejo, nuevo)
    for formato in _FORMATOS_HORA:
        try:
            return datetime.strptime(texto, formato).time()
        except ValueError:
            continue
    return None
