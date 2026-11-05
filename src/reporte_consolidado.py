"""
Excel del consolidado de reclamación de una quincena.

Misma estructura del archivo que usa la empresa ("Acumulado GPS <Mes> Q1/Q2"):

  Horarios   PSO completo (copia de la hoja cargada en la app).
  Resumen    Título en A1:I2, encabezados en la fila 3 y un registro por caso:
             Unidad, Fecha, Ruta, Circulación H-T, Hora inicio, Hora fin, Usuarios,
             Hipervinculo (lleva a la evidencia) y Distancia (km, fórmula a la evidencia).
             Al final, el Total.
  Evidencia  Un bloque por caso, en el mismo orden del Resumen:
               - descripción de la novedad
               - filas del informe de servicios (SAE) donde se presenta la novedad
               - recorte del PSO (izquierda) con la distancia a reclamar en km debajo
               - usos de la unidad entre la hora de inicio y la de fin (derecha)

Los colores son los de la app.
"""
from __future__ import annotations

from datetime import datetime, time
from io import BytesIO

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.hyperlink import Hyperlink
from openpyxl.worksheet.worksheet import Worksheet

from config import REVISION_DETALLADA
from src.consolidado import CasoReclamo, Quincena
from src.pso import COLUMNAS_PSO
from src.reporte_excel import (
    BLANCO, BORDE, FONDO_ALTERNO, FUENTE, GRIS_PESTANA, GRIS_TEXTO, MORADO, VERDE,
    VERDE_MEDIO, VERDE_OSCURO, VERDE_SUAVE,
)

NARANJA_SUAVE = "FFF3E0"
NARANJA_TEXTO = "E65100"
AZUL_ENLACE = "0B57D0"
AMARILLO_TOTAL = "FFF9C4"

_LINEA = Side(style="thin", color=BORDE)
BORDE_CELDA = Border(left=_LINEA, right=_LINEA, top=_LINEA, bottom=_LINEA)
FORMATO_KM = '#,##0.000'

COLUMNAS_RESUMEN = ["Unidad", "Fecha", "Ruta", "Circulación H-T", "Hora inicio", "Hora fin ",
                    "Usuarios", "Hipervinculo", "Distancia"]
ANCHOS_RESUMEN = [10, 13, 20, 20, 13, 13, 11, 20, 13]

COLUMNA_USOS = 8                 # los usos van a la derecha del PSO, desde la columna H
FILAS_ENTRE_CASOS = 3


# ── Utilidades de formato ─────────────────────────────────────────────────────

def _fuente(tamano=10, negrita=False, color="1A1A1A", cursiva=False, subrayado=None) -> Font:
    return Font(name=FUENTE, size=tamano, bold=negrita, color=color, italic=cursiva,
                underline=subrayado)


def _relleno(color: str) -> PatternFill:
    return PatternFill("solid", start_color=color)


def _centro(envolver=False) -> Alignment:
    return Alignment(horizontal="center", vertical="center", wrap_text=envolver)


def _valor_excel(valor):
    """Valores que Excel entiende (fechas, horas y números se conservan)."""
    if valor is None:
        return None
    if isinstance(valor, float) and pd.isna(valor):
        return None
    if isinstance(valor, pd.Timestamp):
        return None if pd.isna(valor) else valor.to_pydatetime()
    if isinstance(valor, pd.Timedelta):
        return str(valor)
    if hasattr(valor, "item") and not isinstance(valor, (str, bytes)):
        try:
            return valor.item()
        except (ValueError, AttributeError):
            return str(valor)
    return valor


def _formato(valor) -> str:
    if isinstance(valor, datetime):
        if valor.hour == valor.minute == valor.second == 0:
            return "DD/MM/YYYY"
        return "DD/MM/YYYY HH:MM:SS"
    if isinstance(valor, time):
        return "HH:MM:SS"
    if isinstance(valor, float):
        return "#,##0.##"
    return "General"


def _encabezados(ws: Worksheet, fila: int, columna: int, nombres: list,
                 color: str = VERDE) -> None:
    for j, nombre in enumerate(nombres):
        c = ws.cell(row=fila, column=columna + j, value=str(nombre))
        c.font = _fuente(9, True, BLANCO)
        c.fill = _relleno(color)
        c.alignment = _centro(True)
        c.border = BORDE_CELDA
    ws.row_dimensions[fila].height = 30


