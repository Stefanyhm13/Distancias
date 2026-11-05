from io import BytesIO

import pandas as pd
import pytest
from openpyxl import load_workbook

from config import Validacion
from src.analisis import analizar
from src.filtros import aplicar_filtros, opciones_linea
from src.lectura import ErrorDeArchivo
from src.reporte_excel import generar_excel
from tests.conftest import (
    ENCABEZADOS_SERVICIOS, excel_servicios, excel_usos, servicio,
)


def viaje(r, vehiculo, inicio):
    v = r.viajes[(r.viajes["Vehículo"] == vehiculo) & (r.viajes["Inicio"] == inicio)]
    assert len(v) == 1
    return v.iloc[0]


def exigido(linea, params):
    """Metros por minuto exigidos (95 %) de una línea."""
    return params.distancia_95_por_linea()[linea]


# ── Un registro por viaje ─────────────────────────────────────────────────────

def test_un_registro_por_viaje(archivos_basicos, params):
    r = analizar(*archivos_basicos, params)
    assert len(r.viajes) == 3
    v = viaje(r, "SAO-001", "05:00:00")
    assert v["Fin"] == "06:10:00"
    assert v["Duración (min)"] == 70
    assert v["Recorrido (m)"] == 21000                       # distancia completa del viaje


def test_minimo_es_duracion_por_distancia_al_95(archivos_basicos, params):
    r = analizar(*archivos_basicos, params)
    v = viaje(r, "SAO-001", "05:00:00")
    assert v["Mínimo (m)"] == round(70 * exigido("6023", params))
    assert v["Diferencia (m)"] == v["Recorrido (m)"] - v["Mínimo (m)"]


def test_caso_real_sao_004(params):
    """Viajes reales de SAO-004 entre 18:03 y 19:27 (ruta 6019, 144,47 m/min)."""
    servicios = excel_servicios([
        servicio("SAO-004", 6019, 4324, "18:03:11", "18:25:25", numero=4339),
        servicio("SAO-004", 6019, 6, "18:25:26", "18:36:49", numero=4450),
        servicio("SAO-004", 6019, 3313, "18:39:52", "19:05:46", numero=4451),
        servicio("SAO-004", 6019, 4318, "19:06:03", "19:27:15", numero=4647),
    ])
    usos = excel_usos([("SAO-004", "18:30:00"), ("SAO-004", "18:45:00"),
                       ("SAO-004", "19:10:00"), ("SAO-004", "18:38:00")])
    r = analizar(usos, servicios, params)
    assert viaje(r, "SAO-004", "18:03:11")["Validación"] == Validacion.OPERO      # sin usos
    assert viaje(r, "SAO-004", "18:25:26")["Validación"] == Validacion.KM_BAJO    # 6 m
    v4451 = viaje(r, "SAO-004", "18:39:52")
    assert v4451["N° viaje"] == "4451"
    assert v4451["Mínimo (m)"] == 3742                       # 25,9 min × 144,47
    assert v4451["Validación"] == Validacion.KM_BAJO         # 3.313 < 3.742
    assert viaje(r, "SAO-004", "19:06:03")["Validación"] == Validacion.OPERO      # 4.318 ≥ 3.063
    # 18:38 cae entre dos viajes (18:36:49 y 18:39:52): uso sin viaje
    assert r.usos_sin_viaje["Hora"].tolist() == ["18:38:00"]


# ── Usos por viaje ────────────────────────────────────────────────────────────

def test_usos_se_asocian_con_inicio_y_fin_de_servicio(params):
    """Caso real SAO-004 viaje 1839: Inicio de Servicio 10:22:08, efectivo 10:22:45."""
    servicios = excel_servicios([
        servicio("SAO-004", 6019, 3341, "10:22:45", "10:38:18", numero=1839,
                 inicio_servicio="10:22:08", fin_servicio="10:38:20"),
    ])
    usos = excel_usos([("SAO-004", "10:22:12"), ("SAO-004", "10:22:17"),
                       ("SAO-004", "10:38:19"), ("SAO-004", "10:22:00")])
    r = analizar(usos, servicios, params)
    v = viaje(r, "SAO-004", "10:22:45")
    assert v["Inicio servicio"] == "10:22:08"
    assert v["Usos"] == 3                                    # 10:22:12, 10:22:17 y 10:38:19
    assert r.usos_sin_viaje["Hora"].tolist() == ["10:22:00"]  # antes del Inicio de Servicio
    # La duración y el mínimo siguen usando las horas efectivas
    assert v["Duración (min)"] == 15.6
    assert v["Mínimo (m)"] == round((15 + 33 / 60) * exigido("6019", params))


