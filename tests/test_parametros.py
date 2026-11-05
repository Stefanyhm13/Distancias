import json

import pandas as pd
import pytest

from src.parametros import Parametros, cargar, guardar, parametros_iniciales, rutas_iniciales

# Valores del cuadro original: distancia al 95 % por minuto
CUADRO_ORIGINAL_95 = {
    "6001": 183.11, "6002": 208.85, "6004": 249.98, "6006C": 175.74,
    "6011": 132.46, "6016A": 212.99, "6019": 144.47, "6024": 195.83, "6025": 250.96,
    "6025B": 163.72,
}


def test_valores_iniciales_coinciden_con_el_cuadro():
    t = parametros_iniciales().tabla_calculada().set_index("linea")
    assert len(t) == 32
    for linea, valor in CUADRO_ORIGINAL_95.items():
        assert t.loc[linea, "distancia_95"] == pytest.approx(valor, abs=0.01)
    assert t.loc["6001", "distancia_x_min"] == pytest.approx(192.74, abs=0.01)


def test_columnas_calculadas_siguen_a_los_datos():
    p = Parametros(rutas_iniciales())
    p.rutas.loc[p.rutas["linea"] == "6001", ["distancia_ciclo_m", "tiempo_ciclo_min"]] = [6000, 30]
    fila = p.tabla_calculada().set_index("linea").loc["6001"]
    assert fila["distancia_x_min"] == 200
    assert fila["distancia_95"] == 190


def test_errores_de_validacion():
    rutas = pd.DataFrame({"linea": ["6001", "6001", "6002"],
                          "distancia_ciclo_m": [100, 100, 100],
                          "tiempo_ciclo_min": [10, 10, 0]})
    errores = " ".join(Parametros(rutas, minutos_agrupar_usos=0).errores())
    assert "entre 1 y 240" in errores
    assert "repetidas: 6001" in errores
    assert "6002" in errores
    assert parametros_iniciales().errores() == []


def test_guardar_y_cargar(tmp_path):
    archivo = tmp_path / "parametros.json"
    p = Parametros(rutas_iniciales(), minutos_agrupar_usos=25)
    p.rutas.loc[0, "distancia_ciclo_m"] = 9999
    guardar(p, archivo)
    leido, aviso = cargar(archivo)
    assert aviso is None
    assert leido.rutas.loc[0, "distancia_ciclo_m"] == 9999
    assert leido.minutos_agrupar_usos == 25


def test_carga_archivo_de_version_con_franjas(tmp_path):
    """Un parametros.json guardado por la versión anterior (con minutos_franja) sigue sirviendo."""
    archivo = tmp_path / "parametros.json"
    archivo.write_text(json.dumps({
        "minutos_franja": 30,
        "rutas": [{"linea": "6001", "distancia_ciclo_m": 5000, "tiempo_ciclo_min": 25}],
    }), encoding="utf-8")
    leido, aviso = cargar(archivo)
    assert aviso is None
    assert leido.distancia_95_por_linea() == {"6001": pytest.approx(190)}
    assert leido.minutos_agrupar_usos == 15                  # valor inicial


def test_archivo_danado_usa_iniciales(tmp_path):
    archivo = tmp_path / "parametros.json"
    archivo.write_text("no es json", encoding="utf-8")
    leido, aviso = cargar(archivo)
    assert len(leido.rutas) == 32
    assert "parámetros iniciales" in aviso


# ── Cumplimiento exigido (porcentaje) ─────────────────────────────────────────

def test_porcentaje_exigido_inicial_es_95():
    p = parametros_iniciales()
    assert p.porcentaje_exigido == 0.95
    assert p.pct == "95%"


def test_porcentaje_exigido_cambia_la_distancia_exigida():
    p = parametros_iniciales()
    p.porcentaje_exigido = 0.90
    t = p.tabla_calculada().set_index("linea")
    assert t.loc["6001", "distancia_95"] == pytest.approx(t.loc["6001", "distancia_x_min"] * 0.90)
    assert p.pct == "90%"
    assert "Distancia al 90% x min (m)" in p.tabla_para_mostrar().columns


def test_porcentaje_con_decimales_se_muestra_con_coma():
    p = parametros_iniciales()
    p.porcentaje_exigido = 0.925
    assert p.pct == "92,5%"


def test_porcentaje_fuera_de_rango_es_error():
    p = parametros_iniciales()
    p.porcentaje_exigido = 1.2
    assert any("cumplimiento exigido" in e for e in p.errores())
    p.porcentaje_exigido = 0
    assert any("cumplimiento exigido" in e for e in p.errores())


def test_porcentaje_se_guarda_y_se_carga(tmp_path):
    archivo = tmp_path / "parametros.json"
    p = parametros_iniciales()
    p.porcentaje_exigido = 0.9
    guardar(p, archivo)
    leido, aviso = cargar(archivo)
    assert aviso is None
    assert leido.porcentaje_exigido == pytest.approx(0.9)


def test_archivo_sin_porcentaje_usa_95(tmp_path):
    """parametros.json guardado antes de este cambio (sin porcentaje) sigue sirviendo."""
    archivo = tmp_path / "parametros.json"
    archivo.write_text(json.dumps({
        "rutas": [{"linea": "6001", "distancia_ciclo_m": 5000, "tiempo_ciclo_min": 25}],
    }), encoding="utf-8")
    leido, aviso = cargar(archivo)
    assert aviso is None
    assert leido.porcentaje_exigido == 0.95


# ── Parámetros por tipo de día ────────────────────────────────────────────────

from src.parametros import cargar_por_dia, guardar_por_dia, iniciales_por_dia  # noqa: E402


def test_por_dia_iniciales_son_iguales_para_los_tres():
    por_dia = iniciales_por_dia()
    assert set(por_dia) == {"HABIL", "SABADO", "DOMINGO"}
    assert {p.pct for p in por_dia.values()} == {"95%"}


def test_por_dia_se_guarda_y_carga_independiente(tmp_path):
    archivo = tmp_path / "parametros.json"
    por_dia = iniciales_por_dia()
    por_dia["SABADO"].porcentaje_exigido = 0.9
    por_dia["DOMINGO"].minutos_agrupar_usos = 30
    guardar_por_dia(por_dia, archivo)
    leido, aviso = cargar_por_dia(archivo)
    assert aviso is None
    assert leido["HABIL"].porcentaje_exigido == pytest.approx(0.95)
    assert leido["SABADO"].porcentaje_exigido == pytest.approx(0.9)
    assert leido["DOMINGO"].minutos_agrupar_usos == 30
    assert leido["HABIL"] is not leido["SABADO"]


def test_archivo_anterior_se_usa_para_los_tres_tipos(tmp_path):
    archivo = tmp_path / "parametros.json"
    p = parametros_iniciales()
    p.porcentaje_exigido = 0.9
    guardar(p, archivo)                       # formato anterior (un solo juego)
    leido, aviso = cargar_por_dia(archivo)
    assert aviso is None
    assert {t: x.porcentaje_exigido for t, x in leido.items()} == {
        "HABIL": pytest.approx(0.9), "SABADO": pytest.approx(0.9), "DOMINGO": pytest.approx(0.9)}
    leido["SABADO"].porcentaje_exigido = 0.5      # son copias independientes
    assert leido["HABIL"].porcentaje_exigido == pytest.approx(0.9)