def _tabla(ws: Worksheet, fila: int, columna: int, df: pd.DataFrame,
           color: str = VERDE) -> int:
    """Escribe encabezado y filas. Devuelve la última fila escrita."""
    _encabezados(ws, fila, columna, list(df.columns), color)
    for i, valores in enumerate(df.astype(object).itertuples(index=False, name=None), 1):
        alterna = i % 2 == 0
        for j, valor in enumerate(valores):
            valor = _valor_excel(valor)
            c = ws.cell(row=fila + i, column=columna + j, value=valor)
            c.font = _fuente(9)
            c.border = BORDE_CELDA
            c.alignment = _centro()
            c.number_format = _formato(valor)
            if alterna:
                c.fill = _relleno(FONDO_ALTERNO)
    return fila + len(df)


def _enlace(celda, destino: str, texto: str | None = None) -> None:
    """Hipervínculo dentro del libro (destino: "Evidencia!A12")."""
    if texto is not None:
        celda.value = texto
    celda.hyperlink = Hyperlink(ref=celda.coordinate, location=destino, display=str(celda.value))
    celda.font = _fuente(10, color=AZUL_ENLACE, subrayado="single")


# ── Textos ───────────────────────────────────────────────────────────────────

def unidad_c6(caso: CasoReclamo) -> str:
    return f"C6-{caso.numero_unidad:03d}"


def descripcion(caso: CasoReclamo) -> str:
    fecha = f"{caso.fecha:%d-%m-%Y}"
    desde, hasta = f"{caso.inicio:%H:%M}", f"{caso.fin:%H:%M}"
    if caso.revision_detallada:
        return (f"Unidad {unidad_c6(caso)} el {fecha} registra una movilización de "
                f"{caso.usuarios} usuarios entre las {desde} y las {hasta} sin información "
                f"en SAE (no hay servicio registrado en ese horario). Se requiere revisión "
                f"detallada para establecer ruta, circulación y distancia a reclamar.")
    texto = (f"Unidad {unidad_c6(caso)} de la ruta {caso.ruta} el {fecha} no muestra "
             f"kilometraje correspondiente al programado, desde el itinerario {desde} hasta "
             f"el itinerario de {hasta}, la información se corrobora con una movilización "
             f"para dicho día de {caso.usuarios} usuarios")
    if caso.recorrido_m:
        texto += (f" (SAE registra solo {caso.recorrido_m / 1000:,.3f} km, por debajo de la "
                  f"distancia media)").replace(",", "X").replace(".", ",").replace("X", ".")
    if caso.casos_unidos > 1:
        texto += f". Se unen {caso.casos_unidos} registros seguidos de la unidad"
    return texto


# ── Hojas ────────────────────────────────────────────────────────────────────

def _hoja_horarios(wb: Workbook, hoja_pso: pd.DataFrame | None) -> None:
    ws = wb.create_sheet("Horarios")
    ws.sheet_properties.tabColor = GRIS_PESTANA
    if hoja_pso is None or hoja_pso.empty:
        ws["A1"] = "No hay PSO cargado en la app."
        return
    columnas = list(hoja_pso.columns)
    pso_desde = next((i for i, c in enumerate(columnas) if c in COLUMNAS_PSO), len(columnas))
    for j, nombre in enumerate(columnas, start=1):
        titulo = "" if str(nombre).startswith("Unnamed") else str(nombre)   # sin título en Excel
        c = ws.cell(row=1, column=j, value=titulo)
        c.font = _fuente(9, True, BLANCO)
        c.fill = _relleno(VERDE_OSCURO if j - 1 >= pso_desde else VERDE)
        c.alignment = _centro(True)
    for i, valores in enumerate(hoja_pso.astype(object).itertuples(index=False, name=None), 2):
        for j, valor in enumerate(valores, start=1):
            ws.cell(row=i, column=j, value=_valor_excel(valor))
    for j, nombre in enumerate(columnas, start=1):
        ws.column_dimensions[get_column_letter(j)].width = max(11, min(len(str(nombre)) + 4, 30))
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(columnas))}{len(hoja_pso) + 1}"