def test_usos_dentro_del_horario_de_servicio_exacto(params):
    servicios = excel_servicios([servicio("SAO-010", 6001, 9000, "06:00:00", "06:30:00")])
    usos = excel_usos([("SAO-010", "06:00:00"), ("SAO-010", "06:30:00"),
                       ("SAO-010", "05:59:59"), ("SAO-010", "06:30:01")])
    r = analizar(usos, servicios, params)
    assert viaje(r, "SAO-010", "06:00:00")["Usos"] == 2
    assert r.usos_sin_viaje["Hora"].tolist() == ["05:59:59", "06:30:01"]


def test_uso_sin_viaje_va_a_revisar_con_km_0(archivos_basicos, params):
    r = analizar(*archivos_basicos, params)
    s = r.usos_sin_viaje
    assert list(s.columns) == ["Vehículo", "Línea", "Fecha", "Hora", "Recorrido (m)", "Validación"]
    assert len(s) == 4                                        # 07:10, 05:40, 23:45, SAO-099
    assert (s["Recorrido (m)"] == 0).all()
    assert (s["Validación"] == Validacion.USO_SIN_VIAJE).all()
    assert s.iloc[0]["Fecha"] == "13/10/2026"
    # Bus que no aparece en el informe de servicios: también va a revisar
    assert "SAO-099" in s["Vehículo"].tolist()


def test_viaje_largo_que_contiene_otro(params):
    servicios = excel_servicios([
        servicio("SAO-020", 6002, 20000, "08:00:00", "10:00:00"),
        servicio("SAO-020", 6002, 1000, "08:30:00", "08:40:00"),
    ])
    r = analizar(excel_usos([("SAO-020", "09:00:00"), ("SAO-020", "08:35:00")]),
                 servicios, params)
    assert viaje(r, "SAO-020", "08:00:00")["Usos"] == 1      # 09:00 cae solo en el largo
    assert viaje(r, "SAO-020", "08:30:00")["Usos"] == 1      # 08:35 va al que empezó después
    assert r.usos_sin_viaje.empty


def test_viaje_que_cruza_medianoche_recibe_usos_de_madrugada(params):
    servicios = excel_servicios([
        servicio("SAO-005", 6001, 9000, "23:40:00", "00:20:00", fecha_fin="14/10/2026"),
    ])
    usos = excel_usos([("SAO-005", "23:50:00")])
    madrugada = excel_usos([("SAO-005", "00:10:00")], fecha="2026-10-14")
    todos = pd.concat([pd.read_excel(usos), pd.read_excel(madrugada)], ignore_index=True)
    archivo = BytesIO(); todos.to_excel(archivo, index=False); archivo.seek(0)
    r = analizar(archivo, servicios, params)
    v = viaje(r, "SAO-005", "23:40:00")
    assert v["Fin"] == "00:20:00 (+1 día)"
    assert v["Usos"] == 2


# ── Validaciones ──────────────────────────────────────────────────────────────

def test_validaciones(params):
    servicios = excel_servicios([
        servicio("SAO-030", 6025, 0, "06:00:00", "06:20:00"),       # sin km, con usos
        servicio("SAO-030", 6025, 0, "07:00:00", "07:20:00"),       # sin km, sin usos
        servicio("SAO-030", 6025, 1000, "08:00:00", "08:20:00"),    # km bajo con usos
        servicio("SAO-030", 6025, 1000, "09:00:00", "09:20:00"),    # km bajo sin usos
        servicio("SAO-030", 6025, 9000, "10:00:00", "10:20:00"),    # cumple
    ])
    usos = excel_usos([("SAO-030", "06:05:00"), ("SAO-030", "08:05:00"), ("SAO-030", "10:05:00")])
    r = analizar(usos, servicios, params)
    assert viaje(r, "SAO-030", "06:00:00")["Validación"] == Validacion.REVISAR
    assert viaje(r, "SAO-030", "07:00:00")["Validación"] == Validacion.NO_OPERO
    assert viaje(r, "SAO-030", "08:00:00")["Validación"] == Validacion.KM_BAJO
    assert viaje(r, "SAO-030", "09:00:00")["Validación"] == Validacion.OPERO
    assert viaje(r, "SAO-030", "10:00:00")["Validación"] == Validacion.OPERO


