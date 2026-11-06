"""
Historial de días revisados (base de datos SQLite).

Cada día analizado se guarda con:
  - sus indicadores (km recorridos, km por recuperar, casos a revisar, ...),
  - el detalle de viajes / franjas que operaron o se deben revisar (para las métricas),
  - el informe Excel tal como se generó (para volver a descargarlo).

La base es un solo archivo (datos/historial.db) que se crea solo la primera vez.
No necesita instalar nada: SQLite viene incluido en Python.

Este archivo es igual en la versión por viajes y en la versión por franjas.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from config import ARCHIVO_BASE_DATOS, Validacion

RAIZ = Path(__file__).resolve().parent.parent
RUTA_BD = RAIZ / ARCHIVO_BASE_DATOS

USO_SIN_VIAJE = getattr(Validacion, "USO_SIN_VIAJE", "REVISAR - Uso sin viaje")

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS dias (
    fecha               TEXT PRIMARY KEY,   -- AAAA-MM-DD
    guardado_en         TEXT NOT NULL,
    archivo_usos        TEXT,
    archivo_servicios   TEXT,
    vehiculos           INTEGER,
    registros           INTEGER,            -- viajes o franjas del día
    usuarios            INTEGER,
    km_recorridos       REAL,
    km_por_recuperar    REAL,               -- km faltantes en casos Distancia 0 y Equivalencia
    casos_revisar       INTEGER,
    sin_km              INTEGER,
    km_bajo             INTEGER,
    usos_sin_viaje      INTEGER,
    porcentaje_exigido  REAL,
    tipo_dia            TEXT,               -- HABIL, SABADO o DOMINGO
    indicadores         TEXT,               -- JSON con todos los indicadores
    nombre_excel        TEXT,
    excel               BLOB
);
CREATE TABLE IF NOT EXISTS detalle (
    fecha        TEXT NOT NULL,
    vehiculo     TEXT,
    linea        TEXT,
    hora         TEXT,
    validacion   TEXT,
    recorrido_m  REAL,
    minimo_m     REAL,
    diferencia_m REAL,
    usos         INTEGER
);
CREATE INDEX IF NOT EXISTS idx_detalle_fecha ON detalle (fecha);
"""

COLUMNAS_DIAS = [
    "fecha", "guardado_en", "archivo_usos", "archivo_servicios", "vehiculos", "registros",
    "usuarios", "km_recorridos", "km_por_recuperar", "casos_revisar", "sin_km", "km_bajo",
    "usos_sin_viaje", "porcentaje_exigido", "tipo_dia",
]


def _conectar(ruta: Path | None = None) -> sqlite3.Connection:
    ruta = Path(ruta or RUTA_BD)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(ruta)
    con.executescript(_ESQUEMA)
    # Bases creadas antes de existir el tipo de día: se agrega la columna
    columnas = {fila[1] for fila in con.execute("PRAGMA table_info(dias)")}
    if "tipo_dia" not in columnas:
        con.execute("ALTER TABLE dias ADD COLUMN tipo_dia TEXT")
        con.commit()
    # Días guardados con los nombres anteriores de validación: se actualizan
    anteriores = getattr(Validacion, "ANTERIORES", {})
    viejos = [v for (v,) in con.execute("SELECT DISTINCT validacion FROM detalle")
              if v in anteriores]
    if viejos:
        con.executemany("UPDATE detalle SET validacion = ? WHERE validacion = ?",
                        [(anteriores[v], v) for v in viejos])
        con.commit()
    return con


def _texto_fecha(fecha) -> str:
    return pd.Timestamp(fecha).strftime("%Y-%m-%d")


# ── Del resultado del análisis a filas de la base ─────────────────────────────

def _tabla_principal(resultado) -> pd.DataFrame:
    """Viajes (versión por viajes) o consolidado de franjas (versión por franjas)."""
    if hasattr(resultado, "viajes"):
        return resultado.viajes
    return resultado.consolidado


