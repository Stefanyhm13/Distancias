"""Pruebas del PSO y del consolidado de reclamación por quincena."""
from datetime import date, datetime
from io import BytesIO

import pandas as pd
import pytest
from openpyxl import Workbook, load_workbook

from config import REVISION_DETALLADA
from tests.conftest import excel_servicios, excel_usos, servicio
from src import consolidado as C
from src import pso as P
from src.analisis import analizar
from src.normalizacion import normalizar_circulacion
from src.reporte_consolidado import COLUMNAS_RESUMEN, generar_consolidado

FECHA = "04/10/2026"           # domingo


def excel_pso(salidas) -> BytesIO:
    """salidas: [(tipo día, ruta, circulación, 'HH:MM', distancia)] en las columnas O-S,
    con columnas A-N de relleno (K se llama 'Tipo Dia', como en el archivo real)."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Horarios"
    relleno = ["Datos Generales Empresa", "Código Línea", "Línea", "Código Itinerario",
               "Itinerario", "Día Operativo", "Expedición", "Tipo Exp", "Calendario",
               "Periodo", "Tipo Dia", "Turno", "Origen", "Destino"]
    ws.append(relleno + P.COLUMNAS_PSO)
    for tipo, ruta, circ, hora, dist in salidas:
        ws.append(["SAO", ruta, "", "", "", "", hora, "", "", "", "LV", circ, "", "",
                   tipo, ruta, circ, hora, dist])
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


SALIDAS_6016 = [("Domingo", 6016, "503", h, d) for h, d in
                [("06:08", 6152), ("06:34", 6117), ("06:59", 6152), ("07:29", 6117),
                 ("07:59", 6152)]]


@pytest.fixture
def pso():
    return P.estandarizar(P.leer_pso(excel_pso(SALIDAS_6016 + [
        ("Domingo", "6006C", "810", "07:54", 1300), ("Domingo", "6006C", "810", "08:02", 1900),
        ("Domingo", 6018, "30", "12:39", 3700), ("Domingo", 6018, "30", "13:01", 3376),
    ])))


@pytest.fixture
def bd(tmp_path, monkeypatch):
    ruta = tmp_path / "historial.db"
    monkeypatch.setattr("src.historial.RUTA_BD", ruta)
    return ruta


def _dt(hora, dia=4):
    return datetime.strptime(f"2026-10-{dia:02d} {hora}", "%Y-%m-%d %H:%M:%S")


# ── Circulación y PSO ─────────────────────────────────────────────────────────

def test_circulacion_del_informe():
    assert normalizar_circulacion("0-503") == "503"
    assert normalizar_circulacion("0-053") == "53"
    assert normalizar_circulacion(461) == "461"
    assert normalizar_circulacion("461.0") == "461"
    assert normalizar_circulacion(None) is None


def test_pso_usa_columnas_o_a_s(pso):
    assert set(pso["tipo"]) == {"DOMINGO"}
    assert "6016" in set(pso["ruta"])


def test_regla_del_ejemplo_06_30_a_07_00(pso):
    """06:34 termina 06:59 (dentro del caso); 06:59 termina 07:29 (fuera)."""
    r = P.itinerarios_del_caso(pso, "DOMINGO", "6016", "503", _dt("06:30:00"),
                               _dt("07:00:28"), date(2026, 10, 4))
    assert r["Hora"].tolist() == ["06:34"]
    assert r["Distancia Media"].sum() == 6117


def test_regla_varios_itinerarios(pso):
    r = P.itinerarios_del_caso(pso, "DOMINGO", "6016", "503", _dt("06:30:00"),
                               _dt("07:35:00"), date(2026, 10, 4))
    assert r["Hora"].tolist() == ["06:34", "06:59"]


def test_ultimo_itinerario_usa_duracion_tipica(pso):
    """07:59 es la última salida: dura lo típico (~30 min)."""
    r = P.itinerarios_del_caso(pso, "DOMINGO", "6016", "503", _dt("07:55:00"),
                               _dt("08:20:00"), date(2026, 10, 4))
    assert r["Hora"].tolist() == ["07:59"]


def test_ruta_con_c_en_el_pso(pso):
    r = P.itinerarios_del_caso(pso, "DOMINGO", "6006", "810", _dt("07:50:00"),
                               _dt("08:12:00"), date(2026, 10, 4))
    assert r["Hora"].tolist() == ["07:54", "08:02"]


def test_otro_tipo_de_dia_no_encuentra(pso):
    r = P.itinerarios_del_caso(pso, "HABIL", "6016", "503", _dt("06:30:00"),
                               _dt("07:00:28"), date(2026, 10, 4))
    assert r.empty


def test_archivo_sin_hoja_horarios():
    wb = Workbook()
    wb.active.append(["a", "b"])
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    with pytest.raises(Exception, match="Horarios"):
        P.leer_pso(buffer)


# ── Análisis: circulación y datos de cada caso ────────────────────────────────

def _analizar(params):
    servicios = excel_servicios([
        servicio("SAO-008", 6016, 0, "06:30:00", "07:00:28", fecha=FECHA, numero=633,
                 ht="0-503"),
        servicio("SAO-008", 6016, 0, "07:03:10", "07:28:40", fecha=FECHA, numero=634,
                 ht="0-503"),
        servicio("SAO-008", 6016, 12000, "07:31:00", "08:30:00", fecha=FECHA, numero=635,
                 ht="0-503"),
        servicio("SAO-008", 6016, 0, "11:18:33", "12:03:16", fecha=FECHA, numero=636,
                 ht="0-503"),
        servicio("SAO-009", 6018, 6, "12:34:34", "13:01:54", fecha=FECHA, numero=2563,
                 ht="0-30"),
    ])
    usos = excel_usos([("SAO-008", "06:31:00")] * 28 + [("SAO-008", "07:05:00")] * 15
                      + [("SAO-008", "11:20:00")] * 7 + [("SAO-009", "12:40:00")] * 7
                      + [("SAO-021", "16:00:00")] * 4, fecha="2026-10-04")
    return analizar(usos, servicios, params, "DOMINGO")


def test_circulacion_en_tablas(params):
    r = _analizar(params)
    assert "Circulación" in r.viajes.columns and "Circulación" in r.resumen.columns
    assert set(r.viajes["Circulación"]) == {"503", "30"}
    assert len(r.casos) == len(r.resumen)
    assert r.casos[0]["servicios"].shape[0] == 1
    assert len(r.casos[0]["usos"]) == r.resumen.loc[0, "Usos"]


def test_casos_seguidos_se_unen(params, pso):
    r = _analizar(params)
    todos = list(range(len(r.resumen)))
    registros = C.preparar_casos(r, todos, pso)
    unidos = [x for x in registros if x.unidad == "SAO-008" and len(x.claves) == 2]
    assert len(unidos) == 1
    caso = unidos[0]
    assert (caso.inicio, caso.fin) == (pd.Timestamp(_dt("06:30:00")),
                                       pd.Timestamp(_dt("07:28:40")))
    assert caso.usuarios == 43
    assert caso.pso["Hora"].tolist() == ["06:34", "06:59"]
    assert caso.distancia_km == pytest.approx(12.269)
    # El de las 11:18 no es seguido: queda aparte
    assert any(x.unidad == "SAO-008" and x.inicio.hour == 11 for x in registros)


def test_solo_se_unen_si_se_seleccionan_los_dos(params, pso):
    r = _analizar(params)
    registros = C.preparar_casos(r, [0], pso)
    assert len(registros) == 1 and len(registros[0].claves) == 1


def test_usos_sin_sae_quedan_en_revision_detallada(params, pso):
    r = _analizar(params)
    posicion = next(i for i, c in enumerate(r.casos) if c["tipo"] == "sin_sae")
    caso = C.preparar_casos(r, [posicion], pso)[0]
    assert caso.ruta == caso.circulacion == REVISION_DETALLADA
    assert caso.distancia_km is None
    assert caso.servicios.empty and len(caso.usos) == 4


# ── Base de datos y quincenas ─────────────────────────────────────────────────

def test_quincenas():
    q1, q2 = C.Quincena.de(date(2026, 10, 15)), C.Quincena.de(date(2026, 10, 16))
    assert (q1.numero, q2.numero) == (1, 2)
    assert q1.nombre_archivo == "Acumulado GPS Octubre Q1.xlsx"
    assert q2.dias == (16, 31)
    assert C.Quincena.de(date(2026, 9, 20)).dias == (16, 30)
    assert q1.titulo == "Acumulado novedad perdida de GPS Octubre Q1"


def test_agregar_no_repite_casos(params, pso, bd):
    r = _analizar(params)
    registros = C.preparar_casos(r, list(range(len(r.resumen))), pso)
    assert C.agregar(registros) == (len(registros), 0)
    assert C.agregar(registros[:1]) == (0, 1)
    q = C.Quincena.de(r.fecha)
    assert len(C.casos(q)) == len(registros)
    assert C.claves_guardadas(q) >= set(registros[0].claves)


def test_casos_de_otro_dia_se_ordenan_por_fecha(params, pso, bd):
    r = _analizar(params)
    registros = C.preparar_casos(r, [0], pso)
    otro = C.CasoReclamo(**{**registros[0].__dict__, "fecha": date(2026, 10, 2),
                            "inicio": pd.Timestamp(_dt("09:00:00", 2)),
                            "fin": pd.Timestamp(_dt("09:30:00", 2)), "claves": ["otro"]})
    C.agregar(registros)
    C.agregar([otro])                                     # se agrega después, es de antes
    fechas = [c.fecha for c in C.casos(C.Quincena.de(r.fecha))]
    assert fechas == sorted(fechas) and fechas[0] == date(2026, 10, 2)


def test_corregir_ruta_recalcula_con_pso(params, pso, bd):
    r = _analizar(params)
    posicion = next(i for i, c in enumerate(r.casos) if c["tipo"] == "sin_sae")
    C.agregar(C.preparar_casos(r, [posicion], pso))
    caso = C.casos(C.Quincena.de(r.fecha))[0]
    corregido = C.actualizar(caso.id, "6016", "503", None, pso)
    assert corregido.ruta == "6016" and not corregido.distancia_manual
    manual = C.actualizar(caso.id, "6016", "503", 5.5, pso)
    assert manual.distancia_km == 5.5 and manual.distancia_manual


def test_pso_se_guarda_en_la_base(bd):
    hoja = P.leer_pso(excel_pso(SALIDAS_6016))
    C.guardar_pso(hoja, "Horarios.xlsx")
    assert C.info_pso()["filas"] == len(hoja)
    original, estandar = C.cargar_pso()
    assert len(original) == len(hoja) and len(estandar) == len(SALIDAS_6016)


# ── Excel del consolidado ─────────────────────────────────────────────────────

def test_excel_del_consolidado(params, pso, bd):
    r = _analizar(params)
    registros = C.preparar_casos(r, list(range(len(r.resumen))), pso)
    C.agregar(registros)
    q = C.Quincena.de(r.fecha)
    hoja = P.leer_pso(excel_pso(SALIDAS_6016))
    contenido = generar_consolidado(q, C.casos(q), hoja)
    wb = load_workbook(BytesIO(contenido))
    assert wb.sheetnames == ["Horarios", "Resumen", "Evidencia"]
    ws = wb["Resumen"]
    assert ws["A1"].value == q.titulo
    assert [c.value for c in ws[3]][:9] == COLUMNAS_RESUMEN
    n = len(registros)
    for fila in range(4, 4 + n):
        enlace = ws.cell(fila, 8)
        assert enlace.hyperlink.location.startswith("Evidencia!A")
        destino = int(enlace.hyperlink.location.split("!A")[1])
        assert wb["Evidencia"].cell(destino, 1).value.startswith("Unidad C6-")
    assert ws.cell(4 + n, 8).value == "Total"
    assert ws.cell(4 + n, 9).value == f"=SUM(I4:I{3 + n})"
    # Distancia de un caso con PSO: fórmula a su total en Evidencia (suma / 1000)
    con_pso = [i for i, c in enumerate(C.casos(q)) if c.distancia_km is not None]
    formula = ws.cell(4 + con_pso[0], 9).value
    assert formula.startswith("=Evidencia!$E$")
    total = wb["Evidencia"][formula.split("!")[1].replace("$", "")].value
    assert total.startswith("=SUM(E") and total.endswith("/1000")
    # Casos sin SAE: REVISION DETALLADA y sin distancia
    filas = {ws.cell(f, 3).value: ws.cell(f, 9).value for f in range(4, 4 + n)}
    assert filas[REVISION_DETALLADA] is None


def test_equivalencia_reclama_lo_que_falta(params, pso, bd):
    """SAE registró 6 m; el PSO dice 3.700 m: se reclaman 3,694 km."""
    r = _analizar(params)
    posicion = next(i for i, c in enumerate(r.casos) if c["vehiculo"] == "SAO-009")
    caso = C.preparar_casos(r, [posicion], pso)[0]
    assert caso.equivalencia
    assert caso.pso["Hora"].tolist() == ["12:39"]
    assert caso.distancia_km == pytest.approx(3.694)
    C.agregar([caso])
    q = C.Quincena.de(r.fecha)
    wb = load_workbook(BytesIO(generar_consolidado(q, C.casos(q), None)))
    formula = wb["Resumen"]["I4"].value
    celda = formula.split("!")[1].replace("$", "")
    ev = wb["Evidencia"]
    fila = int(celda[1:])
    assert ev[celda].value == f"=MAX(E{fila - 2}-E{fila - 1},0)"
    assert ev[f"E{fila - 1}"].value == pytest.approx(0.006)
    assert ev[f"E{fila - 2}"].value.startswith("=SUM(E")


def test_pso_lee_la_hoja_completa():
    hoja = P.leer_pso(excel_pso(SALIDAS_6016))
    assert list(hoja.columns)[:2] == ["Datos Generales Empresa", "Código Línea"]
    assert len(hoja.columns) == 19 and len(hoja) == len(SALIDAS_6016)


def test_borrar_consolidados_de_quincenas(params, pso, bd, tmp_path):
    r = _analizar(params)
    registros = C.preparar_casos(r, list(range(len(r.resumen))), pso)
    C.agregar(registros)
    q = C.Quincena.de(r.fecha)
    carpeta = tmp_path / "consolidados"
    carpeta.mkdir()
    (carpeta / q.nombre_archivo).write_bytes(b"excel")

    assert C.eliminar_quincenas([q], carpeta=carpeta) == (len(registros), 1)
    assert C.quincenas() == []
    assert C.casos(q) == []
    assert not (carpeta / q.nombre_archivo).exists()
    assert C.eliminar_quincenas([], carpeta=carpeta) == (0, 0)