def test_ruta_sin_parametros_solo_revisa_sin_km(params):
    servicios = excel_servicios([servicio("SAO-011", 6017, 100, "06:00:00", "06:30:00")])
    r = analizar(excel_usos([("SAO-011", "06:05:00")]), servicios, params)
    v = viaje(r, "SAO-011", "06:00:00")
    assert pd.isna(v["Mínimo (m)"])
    assert v["Validación"] == Validacion.OPERO
    assert any("6017" in a for a in r.avisos)


def test_duplicado_en_cero_se_descarta(params):
    servicios = excel_servicios([
        servicio("SAO-007", 6014, 0, "07:00:00", "07:30:00"),
        servicio("SAO-007", 6014, 5000, "07:00:00", "07:30:00"),
        servicio("SAO-007", 6014, 0, "09:00:00", "09:30:00"),      # sin gemelo: se conserva
    ])
    r = analizar(excel_usos([("SAO-007", "07:10:00")]), servicios, params)
    assert len(r.viajes) == 2
    assert len(r.servicios) == 2
    assert any("descartaron 1" in a for a in r.avisos)


def test_resumen_une_viajes_a_revisar_y_grupos_sin_viaje(archivos_basicos, params):
    r = analizar(*archivos_basicos, params)
    assert r.resumen["Validación"].str.startswith("REVISAR").all()
    assert len(r.resumen) == r.indicadores["total_revisar"]
    assert r.indicadores["km_bajo"] == 1                      # SAO-002 05:00
    assert r.indicadores["usos_sin_viaje"] == 4
    assert r.indicadores["grupos_sin_viaje"] == 4             # todos separados
    assert len(r.resumen) == 5


# ── Agrupación de usos sin viaje ──────────────────────────────────────────────

def _grupos(r):
    return [(g["Vehículo"], g["Inicio"], g["Fin"], g["Usos"])
            for _, g in r.grupos_sin_viaje.iterrows()]


def test_agrupa_usos_seguidos_del_mismo_bus(params):
    servicios = excel_servicios([servicio("SAO-040", 6001, 9000, "08:00:00", "08:30:00")])
    usos = excel_usos([("SAO-040", "07:00:00"), ("SAO-040", "07:10:00"), ("SAO-040", "07:20:00"),
                       ("SAO-040", "07:50:00"),                       # 30 min después: otro grupo
                       ("SAO-041", "07:05:00")])                      # otro bus: otro grupo
    r = analizar(usos, servicios, params)
    assert _grupos(r) == [("SAO-040", "07:00:00", "07:20:00", 3),
                          ("SAO-040", "07:50:00", "07:50:00", 1),
                          ("SAO-041", "07:05:00", "07:05:00", 1)]
    assert r.grupos_sin_viaje.iloc[0]["Duración (min)"] == 20


def test_un_viaje_en_medio_separa_los_grupos(params):
    servicios = excel_servicios([servicio("SAO-042", 6001, 3000, "07:05:00", "07:08:00")])
    usos = excel_usos([("SAO-042", "07:00:00"), ("SAO-042", "07:10:00")])   # 10 min, viaje en medio
    r = analizar(usos, servicios, params)
    assert len(r.grupos_sin_viaje) == 2


def test_minutos_para_agrupar_es_configurable(params):
    servicios = excel_servicios([servicio("SAO-043", 6001, 9000, "08:00:00", "08:30:00")])
    usos = excel_usos([("SAO-043", "07:00:00"), ("SAO-043", "07:25:00")])   # 25 min
    params.minutos_agrupar_usos = 15
    assert len(analizar(usos, servicios, params).grupos_sin_viaje) == 2
    usos.seek(0); servicios.seek(0)
    params.minutos_agrupar_usos = 30
    assert len(analizar(usos, servicios, params).grupos_sin_viaje) == 1