def _bloque_evidencia(ws: Worksheet, fila: int, caso: CasoReclamo, fila_resumen: int) -> tuple[int, int]:
    """Escribe la evidencia de un caso desde `fila`.

    Devuelve (fila de la celda con la distancia en km, siguiente fila libre).
    """
    ancho = max(len(caso.servicios.columns), COLUMNA_USOS + len(caso.usos.columns) - 1, 12)
    # Descripción
    ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=ancho)
    c = ws.cell(row=fila, column=1, value=descripcion(caso))
    c.font = _fuente(10, True, VERDE_OSCURO)
    c.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True, indent=1)
    for j in range(1, ancho + 1):
        ws.cell(row=fila, column=j).fill = _relleno(VERDE_SUAVE)
        ws.cell(row=fila, column=j).border = Border(top=Side(style="medium", color=VERDE))
    ws.row_dimensions[fila].height = 46
    volver = ws.cell(row=fila + 1, column=1)
    _enlace(volver, f"Resumen!A{fila_resumen}", "↩ Volver al Resumen")
    volver.font = _fuente(8, color=AZUL_ENLACE, subrayado="single")

    # Informe de servicios
    f = fila + 3
    ws.cell(row=f, column=1, value="Informe de servicios (SAE)").font = _fuente(10, True, VERDE)
    if caso.servicios.empty:
        ws.cell(row=f + 1, column=1, value="Sin registro en el informe de servicios para este "
                "horario (usos sin información en SAE).").font = _fuente(9, cursiva=True,
                                                                         color=GRIS_TEXTO)
        f += 3
    else:
        f = _tabla(ws, f + 1, 1, caso.servicios, VERDE_MEDIO) + 3

    # PSO (izquierda) y usos (derecha), lado a lado
    ws.cell(row=f, column=1, value="PSO (Horarios)").font = _fuente(10, True, VERDE)
    ws.cell(row=f, column=COLUMNA_USOS,
            value=f"Usos de la unidad ({caso.usuarios})").font = _fuente(10, True, MORADO)

    if caso.revision_detallada:
        ws.cell(row=f + 1, column=1, value=REVISION_DETALLADA).font = _fuente(10, True, NARANJA_TEXTO)
        ws.cell(row=f + 2, column=1, value="Ruta y circulación por definir.").font = \
            _fuente(9, cursiva=True, color=GRIS_TEXTO)
        fin_pso = f + 2
    elif caso.pso.empty:
        ws.cell(row=f + 1, column=1, value="No se encontraron itinerarios del PSO para esta "
                "ruta, circulación y horario.").font = _fuente(9, cursiva=True, color=NARANJA_TEXTO)
        fin_pso = f + 1
    else:
        fin_pso = _tabla(ws, f + 1, 1, caso.pso[COLUMNAS_PSO], VERDE_OSCURO)

    # Distancia a reclamar en km, debajo del PSO
    fila_total = fin_pso + 1
    formula_pso = f"SUM(E{f + 2}:E{fin_pso})/1000"
    if caso.equivalencia and not caso.pso.empty and not caso.distancia_manual:
        # Equivalencia: PSO − lo que registró SAE = lo que falta
        for etiqueta_texto, valor in (("Distancia según PSO (km)", f"={formula_pso}"),
                                      ("Registrado en SAE (km)", caso.recorrido_m / 1000)):
            _fila_distancia(ws, fila_total, etiqueta_texto, valor, destacar=False)
            fila_total += 1
        _fila_distancia(ws, fila_total, "Distancia a reclamar (km)",
                        f"=MAX(E{fila_total - 2}-E{fila_total - 1},0)")
        ws.cell(row=fila_total + 1, column=1, value="Equivalencia: se reclama lo que falta "
                "para completar la distancia del PSO.").font = _fuente(8, cursiva=True,
                                                                        color=GRIS_TEXTO)
        fin_usos = _usos_evidencia(ws, f, caso)
        return fila_total, max(fila_total + 2, fin_usos) + 1 + FILAS_ENTRE_CASOS

    etiqueta = ws.cell(row=fila_total, column=1, value="Distancia a reclamar (km)")
    etiqueta.font = _fuente(9, True, VERDE_OSCURO)
    ws.merge_cells(start_row=fila_total, start_column=1, end_row=fila_total, end_column=4)
    etiqueta.alignment = Alignment(horizontal="right", vertical="center", indent=1)
    total = ws.cell(row=fila_total, column=5)
    if caso.distancia_manual:
        total.value = caso.distancia_km
        nota = "Distancia escrita en la app" if caso.distancia_km is not None else \
            "Distancia por definir"
        ws.cell(row=fila_total + 1, column=1, value=nota).font = _fuente(8, cursiva=True,
                                                                         color=GRIS_TEXTO)
    elif not caso.pso.empty:
        total.value = f"={formula_pso}"
    total.number_format = FORMATO_KM
    total.font = _fuente(11, True, VERDE_OSCURO)
    total.fill = _relleno(AMARILLO_TOTAL)
    total.border = BORDE_CELDA
    total.alignment = _centro()

    fin_usos = _usos_evidencia(ws, f, caso)

    return fila_total, max(fila_total + 1, fin_usos) + 1 + FILAS_ENTRE_CASOS