def detalle_del_dia(resultado) -> pd.DataFrame:
    """Filas que sirven para las métricas: todo lo que operó o se debe revisar.

    Los registros "No operó" (sin distancia ni usos) no aportan a las métricas y
    en la versión por franjas son la mayoría, así que no se guardan.
    """
    principal = _tabla_principal(resultado)
    hora = "Inicio" if "Inicio" in principal.columns else "Franja Inicio"
    partes = [principal.assign(_hora=principal[hora])]
    grupos = getattr(resultado, "grupos_sin_viaje", None)
    if grupos is not None and not grupos.empty:
        partes.append(grupos.assign(_hora=grupos["Inicio"]))
    tabla = pd.concat(partes, ignore_index=True)
    tabla = tabla[tabla["Validación"] != Validacion.NO_OPERO]

    def numero(col):
        if col not in tabla:
            return pd.Series(float("nan"), index=tabla.index)
        return pd.to_numeric(tabla[col], errors="coerce").astype(float)

    return pd.DataFrame({
        "vehiculo": tabla["Vehículo"].astype(str),
        "linea": tabla["Línea"].fillna("").astype(str),
        "hora": tabla["_hora"].fillna("").astype(str),
        "validacion": tabla["Validación"].astype(str),
        "recorrido_m": numero("Recorrido (m)"),
        "minimo_m": numero("Mínimo (m)"),
        "diferencia_m": numero("Diferencia (m)"),
        "usos": pd.to_numeric(tabla["Usos"], errors="coerce").fillna(0).astype(int),
    }).reset_index(drop=True)


def km_por_recuperar(detalle: pd.DataFrame) -> pd.Series:
    """Km faltantes de cada fila: lo que le faltó para el mínimo en REVISAR y Km bajo."""
    a_revisar = detalle["validacion"].isin([Validacion.REVISAR, Validacion.KM_BAJO])
    faltante = (-detalle["diferencia_m"]).clip(lower=0).fillna(0)
    return (faltante.where(a_revisar, 0)) / 1000


def resumen_del_dia(resultado, detalle: pd.DataFrame) -> dict:
    ind = resultado.indicadores
    return {
        "vehiculos": int(ind.get("vehiculos", 0)),
        "registros": int(ind.get("viajes", len(_tabla_principal(resultado)))),
        "usuarios": int(ind.get("total_usuarios", 0)),
        "km_recorridos": float(ind.get("total_km", 0)),
        "km_por_recuperar": round(float(km_por_recuperar(detalle).sum()), 1),
        "casos_revisar": int(ind.get("total_revisar", 0)),
        "sin_km": int(ind.get("revisar", 0)),
        "km_bajo": int(ind.get("km_bajo", 0)),
        "usos_sin_viaje": int(ind.get("usos_sin_viaje", 0)),
        "porcentaje_exigido": float(resultado.parametros.porcentaje_exigido),
        "tipo_dia": getattr(resultado, "tipo_dia", "") or None,
    }


def _a_json(valor):
    if hasattr(valor, "item"):
        return valor.item()
    return str(valor)


# ── Operaciones ───────────────────────────────────────────────────────────────

def existe(fecha, ruta: Path | None = None) -> bool:
    with closing(_conectar(ruta)) as con:
        fila = con.execute("SELECT 1 FROM dias WHERE fecha = ?", (_texto_fecha(fecha),)).fetchone()
    return fila is not None


def guardado_en(fecha, ruta: Path | None = None) -> str | None:
    with closing(_conectar(ruta)) as con:
        fila = con.execute("SELECT guardado_en FROM dias WHERE fecha = ?",
                           (_texto_fecha(fecha),)).fetchone()
    return fila[0] if fila else None