def test_agrupa_por_ruta_si_el_archivo_de_usos_la_trae(params):
    servicios = excel_servicios([servicio("SAO-044", 6001, 9000, "08:00:00", "08:30:00")])
    df = pd.DataFrame({"Id": [1, 2, 3], "Fecha": ["2026-10-13"] * 3,
                       "Hora": ["07:00:00", "07:05:00", "07:10:00"],
                       "Equipo": ["SAO-044"] * 3, "Línea": [6001, 6001, 6002]})
    usos = BytesIO(); df.to_excel(usos, index=False); usos.seek(0)
    r = analizar(usos, servicios, params)
    assert [(g["Línea"], g["Usos"]) for _, g in r.grupos_sin_viaje.iterrows()] == [
        ("6001", 2), ("6002", 1)]


def test_indicadores(archivos_basicos, params):
    r = analizar(*archivos_basicos, params)
    assert r.indicadores["vehiculos"] == 2
    assert r.indicadores["viajes"] == 3
    assert r.indicadores["total_usuarios"] == 6
    assert r.indicadores["total_km"] == 24.5


# ── Errores de archivo ────────────────────────────────────────────────────────

def test_falta_columna_de_vehiculos(params):
    encabezados = ["Otra" if e == "Vehículos" else e for e in ENCABEZADOS_SERVICIOS]
    servicios = excel_servicios([servicio("SAO-001", 6023, 1000, "05:00:00", "05:30:00")],
                                encabezados=encabezados)
    with pytest.raises(ErrorDeArchivo, match="Vehículos"):
        analizar(excel_usos([("SAO-001", "05:10:00")]), servicios, params)


def test_error_muestra_encabezados_encontrados(params):
    encabezados = ["Otra" if e == "Vehículos" else e for e in ENCABEZADOS_SERVICIOS]
    servicios = excel_servicios([servicio("SAO-001", 6023, 1000, "05:00:00", "05:30:00")],
                                encabezados=encabezados)
    with pytest.raises(ErrorDeArchivo, match="Encabezados encontrados: #, Otra"):
        analizar(excel_usos([("SAO-001", "05:10:00")]), servicios, params)


def test_hoja_incorrecta(params):
    servicios = excel_servicios([], hoja="Otra")
    with pytest.raises(ErrorDeArchivo, match="Hoja1"):
        analizar(excel_usos([("SAO-001", "05:10:00")]), servicios, params)


def test_usos_de_otra_fecha(archivos_basicos, params):
    _, servicios = archivos_basicos
    with pytest.raises(ErrorDeArchivo, match="no tiene registros"):
        analizar(excel_usos([("SAO-001", "05:10:00")], fecha="2026-10-01"), servicios, params)


def test_archivos_invertidos(params):
    from openpyxl import Workbook
    usos = BytesIO()
    wb = Workbook(); ws = wb.active; ws.title = "Hoja1"
    ws.append(["Id", "Fecha", "Hora", "Equipo", "Línea"])
    ws.append([1, "2026-10-13", "05:00:00", "SAO-001", 6001])
    wb.save(usos); usos.seek(0)
    servicios = excel_servicios([servicio("SAO-001", 6023, 1000, "05:00:00", "05:30:00")])
    with pytest.raises(ErrorDeArchivo, match="cargaste el archivo de usos"):
        analizar(servicios, usos, params)


# ── Filtros y Excel ───────────────────────────────────────────────────────────

def test_filtro_linea_exacto():
    df = pd.DataFrame({"Línea": ["6025", "6025B", "6012, 6025", ""]})
    assert opciones_linea(df["Línea"]) == ["6012", "6025", "6025B"]
    assert aplicar_filtros(df, {"Línea": "6025"})["Línea"].tolist() == ["6025", "6012, 6025"]


def _leer_hojas(contenido: bytes) -> dict:
    """Lee cada hoja del informe tomando como encabezado la fila verde (la de los filtros)."""
    from openpyxl import load_workbook
    wb = load_workbook(BytesIO(contenido))
    hojas = {}
    for ws in wb.worksheets:
        encabezado = int(ws.freeze_panes[1:]) - 1
        hojas[ws.title] = pd.read_excel(BytesIO(contenido), sheet_name=ws.title,
                                        header=encabezado - 1)
    return hojas