def _fila_distancia(ws: Worksheet, fila: int, texto: str, valor, destacar: bool = True) -> None:
    etiqueta = ws.cell(row=fila, column=1, value=texto)
    etiqueta.font = _fuente(9, True, VERDE_OSCURO if destacar else GRIS_TEXTO)
    ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=4)
    etiqueta.alignment = Alignment(horizontal="right", vertical="center", indent=1)
    celda = ws.cell(row=fila, column=5, value=valor)
    celda.number_format = FORMATO_KM
    celda.font = _fuente(11 if destacar else 10, destacar, VERDE_OSCURO if destacar else "1A1A1A")
    celda.border = BORDE_CELDA
    celda.alignment = _centro()
    if destacar:
        celda.fill = _relleno(AMARILLO_TOTAL)


def _usos_evidencia(ws: Worksheet, fila: int, caso: CasoReclamo) -> int:
    """Tabla de usos a la derecha del PSO. Devuelve la última fila escrita."""
    if caso.usos.empty:
        ws.cell(row=fila + 1, column=COLUMNA_USOS, value="Sin usos registrados.").font = \
            _fuente(9, cursiva=True, color=GRIS_TEXTO)
        return fila + 1
    return _tabla(ws, fila + 1, COLUMNA_USOS, caso.usos, MORADO)


def _hoja_evidencia(wb: Workbook, casos: list[CasoReclamo]) -> list[tuple[int, int]]:
    """Un bloque por caso. Devuelve (fila de inicio, fila de la distancia) de cada caso."""
    ws = wb.create_sheet("Evidencia")
    ws.sheet_properties.tabColor = MORADO
    ws.sheet_view.showGridLines = False
    posiciones = []
    fila = 1
    for i, caso in enumerate(casos):
        fila_total, siguiente = _bloque_evidencia(ws, fila, caso, 4 + i)
        posiciones.append((fila, fila_total))
        fila = siguiente
    for j in range(1, 30):
        ws.column_dimensions[get_column_letter(j)].width = 15
    ws.column_dimensions["A"].width = 13
    return posiciones


