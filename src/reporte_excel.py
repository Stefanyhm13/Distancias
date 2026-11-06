"""
Informe Excel con el diseño corporativo de la app.

Cada hoja tiene la misma estructura:
    fila 1   título (franja verde oscuro)
    fila 2   qué contiene la hoja
    fila 3   fecha del informe y fecha de generación
    (Resumen: tarjetas de indicadores con fórmulas)
    (hojas con validación: leyenda de colores)
    tabla    encabezado verde, filtros, paneles fijos y filas alternadas
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, time
from io import BytesIO

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, NamedStyle, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from config import Validacion
from src.analisis import COL_RECORRIDO, ResultadoAnalisis
from src.calendario import NOMBRES_TIPO
from src.normalizacion import normalizar_texto, parsear_hora

# ── Paleta corporativa (la misma de la app) ───────────────────────────────────
VERDE_OSCURO = "0D4F28"
VERDE = "1B7A3E"
VERDE_MEDIO = "25A055"
VERDE_SUAVE = "C8E6D0"
FONDO_ALTERNO = "F3F7F3"
FONDO_TARJETA = "F8FBF8"
BORDE = "D5DED6"
GRIS_TEXTO = "5F6B63"
GRIS_PESTANA = "8C9A90"
MORADO = "8E24AA"
BLANCO = "FFFFFF"

FUENTE = "Arial"

# Colores de cada validación: (relleno de la celda, color del texto, tinte de la fila)
COLORES_VALIDACION = {
    Validacion.OPERO:         ("E8F5E9", "1B5E20", None),
    Validacion.NO_OPERO:      ("EEEEEE", "757575", None),
    Validacion.REVISAR:       ("FFCDD2", "B71C1C", "FFF1F2"),
    Validacion.KM_BAJO:       ("FFE0B2", "E65100", "FFF6EC"),
    Validacion.USO_SIN_VIAJE: ("E1BEE7", "6A1B9A", "F7EEF9"),
}
DESCRIPCION_VALIDACION = {
    Validacion.OPERO: "cumplió la distancia mínima",
    Validacion.NO_OPERO: "viaje sin distancia ni usos",
    Validacion.REVISAR: "registro sin distancia con usos",
    Validacion.KM_BAJO: "menos del mínimo y con usos",
    Validacion.USO_SIN_VIAJE: "uso fuera de todo viaje (km 0)",
}

_LINEA = Side(style="thin", color=BORDE)
BORDE_CELDA = Border(left=_LINEA, right=_LINEA, top=_LINEA, bottom=_LINEA)

# Formatos de número
FORMATO_METROS = '#,##0;[Red]-#,##0;0'      # negativos en rojo
FORMATO_MINUTOS = '0.0'
FORMATO_ENTERO = '#,##0'
FORMATO_FECHA_HORA = 'DD/MM/YYYY HH:MM:SS'
FORMATO_FECHA = 'DD/MM/YYYY'
FORMATO_HORA = 'HH:MM:SS'
FORMATO_DECIMAL = '#,##0.00'

ANCHO_MIN, ANCHO_MAX = 9, 40
FILAS_MUESTRA_ANCHO = 400


@dataclass
class Hoja:
    nombre: str
    titulo: str
    descripcion: str
    datos: pd.DataFrame
    leyenda: list = field(default_factory=list)       # validaciones a explicar
    color_pestana: str = VERDE_MEDIO


@dataclass
class HojaEscrita:
    ws: Worksheet
    datos: pd.DataFrame
    encabezado: int                                  # fila del encabezado de la tabla

    def rango(self, columna: str) -> str:
        """Referencia absoluta a los datos de una columna: 'Viajes'!$N$12:$N$5586."""
        letra = get_column_letter(list(self.datos.columns).index(columna) + 1)
        fin = self.encabezado + max(len(self.datos), 1)
        return f"'{self.ws.title}'!${letra}${self.encabezado + 1}:${letra}${fin}"


# ── Estilos con nombre (una asignación por celda: rápido en hojas grandes) ────

TIPOS = {"texto": "General", "metros": FORMATO_METROS, "minutos": FORMATO_MINUTOS,
         "entero": FORMATO_ENTERO, "fecha": FORMATO_FECHA_HORA, "decimal": FORMATO_DECIMAL,
         "solo_fecha": FORMATO_FECHA, "hora": FORMATO_HORA}


def _registrar_estilos(wb: Workbook) -> None:
    fuente = Font(name=FUENTE, size=10, color="1A1A1A")
    for sufijo, relleno in (("", None), (" alterna", FONDO_ALTERNO)):
        for tipo, formato in TIPOS.items():
            estilo = NamedStyle(name=tipo + sufijo, font=fuente, border=BORDE_CELDA,
                                number_format=formato,
                                alignment=Alignment(horizontal="center", vertical="center"))
            if relleno:
                estilo.fill = PatternFill("solid", start_color=relleno)
            wb.add_named_style(estilo)


def _es_columna_hora(nombre: str) -> bool:
    return "hora" in normalizar_texto(nombre).split()


def _a_horas(serie: pd.Series) -> pd.Series | None:
    """Columna de horas -> valores datetime.time (Excel los guarda como hora real).

    Acepta horas ya leídas como hora, fracciones de día (0.5 = 12:00:00, que es como
    Excel guarda las horas y por eso se veían en decimal), fecha-hora o texto
    ('17:40:00', '5:05:00 a. m.'). Devuelve None si la columna no es de horas.
    """
    valores = serie.dropna()
    if valores.empty:
        return None
    if pd.api.types.is_numeric_dtype(serie):
        if not ((valores >= 0) & (valores < 1)).all():
            return None
        segundos = (serie * 86400).round()
        return segundos.map(lambda x: None if pd.isna(x) else
                            time(int(x) // 3600 % 24, int(x) // 60 % 60, int(x) % 60))
    if pd.api.types.is_timedelta64_dtype(serie):
        segundos = serie.dt.total_seconds()
        return segundos.map(lambda x: None if pd.isna(x) else
                            time(int(x) // 3600 % 24, int(x) // 60 % 60, int(x) % 60))
    horas = serie.map(parsear_hora)
    if horas[serie.notna()].isna().any():
        return None                       # hay textos que no son horas: se deja igual
    return horas


def _preparar(df: pd.DataFrame) -> pd.DataFrame:
    """Columnas de hora como horas reales, para que Excel las muestre como HH:MM:SS."""
    df = df.copy()
    for nombre in df.columns:
        if _es_columna_hora(str(nombre)):
            horas = _a_horas(df[nombre])
            if horas is not None:
                df[nombre] = horas.astype(object)
    return df


def _tipo_columna(nombre: str, serie: pd.Series) -> str:
    if nombre.endswith("(m)"):
        return "metros"
    if nombre.endswith("(min)"):
        return "minutos"
    valores = serie.dropna()
    if not valores.empty and valores.map(lambda v: isinstance(v, time)).all():
        return "hora"
    if pd.api.types.is_datetime64_any_dtype(serie):
        # Fechas sin hora (todas a medianoche) se muestran solo como fecha
        if not valores.empty and (valores == valores.dt.normalize()).all():
            return "solo_fecha"
        return "fecha"
    if pd.api.types.is_integer_dtype(serie):
        return "entero"
    if pd.api.types.is_float_dtype(serie):
        return "decimal"
    return "texto"


# ── Bloques de cada hoja ──────────────────────────────────────────────────────

def _franja(ws: Worksheet, fila: int, ancho: int, texto: str, fuente: Font,
            relleno: str | None = None, alto: float | None = None) -> None:
    ultima = get_column_letter(ancho)
    ws.merge_cells(f"A{fila}:{ultima}{fila}")
    celda = ws[f"A{fila}"]
    celda.value = texto
    celda.font = fuente
    celda.alignment = Alignment(horizontal="left", vertical="center", indent=1, wrap_text=True)
    if relleno:
        for col in range(1, ancho + 1):
            ws.cell(row=fila, column=col).fill = PatternFill("solid", start_color=relleno)
    if alto:
        ws.row_dimensions[fila].height = alto


def _texto_tipo_dia(tipo_dia: str) -> str:
    if not tipo_dia:
        return ""
    return f"     ·     Analizado como día {NOMBRES_TIPO.get(tipo_dia, tipo_dia)}"


def _encabezado_hoja(ws: Worksheet, hoja: Hoja, fecha, ancho: int, tipo_dia: str = "") -> int:
    """Título, descripción y fecha. Devuelve la siguiente fila libre."""
    _franja(ws, 1, ancho, f"Recuperación de Km · SAO   |   {hoja.titulo}",
            Font(name=FUENTE, size=15, bold=True, color=BLANCO), VERDE_OSCURO, 34)
    _franja(ws, 2, ancho, hoja.descripcion,
            Font(name=FUENTE, size=10, italic=True, color=GRIS_TEXTO), None, 32)
    _franja(ws, 3, ancho, f"Fecha del informe: {fecha:%d/%m/%Y}{_texto_tipo_dia(tipo_dia)}"
                          f"     ·     Generado: {datetime.now():%d/%m/%Y %H:%M}",
            Font(name=FUENTE, size=9, bold=True, color=VERDE), None, 18)
    for col in range(1, ancho + 1):
        ws.cell(row=3, column=col).border = Border(bottom=Side(style="medium", color=VERDE_SUAVE))
    return 5


def _leyenda(ws: Worksheet, fila: int, validaciones: list) -> int:
    """Un recuadro de color por cada validación, con su explicación debajo."""
    etiqueta = ws.cell(row=fila, column=1, value="Leyenda")
    etiqueta.font = Font(name=FUENTE, size=9, bold=True, color=VERDE)
    etiqueta.alignment = Alignment(horizontal="center", vertical="center")
    col = 2
    for validacion in validaciones:
        relleno, texto, _ = COLORES_VALIDACION[validacion]
        ws.merge_cells(start_row=fila, start_column=col, end_row=fila, end_column=col + 1)
        ws.merge_cells(start_row=fila + 1, start_column=col, end_row=fila + 1, end_column=col + 1)
        chip = ws.cell(row=fila, column=col, value=validacion)
        chip.font = Font(name=FUENTE, size=9, bold=True, color=texto)
        chip.alignment = Alignment(horizontal="center", vertical="center")
        for c in (col, col + 1):
            ws.cell(row=fila, column=c).fill = PatternFill("solid", start_color=relleno)
        nota = ws.cell(row=fila + 1, column=col, value=DESCRIPCION_VALIDACION[validacion])
        nota.font = Font(name=FUENTE, size=8, italic=True, color=GRIS_TEXTO)
        nota.alignment = Alignment(horizontal="center", vertical="top", wrap_text=True)
        col += 3
    ws.row_dimensions[fila].height = 20
    ws.row_dimensions[fila + 1].height = 24
    return fila + 3


def _tarjetas(ws: Worksheet, fila: int, tarjetas: list) -> int:
    """Indicadores: etiqueta arriba y valor (fórmula) grande abajo, dos columnas por tarjeta."""
    col = 1
    for etiqueta, formula, formato, color in tarjetas:
        ws.merge_cells(start_row=fila, start_column=col, end_row=fila, end_column=col + 1)
        ws.merge_cells(start_row=fila + 1, start_column=col, end_row=fila + 1, end_column=col + 1)
        titulo = ws.cell(row=fila, column=col, value=etiqueta.upper())
        titulo.font = Font(name=FUENTE, size=8, bold=True, color=GRIS_TEXTO)
        valor = ws.cell(row=fila + 1, column=col, value=formula)
        valor.font = Font(name=FUENTE, size=18, bold=True, color=color)
        valor.number_format = formato
        for celda in (titulo, valor):
            celda.alignment = Alignment(horizontal="center", vertical="center")
        for r in (fila, fila + 1):
            for c in (col, col + 1):
                ws.cell(row=r, column=c).fill = PatternFill("solid", start_color=FONDO_TARJETA)
                ws.cell(row=r, column=c).border = Border(
                    top=Side(style="thick", color=color) if r == fila else None,
                    bottom=_LINEA if r == fila + 1 else None,
                    left=_LINEA if c == col else None,
                    right=_LINEA if c == col + 1 else None)
        col += 2
    ws.row_dimensions[fila].height = 20
    ws.row_dimensions[fila + 1].height = 36
    return fila + 3


def _tabla(ws: Worksheet, fila: int, df: pd.DataFrame) -> int:
    """Escribe la tabla con formato. Devuelve la fila del encabezado."""
    df = _preparar(df)
    for j, nombre in enumerate(df.columns, start=1):
        c = ws.cell(row=fila, column=j, value=str(nombre))
        c.font = Font(name=FUENTE, size=10, bold=True, color=BLANCO)
        c.fill = PatternFill("solid", start_color=VERDE)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = Border(left=Side(style="thin", color=VERDE_MEDIO),
                          right=Side(style="thin", color=VERDE_MEDIO),
                          bottom=Side(style="medium", color=VERDE_OSCURO))
    ws.row_dimensions[fila].height = 32

    tipos = [_tipo_columna(str(n), df[n]) for n in df.columns]
    valores = df.astype(object).where(df.notna(), None).itertuples(index=False, name=None)
    for i, fila_datos in enumerate(valores, start=1):
        sufijo = " alterna" if i % 2 == 0 else ""
        for j, (valor, tipo) in enumerate(zip(fila_datos, tipos), start=1):
            ws.cell(row=fila + i, column=j, value=valor).style = tipo + sufijo

    for j, nombre in enumerate(df.columns, start=1):
        muestra = df[nombre].head(FILAS_MUESTRA_ANCHO).map(
            lambda v: "" if v is None or (not isinstance(v, time) and pd.isna(v)) else str(v))
        largo = max([len(str(nombre)) * 0.85] + [len(v) for v in muestra])
        ws.column_dimensions[get_column_letter(j)].width = max(ANCHO_MIN, min(largo + 3, ANCHO_MAX))

    ws.freeze_panes = ws.cell(row=fila + 1, column=1)
    if len(df):
        ws.auto_filter.ref = f"A{fila}:{get_column_letter(len(df.columns))}{fila + len(df)}"
    return fila


def _colorear_validacion(ws: Worksheet, df: pd.DataFrame, encabezado: int) -> None:
    """Celda de validación con su color; filas a revisar con un tinte suave."""
    if "Validación" not in df.columns:
        return
    col_validacion = list(df.columns).index("Validación") + 1
    for i, validacion in enumerate(df["Validación"], start=1):
        colores = COLORES_VALIDACION.get(validacion)
        if not colores:
            continue
        relleno, texto, tinte = colores
        fila = encabezado + i
        if tinte:
            for j in range(1, len(df.columns) + 1):
                ws.cell(row=fila, column=j).fill = PatternFill("solid", start_color=tinte)
        celda = ws.cell(row=fila, column=col_validacion)
        celda.fill = PatternFill("solid", start_color=relleno)
        celda.font = Font(name=FUENTE, size=10, bold=True, color=texto)


def _configurar_vista(ws: Worksheet, encabezado: int) -> None:
    ws.sheet_view.showGridLines = False
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_title_rows = f"{encabezado}:{encabezado}"


def _escribir_hoja(wb: Workbook, hoja: Hoja, fecha, tarjetas: list | None = None,
                   tipo_dia: str = "") -> HojaEscrita:
    ws = wb.create_sheet(hoja.nombre)
    ws.sheet_properties.tabColor = hoja.color_pestana
    ancho = max(len(hoja.datos.columns), 2 * len(tarjetas or []),
                3 * len(hoja.leyenda) + 1, 8)
    fila = _encabezado_hoja(ws, hoja, fecha, ancho, tipo_dia)
    if tarjetas:
        fila = _tarjetas(ws, fila, tarjetas)
    if hoja.leyenda:
        fila = _leyenda(ws, fila, hoja.leyenda)
    encabezado = _tabla(ws, fila, hoja.datos)
    _colorear_validacion(ws, hoja.datos, encabezado)
    _configurar_vista(ws, encabezado)
    return HojaEscrita(ws, hoja.datos, encabezado)


def _hoja_parametros(wb: Workbook, resultado: ResultadoAnalisis) -> None:
    """Parámetros con fórmulas: si se cambia un dato, las columnas calculadas se actualizan."""
    p = resultado.parametros
    rutas = p.tabla_calculada()
    pct = p.pct
    datos = pd.DataFrame({
        "Línea": rutas["linea"],
        "Distancia de ciclo (m)": rutas["distancia_ciclo_m"],
        "Tiempo de ciclo (min)": rutas["tiempo_ciclo_min"],
        "Distancia x min (m)": None,
        f"Distancia al {pct} x min (m)": None,
    })
    hoja = _escribir_hoja(wb, Hoja(
        "Parámetros", "Parámetros del análisis",
        f"Distancias por ruta con las que se hizo el análisis. Cada viaje debe recorrer al menos: "
        f"minutos del viaje × distancia al {pct} x min de su ruta. Las dos últimas columnas "
        f"son fórmulas.", datos, color_pestana=GRIS_PESTANA), resultado.fecha,
        tipo_dia=resultado.tipo_dia)
    ws, h = hoja.ws, hoja.encabezado

    # Supuestos en celdas propias, referenciados por las fórmulas
    nota = h + len(datos) + 2
    celda_pct = f"$B${nota + 1}"
    for k, (etiqueta, valor, formato) in enumerate([
        ("Supuestos del análisis", None, None),
        ("Porcentaje exigido", p.porcentaje_exigido,
         "0%" if round(p.porcentaje_exigido * 100, 6).is_integer() else "0.0%"),
        ("Minutos para agrupar usos sin viaje", p.minutos_agrupar_usos, "0"),
        ("Tipo de día (tabla de parámetros usada)",
         NOMBRES_TIPO.get(resultado.tipo_dia, resultado.tipo_dia) or None, "@"),
    ]):
        a = ws.cell(row=nota + k, column=1, value=etiqueta)
        a.font = Font(name=FUENTE, size=10, bold=(k == 0), color=VERDE if k == 0 else "1A1A1A")
        if valor is not None:
            b = ws.cell(row=nota + k, column=2, value=valor)
            b.number_format = formato
            b.font = Font(name=FUENTE, size=10, bold=True, color="0000FF")
            b.fill = PatternFill("solid", start_color="FFF9C4")
            b.border = BORDE_CELDA
            b.alignment = Alignment(horizontal="center")
    ws.cell(row=nota + 4, column=1,
            value="Valores con los que se generó este informe (se cambian en la app, "
                  "en 'Modificar parámetros').").font = \
        Font(name=FUENTE, size=8, italic=True, color=GRIS_TEXTO)

    for i in range(1, len(datos) + 1):
        r = h + i
        ws.cell(row=r, column=4, value=f'=IFERROR(B{r}/C{r},"")').number_format = FORMATO_DECIMAL
        ws.cell(row=r, column=5, value=f'=IFERROR(D{r}*{celda_pct},"")').number_format = \
            FORMATO_DECIMAL
        ws.cell(row=r, column=3).number_format = FORMATO_DECIMAL
    ws.column_dimensions["A"].width = 34
    for letra in "BCDE":
        ws.column_dimensions[letra].width = 22


# ── API pública ───────────────────────────────────────────────────────────────

ORDEN_HOJAS = ["Informe de Servicios", "Usos", "Usos sin información en SAE", "Usos sin info SAE - detalle",
               "Registros SAE", "Resumen", "Parámetros"]


def nombre_archivo(resultado: ResultadoAnalisis) -> str:
    return f"Informe_Recuperacion_Km_{resultado.fecha:%Y-%m-%d}.xlsx"


def generar_excel(resultado: ResultadoAnalisis) -> bytes:
    r = resultado
    fecha = r.fecha
    minutos = r.parametros.minutos_agrupar_usos
    pct = r.parametros.pct
    tipo = getattr(r, "tipo_dia", "")

    wb = Workbook()
    wb.remove(wb.active)
    _registrar_estilos(wb)

    _escribir_hoja(wb, Hoja(
        "Informe de Servicios", "Informe de servicios",
        "Servicios del informe original, ordenados por vehículo y hora "
        "(sin los registros duplicados con distancia 0).",
        r.servicios, color_pestana=GRIS_PESTANA), fecha, tipo_dia=tipo)

    usos = _escribir_hoja(wb, Hoja(
        "Usos", "Usos del día",
        "Usos (validaciones de pasajeros) de la fecha del informe y de la madrugada siguiente, "
        "ordenados por hora.", r.usos, color_pestana=GRIS_PESTANA), fecha, tipo_dia=tipo)

    grupos = _escribir_hoja(wb, Hoja(
        "Usos sin información en SAE", "Usos sin información en SAE (agrupados)",
        "Usos que no caen dentro de ningún viaje de su bus (entre Inicio y Fin de Servicio). "
        f"Se agrupan los usos seguidos del mismo bus y ruta, separados por {minutos} min o menos "
        "y sin un viaje entre ellos. Inicio y Fin = primer y último uso del grupo.",
        r.grupos_sin_viaje, leyenda=[Validacion.USO_SIN_VIAJE], color_pestana=MORADO), fecha, tipo_dia=tipo)

    _escribir_hoja(wb, Hoja(
        "Usos sin info SAE - detalle", "Usos sin información en SAE (uno por uno)",
        "Cada uso que no cae dentro de ningún viaje de su bus, con su fecha y hora.",
        r.usos_sin_viaje, leyenda=[Validacion.USO_SIN_VIAJE], color_pestana=MORADO), fecha, tipo_dia=tipo)

    viajes = _escribir_hoja(wb, Hoja(
        "Registros SAE", "Análisis por registro SAE",
        "Un registro por viaje. Inicio/Fin servicio = ventana para contar los usos. "
        f"Inicio/Fin efectivo = duración del viaje. Mínimo = duración efectiva × distancia al "
        f"{pct} x min de la ruta. Diferencia en rojo = metros que faltaron.",
        r.viajes.rename(columns={"Inicio": "Inicio efectivo", "Fin": "Fin efectivo"}),
        leyenda=[Validacion.OPERO, Validacion.NO_OPERO, Validacion.REVISAR,
                           Validacion.KM_BAJO], color_pestana=VERDE_MEDIO), fecha, tipo_dia=tipo)

    validacion = viajes.rango("Validación")
    tarjetas = [
        ("Registros SAE", f"=COUNTA({viajes.rango('N° viaje')})", FORMATO_ENTERO, VERDE),
        ("Km recorridos", f"=SUM({viajes.rango(COL_RECORRIDO)})/1000", "#,##0.0", "00796B"),
        ("Total usuarios día", f"=COUNTA({usos.rango(r.usos.columns[0])})", FORMATO_ENTERO, "7B1FA2"),
        ("Registros con distancia 0", f'=COUNTIF({validacion},"{Validacion.REVISAR}")',
         FORMATO_ENTERO, "C62828"),
        ("Registros con km bajo (equivalencia distancia media)", f'=COUNTIF({validacion},"{Validacion.KM_BAJO}")',
         FORMATO_ENTERO, "E65100"),
        ("Usos sin información en SAE",
         f"=SUM({grupos.rango('Usos')})" if len(r.grupos_sin_viaje) else 0,
         FORMATO_ENTERO, "6A1B9A"),
    ]
    _escribir_hoja(wb, Hoja(
        "Resumen", "Resumen para revisar",
        "Viajes a revisar y grupos de usos sin viaje, ordenados por vehículo y hora: "
        "son los km potencialmente recuperables.",
        r.resumen, leyenda=[Validacion.REVISAR, Validacion.KM_BAJO, Validacion.USO_SIN_VIAJE],
        color_pestana=VERDE_OSCURO), fecha, tarjetas=tarjetas,
        tipo_dia=tipo)

    _hoja_parametros(wb, r)

    # Se abre en el Resumen
    wb.active = wb.sheetnames.index("Resumen")
    for ws in wb.worksheets:
        ws.sheet_view.tabSelected = ws.title == "Resumen"
    wb.calculation.fullCalcOnLoad = True          # Excel calcula las fórmulas al abrir

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