def test_excel_generado(archivos_basicos, params):
    r = analizar(*archivos_basicos, params)
    contenido = generar_excel(r)
    hojas = _leer_hojas(contenido)
    assert list(hojas) == ["Informe de Servicios", "Usos", "Usos sin información en SAE",
                           "Usos sin info SAE - detalle", "Registros SAE", "Resumen", "Parámetros"]
    assert list(hojas["Registros SAE"].columns) == [
        "N° viaje", "Vehículo", "Línea", "Circulación", "Fecha", "Inicio servicio",
        "Fin servicio", "Inicio efectivo", "Fin efectivo", "Duración (min)",
        "Recorrido (m)", "Mínimo (m)", "Diferencia (m)", "Usos", "Validación"]
    assert len(hojas["Resumen"]) == r.indicadores["total_revisar"]
    assert len(hojas["Usos sin información en SAE"]) == 4                 # grupos
    assert len(hojas["Usos sin info SAE - detalle"]) == 4
    assert hojas["Informe de Servicios"]["Línea"].astype(str).tolist() == ["6023", "6025B", "6025"]
    assert len(hojas["Parámetros"].dropna(subset=["Línea"]).query("Línea.str.match('^6')",
                                                                  engine="python")) == 32
    from openpyxl import load_workbook
    wb = load_workbook(BytesIO(contenido))
    assert wb.active.title == "Resumen"                       # se abre en el Resumen
    assert wb["Resumen"]["A6"].value.startswith("=COUNTA(")   # indicadores con fórmulas


def test_porcentaje_exigido_cambia_el_minimo_del_viaje(archivos_basicos, params):
    params.porcentaje_exigido = 0.80
    r = analizar(*archivos_basicos, params)
    v = viaje(r, "SAO-001", "05:00:00")
    x_min = params.tabla_calculada().set_index("linea").loc["6023", "distancia_x_min"]
    assert v["Mínimo (m)"] == round(70 * x_min * 0.80)


def test_excel_usa_el_porcentaje_elegido(archivos_basicos, params):
    from openpyxl import load_workbook
    params.porcentaje_exigido = 0.90
    wb = load_workbook(BytesIO(generar_excel(analizar(*archivos_basicos, params))))
    ws = wb["Parámetros"]
    valores = [c.value for fila in ws.iter_rows() for c in fila]
    assert "Distancia al 90% x min (m)" in valores
    assert 0.90 in valores


def _usos_con_hora_de_excel() -> BytesIO:
    """Usos con la hora guardada como hora real de Excel (así vienen los archivos reales)."""
    from datetime import datetime, time
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(["Id", "Fecha", "Hora", "Equipo"])
    for i, (bus, hora) in enumerate([("SAO-001", time(5, 10)), ("SAO-099", time(9, 0, 15))]):
        ws.append([i, datetime(2026, 10, 13), hora, bus])
        ws.cell(row=ws.max_row, column=3).number_format = "h:mm:ss AM/PM"
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def _celda_bajo_titulo(ws, titulo):
    for fila in ws.iter_rows():
        for celda in fila:
            if celda.value == titulo:
                return ws.cell(row=celda.row + 1, column=celda.column)
    raise AssertionError(titulo)


def test_excel_hora_de_usos_en_formato_hora(archivos_basicos, params):
    from datetime import time
    _, servicios = archivos_basicos
    r = analizar(_usos_con_hora_de_excel(), servicios, params, "HABIL")
    wb = load_workbook(BytesIO(generar_excel(r)))
    hora = _celda_bajo_titulo(wb["Usos"], "Hora")
    assert hora.value == time(5, 10)
    assert hora.number_format == "HH:MM:SS"                 # no un decimal como 0,2153
    assert _celda_bajo_titulo(wb["Usos"], "Fecha").number_format == "DD/MM/YYYY"
    detalle = _celda_bajo_titulo(wb["Usos sin info SAE - detalle"], "Hora")
    assert isinstance(detalle.value, time) and detalle.number_format == "HH:MM:SS"


def test_excel_dice_el_tipo_de_dia(archivos_basicos, params):
    r = analizar(*archivos_basicos, params, "SABADO")
    assert r.tipo_dia == "SABADO"
    wb = load_workbook(BytesIO(generar_excel(r)))
    assert "SÁBADO" in wb["Resumen"]["A3"].value
