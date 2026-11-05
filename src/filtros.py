"""Filtros de tablas usados por la interfaz (lógica pura, sin Streamlit)."""
import re

import pandas as pd

from src.normalizacion import numero_bus, ordenar_lineas

TODOS = "Todos"


def opciones_linea(serie: pd.Series) -> list:
    """Líneas presentes en una columna; separa celdas con varias ('6012, 6023')."""
    partes = serie.dropna().astype(str).str.split(",").explode().str.strip()
    return ordenar_lineas(partes[partes != ""])


def opciones(df: pd.DataFrame, columna: str) -> list:
    """Valores para un desplegable, en orden natural."""
    if columna == "Línea":
        return opciones_linea(df[columna])
    valores = df[columna].dropna().astype(str).unique().tolist()
    return sorted(valores, key=lambda v: (numero_bus(v), v))


def filtrar_linea(df: pd.DataFrame, columna: str, linea: str) -> pd.DataFrame:
    """Coincidencia exacta de línea: '6025' no trae las filas de '6025B'."""
    patron = rf"(?<![\w]){re.escape(linea)}(?![\w])"
    return df[df[columna].astype(str).str.contains(patron, regex=True, na=False)]


def aplicar_filtros(df: pd.DataFrame, seleccion: dict, texto: str = "") -> pd.DataFrame:
    """seleccion: {columna: valor elegido}. TODOS no filtra. texto busca en todas las columnas."""
    for columna, valor in seleccion.items():
        if valor == TODOS:
            continue
        if columna == "Línea":
            df = filtrar_linea(df, columna, valor)
        else:
            df = df[df[columna].astype(str) == valor]
    if texto:
        coincide = df.astype(str).apply(
            lambda col: col.str.contains(texto, case=False, regex=False, na=False)
        ).any(axis=1)
        df = df[coincide]
    return df