def _hoja_resumen(wb: Workbook, quincena: Quincena, casos: list[CasoReclamo],
                  posiciones: list[tuple[int, int]]) -> None:
    ws = wb.create_sheet("Resumen", 1)
    ws.sheet_properties.tabColor = VERDE_OSCURO
    ws.sheet_view.showGridLines = False
    ultima = get_column_letter(len(COLUMNAS_RESUMEN))

    ws.merge_cells(f"A1:{ultima}2")
    titulo = ws["A1"]
    titulo.value = quincena.titulo
    titulo.font = _fuente(15, True, BLANCO)
    titulo.alignment = _centro()
    for fila in (1, 2):
        for j in range(1, len(COLUMNAS_RESUMEN) + 1):
            ws.cell(row=fila, column=j).fill = _relleno(VERDE_OSCURO)
    ws.row_dimensions[1].height = 22
    ws.row_dimensions[2].height = 22
    _encabezados(ws, 3, 1, COLUMNAS_RESUMEN)

    for i, (caso, (fila_evidencia, fila_total)) in enumerate(zip(casos, posiciones)):
        r = 4 + i
        alterna = i % 2 == 1
        valores = [caso.numero_unidad, datetime.combine(caso.fecha, time()), caso.ruta,
                   caso.circulacion, caso.inicio.time(), caso.fin.time(), caso.usuarios]
        formatos = ["0", "DD/MM/YYYY", "@", "@", "HH:MM:SS", "HH:MM:SS", "#,##0"]
        for j, (valor, formato) in enumerate(zip(valores, formatos), start=1):
            c = ws.cell(row=r, column=j, value=int(valor) if formato == "@" and
                        str(valor).isdigit() else valor)
            c.number_format = "0" if formato == "@" and str(valor).isdigit() else formato
            c.font = _fuente(10, j == 1)
            c.alignment = _centro()
        enlace = ws.cell(row=r, column=8)
        _enlace(enlace, f"Evidencia!A{fila_evidencia}", f"Evidencia!A{fila_evidencia}")
        enlace.alignment = _centro()
        distancia = ws.cell(row=r, column=9)
        if caso.distancia_km is not None:
            distancia.value = f"=Evidencia!$E${fila_total}"
        distancia.number_format = FORMATO_KM
        distancia.font = _fuente(10, True)
        distancia.alignment = _centro()
        for j in range(1, len(COLUMNAS_RESUMEN) + 1):
            c = ws.cell(row=r, column=j)
            c.border = BORDE_CELDA
            if alterna:
                c.fill = _relleno(FONDO_ALTERNO)
        if caso.revision_detallada or caso.distancia_km is None:
            for j in (3, 4, 9):
                ws.cell(row=r, column=j).fill = _relleno(NARANJA_SUAVE)
            for j in (3, 4):
                ws.cell(row=r, column=j).font = _fuente(9, True, NARANJA_TEXTO)

    total = 4 + len(casos)
    ws.cell(row=total, column=8, value="Total").font = _fuente(10, True, BLANCO)
    suma = ws.cell(row=total, column=9,
                   value=f"=SUM(I4:I{total - 1})" if casos else 0)
    suma.font = _fuente(11, True, BLANCO)
    suma.number_format = FORMATO_KM
    for j in (8, 9):
        celda = ws.cell(row=total, column=j)
        celda.fill = _relleno(VERDE_OSCURO)
        celda.alignment = _centro()
        celda.border = BORDE_CELDA

    nota = total + 2
    ws.cell(row=nota, column=1, value=f"Quincena: {quincena.rango}  ·  Generado: "
            f"{datetime.now():%d/%m/%Y %H:%M}  ·  Recuperación de Km · SAO").font = \
        _fuente(8, cursiva=True, color=GRIS_TEXTO)
    if any(c.revision_detallada or c.distancia_km is None for c in casos):
        ws.cell(row=nota + 1, column=1, value="En naranja: casos sin distancia calculada "
                f"({REVISION_DETALLADA} o sin itinerarios en el PSO).").font = \
            _fuente(8, cursiva=True, color=NARANJA_TEXTO)

    for j, ancho in enumerate(ANCHOS_RESUMEN, start=1):
        ws.column_dimensions[get_column_letter(j)].width = ancho
    ws.freeze_panes = "A4"
    if casos:
        ws.auto_filter.ref = f"A3:{ultima}{total - 1}"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True


def generar_consolidado(quincena: Quincena, casos: list[CasoReclamo],
                        hoja_pso: pd.DataFrame | None) -> bytes:
    casos = sorted(casos, key=lambda c: (c.fecha, c.inicio, c.numero_unidad))
    wb = Workbook()
    wb.remove(wb.active)
    _hoja_horarios(wb, hoja_pso)
    posiciones = _hoja_evidencia(wb, casos)
    _hoja_resumen(wb, quincena, casos, posiciones)
    wb.active = wb.sheetnames.index("Resumen")
    for ws in wb.worksheets:
        ws.sheet_view.tabSelected = ws.title == "Resumen"
    wb.calculation.fullCalcOnLoad = True
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
