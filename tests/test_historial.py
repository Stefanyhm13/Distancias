"""Base de datos del historial: guardar, reemplazar, consultar y descargar."""
import pandas as pd
import pytest

from config import Validacion
from src import historial as bd
from src.analisis import analizar
from src.reporte_excel import generar_excel, nombre_archivo
from tests.conftest import excel_servicios, excel_usos, servicio


@pytest.fixture
def ruta(tmp_path):
    return tmp_path / "historial.db"


def _resultado(params, fecha="13/10/2026", fecha_usos="2026-10-13", distancia=500):
    servicios = excel_servicios([
        servicio("SAO-001", 6023, 21000, "05:00:00", "06:10:00", fecha=fecha),
        servicio("SAO-002", 6025, distancia, "05:00:00", "05:20:00", fecha=fecha),
        servicio("SAO-003", 6025, 0, "07:00:00", "07:20:00", fecha=fecha),
    ])
    usos = excel_usos([("SAO-001", "05:10:00"), ("SAO-002", "05:05:00"),
                       ("SAO-003", "07:05:00"), ("SAO-001", "09:00:00")], fecha=fecha_usos)
    return analizar(usos, servicios, params)


def test_guardar_y_consultar(params, ruta):
    r = _resultado(params)
    assert not bd.existe(r.fecha, ruta)
    excel = generar_excel(r)
    bd.guardar(r, excel, nombre_archivo(r), "Usos.xlsx", "Servicios.xlsx", ruta=ruta)

    assert bd.existe(r.fecha, ruta)
    dias = bd.dias(ruta)
    assert len(dias) == 1
    dia = dias.iloc[0]
    assert (dia["anio"], dia["mes"], dia["dia"]) == (2026, 10, 13)
    assert dia["km_recorridos"] == r.indicadores["total_km"]
    assert dia["casos_revisar"] == r.indicadores["total_revisar"]

    contenido, nombre = bd.excel(r.fecha, ruta)
    assert contenido == excel and nombre == nombre_archivo(r)


def test_km_por_recuperar_es_lo_que_falta_al_minimo(params, ruta):
    r = _resultado(params)
    bd.guardar(r, b"x", "x.xlsx", ruta=ruta)
    detalle = bd.detalle([r.fecha], ruta)
    revisar = detalle[detalle["validacion"].isin([Validacion.REVISAR, Validacion.KM_BAJO])]
    assert not revisar.empty
    esperado = (-revisar["diferencia_m"]).clip(lower=0).sum() / 1000
    assert bd.dias(ruta).iloc[0]["km_por_recuperar"] == pytest.approx(esperado, abs=0.05)
    assert esperado > 0
    # Lo que operó bien no aporta km por recuperar
    assert (detalle.loc[detalle["validacion"] == Validacion.OPERO, "km_por_recuperar"] == 0).all()
    # Los "No operó" no se guardan en el detalle
    assert Validacion.NO_OPERO not in set(detalle["validacion"])


def test_reemplazar_un_dia_no_duplica(params, ruta):
    r1 = _resultado(params, distancia=500)
    bd.guardar(r1, b"uno", "a.xlsx", ruta=ruta)
    filas_antes = len(bd.detalle([r1.fecha], ruta))
    r2 = _resultado(params, distancia=6000)
    bd.guardar(r2, b"dos", "a.xlsx", ruta=ruta)

    assert len(bd.dias(ruta)) == 1
    assert len(bd.detalle([r1.fecha], ruta)) == filas_antes
    assert bd.excel(r1.fecha, ruta)[0] == b"dos"


def test_varios_dias_y_eliminar(params, ruta):
    a = _resultado(params, "13/10/2026", "2026-10-13")
    b = _resultado(params, "02/11/2026", "2026-11-02")
    bd.guardar(a, b"a", "a.xlsx", ruta=ruta)
    bd.guardar(b, b"b", "b.xlsx", ruta=ruta)
    dias = bd.dias(ruta)
    assert list(dias["mes"]) == [10, 11]
    assert set(bd.detalle(list(dias["fecha"]), ruta)["fecha"]) == {"2026-10-13", "2026-11-02"}

    bd.eliminar(a.fecha, ruta)
    assert list(bd.dias(ruta)["fecha"]) == [pd.Timestamp("2026-11-02")]
    assert bd.excel(a.fecha, ruta) is None
    assert bd.detalle([a.fecha], ruta).empty


def test_base_vacia(ruta):
    assert bd.dias(ruta).empty
    assert bd.detalle([], ruta).empty