def guardar(resultado, excel: bytes, nombre_excel: str, archivo_usos: str = "",
            archivo_servicios: str = "", ruta: Path | None = None) -> None:
    """Guarda (o reemplaza) el día del resultado, en una sola transacción."""
    fecha = _texto_fecha(resultado.fecha)
    detalle = detalle_del_dia(resultado)
    resumen = resumen_del_dia(resultado, detalle)
    fila = {
        "fecha": fecha,
        "guardado_en": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "archivo_usos": archivo_usos,
        "archivo_servicios": archivo_servicios,
        **resumen,
        "indicadores": json.dumps(resultado.indicadores, default=_a_json, ensure_ascii=False),
        "nombre_excel": nombre_excel,
        "excel": sqlite3.Binary(excel),
    }
    with closing(_conectar(ruta)) as con, con:
        con.execute("DELETE FROM detalle WHERE fecha = ?", (fecha,))
        con.execute("DELETE FROM dias WHERE fecha = ?", (fecha,))
        columnas = ", ".join(fila)
        marcas = ", ".join("?" for _ in fila)
        con.execute(f"INSERT INTO dias ({columnas}) VALUES ({marcas})", list(fila.values()))
        filas = detalle.assign(fecha=fecha)[
            ["fecha", "vehiculo", "linea", "hora", "validacion",
             "recorrido_m", "minimo_m", "diferencia_m", "usos"]]
        filas = filas.astype(object).where(filas.notna(), None)
        con.executemany("INSERT INTO detalle VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        filas.itertuples(index=False, name=None))


def eliminar(fecha, ruta: Path | None = None) -> None:
    fecha = _texto_fecha(fecha)
    with closing(_conectar(ruta)) as con, con:
        con.execute("DELETE FROM detalle WHERE fecha = ?", (fecha,))
        con.execute("DELETE FROM dias WHERE fecha = ?", (fecha,))


def eliminar_varios(fechas: list, ruta: Path | None = None) -> int:
    """Borra varios días del historial (resumen, detalle y Excel) y libera el espacio.
    Devuelve cuántos días se borraron."""
    textos = [(_texto_fecha(f),) for f in fechas]
    if not textos:
        return 0
    with closing(_conectar(ruta)) as con, con:
        con.executemany("DELETE FROM detalle WHERE fecha = ?", textos)
        borrados = con.executemany("DELETE FROM dias WHERE fecha = ?", textos).rowcount
    compactar(ruta)
    return borrados


def compactar(ruta: Path | None = None) -> None:
    """SQLite no devuelve al disco el espacio de lo que se borra: VACUUM lo reescribe
    sin ese espacio vacío para que el archivo de verdad quede más pequeño."""
    ruta = Path(ruta or RUTA_BD)
    if not ruta.exists():
        return
    with closing(sqlite3.connect(ruta)) as con:
        con.execute("VACUUM")


def tamano_bd(ruta: Path | None = None) -> int:
    """Tamaño del archivo de la base de datos, en bytes."""
    ruta = Path(ruta or RUTA_BD)
    return ruta.stat().st_size if ruta.exists() else 0


def dias(ruta: Path | None = None) -> pd.DataFrame:
    """Todos los días guardados (sin el Excel), con columnas de año, mes y día."""
    with closing(_conectar(ruta)) as con:
        tabla = pd.read_sql_query(
            f"SELECT {', '.join(COLUMNAS_DIAS)} FROM dias ORDER BY fecha", con)
    tabla["fecha"] = pd.to_datetime(tabla["fecha"])
    tabla["anio"] = tabla["fecha"].dt.year
    tabla["mes"] = tabla["fecha"].dt.month
    tabla["dia"] = tabla["fecha"].dt.day
    return tabla


def detalle(fechas: list, ruta: Path | None = None) -> pd.DataFrame:
    """Detalle de las fechas indicadas, con la columna km_por_recuperar calculada."""
    textos = [_texto_fecha(f) for f in fechas]
    if not textos:
        return pd.DataFrame(columns=["fecha", "vehiculo", "linea", "hora", "validacion",
                                     "recorrido_m", "minimo_m", "diferencia_m", "usos",
                                     "km_por_recuperar"])
    with closing(_conectar(ruta)) as con:
        con.execute("CREATE TEMP TABLE _f (fecha TEXT)")
        con.executemany("INSERT INTO _f VALUES (?)", [(t,) for t in textos])
        tabla = pd.read_sql_query(
            "SELECT d.* FROM detalle d JOIN _f USING (fecha)", con)
    tabla["km_por_recuperar"] = km_por_recuperar(tabla)
    return tabla


def excel(fecha, ruta: Path | None = None) -> tuple[bytes, str] | None:
    """(contenido, nombre de archivo) del informe guardado de ese día."""
    with closing(_conectar(ruta)) as con:
        fila = con.execute("SELECT excel, nombre_excel FROM dias WHERE fecha = ?",
                           (_texto_fecha(fecha),)).fetchone()
    if not fila or fila[0] is None:
        return None
    return bytes(fila[0]), fila[1]
