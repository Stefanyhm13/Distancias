"""
Consolidado de reclamación de km por quincena (Q1: días 1 a 15, Q2: 16 a fin de mes).

Flujo:
  1. En la app se marcan los casos del día que se van a reclamar.
  2. `preparar_casos` arma un registro por caso: une los casos seguidos de la misma
     unidad, ruta y circulación, y busca en el PSO los itinerarios que se reclaman.
  3. `agregar` los guarda en la base de datos, en la quincena que les corresponde.
     Si un caso ya estaba en el consolidado, no se repite.
  4. El Excel de la quincena se arma siempre con TODOS los casos guardados de esa
     quincena, ordenados por fecha y hora (ver src/reporte_consolidado.py).

Todo vive en la misma base del historial (datos/historial.db).
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass, field
from datetime import date, datetime, time
from pathlib import Path

import numpy as np
import pandas as pd

from config import CARPETA_CONSOLIDADOS, MINUTOS_CASOS_SEGUIDOS, REVISION_DETALLADA
from src import pso as modulo_pso
from src.historial import RUTA_BD, _conectar, compactar
from src.normalizacion import numero_bus

RAIZ = Path(__file__).resolve().parent.parent
CARPETA = RAIZ / CARPETA_CONSOLIDADOS

MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto",
         "Septiembre", "Octubre", "Noviembre", "Diciembre"]

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS pso (
    id          INTEGER PRIMARY KEY CHECK (id = 1),   -- un solo PSO vigente
    nombre      TEXT,
    cargado_en  TEXT,
    filas       INTEGER,
    hoja        TEXT                                    -- hoja Horarios en JSON
);
CREATE TABLE IF NOT EXISTS consolidado_casos (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    quincena         TEXT NOT NULL,          -- AAAA-MM-Q1 / AAAA-MM-Q2
    fecha            TEXT NOT NULL,          -- AAAA-MM-DD
    tipo             TEXT,                   -- viaje / sin_sae
    tipo_dia         TEXT,                   -- HABIL / SABADO / DOMINGO
    unidad           TEXT,                   -- como en el informe (SAO-008)
    ruta             TEXT,
    circulacion      TEXT,
    inicio           TEXT,                   -- AAAA-MM-DD HH:MM:SS
    fin              TEXT,
    usuarios         INTEGER,
    recorrido_m      REAL,                   -- lo que registró SAE
    distancia_km     REAL,                   -- distancia a reclamar (vacía si no se sabe)
    distancia_manual INTEGER DEFAULT 0,      -- 1 si se escribió a mano en la app
    claves           TEXT,                   -- casos del día que forman este registro
    servicios        TEXT,                   -- evidencia: filas del informe de servicios
    usos             TEXT,                   -- evidencia: usos
    pso              TEXT,                   -- evidencia: itinerarios del PSO
    agregado_en      TEXT
);
CREATE INDEX IF NOT EXISTS idx_consolidado_quincena ON consolidado_casos (quincena);
"""


def _conexion(ruta: Path | None = None) -> sqlite3.Connection:
    con = _conectar(ruta)
    con.executescript(_ESQUEMA)
    return con


# ── Quincenas ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Quincena:
    anio: int
    mes: int
    numero: int                        # 1 o 2

    @classmethod
    def de(cls, fecha) -> "Quincena":
        f = pd.Timestamp(fecha)
        return cls(f.year, f.month, 1 if f.day <= 15 else 2)

    @classmethod
    def desde_clave(cls, clave: str) -> "Quincena":
        anio, mes, q = clave.split("-")
        return cls(int(anio), int(mes), int(q[1]))

    @property
    def clave(self) -> str:
        return f"{self.anio}-{self.mes:02d}-Q{self.numero}"

    @property
    def nombre(self) -> str:
        return f"{MESES[self.mes - 1]} Q{self.numero}"            # Octubre Q1

    @property
    def dias(self) -> tuple[int, int]:
        ultimo = pd.Timestamp(self.anio, self.mes, 1).days_in_month
        return (1, 15) if self.numero == 1 else (16, ultimo)

    @property
    def rango(self) -> str:
        desde, hasta = self.dias
        return f"{desde:02d} al {hasta:02d} de {MESES[self.mes - 1].lower()} de {self.anio}"

    @property
    def titulo(self) -> str:
        return f"Acumulado novedad perdida de GPS {self.nombre}"

    @property
    def nombre_archivo(self) -> str:
        return f"Acumulado GPS {MESES[self.mes - 1]} Q{self.numero}.xlsx"


# ── Tablas <-> JSON (conservando fechas y horas) ──────────────────────────────

def _celda_a_json(valor):
    if valor is None or (not isinstance(valor, (str, bytes, time)) and pd.isna(valor)):
        return None
    if isinstance(valor, (pd.Timestamp, datetime)):
        return {"dt": pd.Timestamp(valor).isoformat()}
    if isinstance(valor, date):
        return {"d": valor.isoformat()}
    if isinstance(valor, time):
        return {"t": valor.isoformat()}
    if isinstance(valor, pd.Timedelta):
        return {"td": valor.total_seconds()}
    if isinstance(valor, np.generic):
        return valor.item()
    if isinstance(valor, (int, float, str, bool)):
        return valor
    return str(valor)


def _celda_desde_json(valor):
    if isinstance(valor, dict):
        if "dt" in valor:
            return pd.Timestamp(valor["dt"]).to_pydatetime()
        if "d" in valor:
            return date.fromisoformat(valor["d"])
        if "t" in valor:
            return time.fromisoformat(valor["t"])
        if "td" in valor:
            return pd.Timedelta(seconds=valor["td"])
    return valor


def tabla_a_json(df: pd.DataFrame | None) -> str:
    if df is None:
        df = pd.DataFrame()
    filas = [[_celda_a_json(v) for v in fila]
             for fila in df.astype(object).itertuples(index=False, name=None)]
    return json.dumps({"columnas": [str(c) for c in df.columns], "filas": filas},
                      ensure_ascii=False)


def tabla_desde_json(texto: str | None) -> pd.DataFrame:
    if not texto:
        return pd.DataFrame()
    datos = json.loads(texto)
    filas = [[_celda_desde_json(v) for v in fila] for fila in datos["filas"]]
    return pd.DataFrame(filas, columns=datos["columnas"], dtype=object)


# ── PSO guardado ─────────────────────────────────────────────────────────────

_cache_pso: dict = {}


def guardar_pso(hoja: pd.DataFrame, nombre: str, ruta: Path | None = None) -> None:
    with closing(_conexion(ruta)) as con, con:
        con.execute("DELETE FROM pso")
        con.execute("INSERT INTO pso (id, nombre, cargado_en, filas, hoja) VALUES (1, ?, ?, ?, ?)",
                    (nombre, datetime.now().strftime("%Y-%m-%d %H:%M"), len(hoja),
                     tabla_a_json(hoja)))
    _cache_pso.clear()


def info_pso(ruta: Path | None = None) -> dict | None:
    """{'nombre', 'cargado_en', 'filas'} del PSO guardado, o None si no hay."""
    with closing(_conexion(ruta)) as con:
        fila = con.execute("SELECT nombre, cargado_en, filas FROM pso WHERE id = 1").fetchone()
    return dict(zip(("nombre", "cargado_en", "filas"), fila)) if fila else None


def cargar_pso(ruta: Path | None = None) -> tuple[pd.DataFrame, pd.DataFrame] | None:
    """(hoja Horarios tal cual, tabla estandarizada para buscar) del PSO guardado."""
    info = info_pso(ruta)
    if info is None:
        return None
    clave = (str(ruta or RUTA_BD), info["cargado_en"], info["filas"])
    if clave not in _cache_pso:
        with closing(_conexion(ruta)) as con:
            texto = con.execute("SELECT hoja FROM pso WHERE id = 1").fetchone()[0]
        hoja = tabla_desde_json(texto)
        _cache_pso.clear()
        _cache_pso[clave] = (hoja, modulo_pso.estandarizar(hoja))
    return _cache_pso[clave]


# ── Casos a reclamar ─────────────────────────────────────────────────────────

@dataclass
class CasoReclamo:
    fecha: date
    tipo: str                          # viaje / sin_sae
    tipo_dia: str
    unidad: str                        # SAO-008
    ruta: str
    circulacion: str
    inicio: pd.Timestamp
    fin: pd.Timestamp
    usuarios: int
    recorrido_m: float
    claves: list
    servicios: pd.DataFrame
    usos: pd.DataFrame
    pso: pd.DataFrame
    distancia_km: float | None = None
    distancia_manual: bool = False
    id: int | None = None
    agregado_en: str = ""

    @property
    def numero_unidad(self) -> int:
        return numero_bus(self.unidad)

    @property
    def revision_detallada(self) -> bool:
        return self.tipo == "sin_sae"

    @property
    def casos_unidos(self) -> int:
        return len(self.claves)

    @property
    def equivalencia(self) -> bool:
        """SAE registró algo de distancia (menos de lo programado): se resta del PSO."""
        return self.tipo == "viaje" and (self.recorrido_m or 0) > 0


def clave_caso(caso: dict) -> str:
    """Identifica un caso del día: unidad + hora de inicio."""
    inicio = pd.Timestamp(caso["inicio"])
    return f"{inicio:%Y-%m-%d}|{caso['bus']}|{inicio:%Y-%m-%d %H:%M:%S}"


def _hay_viaje_entre(horarios: pd.DataFrame | None, bus: str, desde, hasta) -> bool:
    if horarios is None or horarios.empty:
        return False
    otros = horarios[(horarios["bus"] == bus) & (horarios["inicio"] > desde)
                     & (horarios["inicio"] < hasta)]
    return not otros.empty


def unir_seguidos(casos: list[dict], horarios: pd.DataFrame | None) -> list[list[dict]]:
    """Agrupa casos de la misma unidad, ruta y circulación que van uno tras otro."""
    grupos: list[list[dict]] = []
    viajes = sorted((c for c in casos if c["tipo"] == "viaje"),
                    key=lambda c: (str(c["bus"]), pd.Timestamp(c["inicio"])))
    limite = pd.Timedelta(minutes=MINUTOS_CASOS_SEGUIDOS)
    for caso in viajes:
        if grupos:
            anterior = grupos[-1][-1]
            mismo = (anterior["bus"] == caso["bus"] and anterior["linea"] == caso["linea"]
                     and anterior["circulacion"] == caso["circulacion"]
                     and bool(caso["circulacion"]))
            seguido = pd.Timestamp(caso["inicio"]) - pd.Timestamp(anterior["fin"]) <= limite
            if mismo and seguido and not _hay_viaje_entre(
                    horarios, caso["bus"], pd.Timestamp(anterior["inicio"]),
                    pd.Timestamp(caso["inicio"])):
                grupos[-1].append(caso)
                continue
        grupos.append([caso])
    grupos += [[c] for c in casos if c["tipo"] != "viaje"]
    return grupos


def preparar_casos(resultado, posiciones: list[int], pso_estandar: pd.DataFrame | None
                   ) -> list[CasoReclamo]:
    """Casos marcados en la app (posiciones del resumen) -> registros del consolidado."""
    elegidos = [resultado.casos[i] for i in sorted(set(posiciones))]
    tipo_dia = getattr(resultado, "tipo_dia", "") or ""
    fecha = resultado.fecha                    # día operativo (incluye la madrugada siguiente)
    registros = []
    for grupo in unir_seguidos(elegidos, getattr(resultado, "horarios_viajes", None)):
        primero = grupo[0]
        inicio = min(pd.Timestamp(c["inicio"]) for c in grupo)
        fin = max(pd.Timestamp(c["fin"]) for c in grupo)
        usos = pd.concat([c["usos"] for c in grupo])
        servicios = pd.concat([c["servicios"] for c in grupo])
        sin_sae = primero["tipo"] != "viaje"
        ruta = REVISION_DETALLADA if sin_sae else primero["linea"]
        circulacion = REVISION_DETALLADA if sin_sae else primero["circulacion"]
        pso = pd.DataFrame(columns=modulo_pso.COLUMNAS_PSO)
        if not sin_sae and pso_estandar is not None:
            pso = modulo_pso.itinerarios_del_caso(pso_estandar, tipo_dia, ruta, circulacion,
                                                 inicio, fin, fecha)
        registros.append(CasoReclamo(
            fecha=fecha, tipo=primero["tipo"], tipo_dia=tipo_dia,
            unidad=str(primero["vehiculo"]), ruta=ruta, circulacion=circulacion,
            inicio=inicio, fin=fin, usuarios=len(usos),
            recorrido_m=float(sum(c.get("recorrido_m") or 0 for c in grupo)),
            claves=[clave_caso(c) for c in grupo],
            servicios=servicios.reset_index(drop=True), usos=usos.reset_index(drop=True),
            pso=pso, distancia_km=_distancia(
                pso, sum(c.get("recorrido_m") or 0 for c in grupo)),
        ))
    return sorted(registros, key=lambda r: (r.inicio, r.numero_unidad))


def km_pso(pso: pd.DataFrame | None) -> float | None:
    """Distancia de los itinerarios del PSO, en km."""
    if pso is None or pso.empty:
        return None
    return float(pd.to_numeric(pso["Distancia Media"], errors="coerce").sum()) / 1000


def _distancia(pso: pd.DataFrame, recorrido_m: float = 0) -> float | None:
    """Km a reclamar = distancia del PSO − lo que sí registró SAE (casos Equivalencia).

    En los casos con distancia 0 no se resta nada: se reclama todo lo del PSO.
    """
    total = km_pso(pso)
    if total is None:
        return None
    return round(max(total - (recorrido_m or 0) / 1000, 0), 3)


# ── Base de datos ─────────────────────────────────────────────────────────────

def claves_guardadas(quincena: Quincena, ruta: Path | None = None) -> set[str]:
    with closing(_conexion(ruta)) as con:
        filas = con.execute("SELECT claves FROM consolidado_casos WHERE quincena = ?",
                            (quincena.clave,)).fetchall()
    return {c for (texto,) in filas for c in json.loads(texto or "[]")}


def agregar(registros: list[CasoReclamo], ruta: Path | None = None) -> tuple[int, int]:
    """Guarda los registros en su quincena. Devuelve (agregados, ya estaban)."""
    agregados = repetidos = 0
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M")
    existentes: dict[str, set] = {}
    with closing(_conexion(ruta)) as con, con:
        for r in registros:
            q = Quincena.de(r.fecha)
            if q.clave not in existentes:
                existentes[q.clave] = {
                    c for (t,) in con.execute(
                        "SELECT claves FROM consolidado_casos WHERE quincena = ?", (q.clave,))
                    for c in json.loads(t or "[]")}
            if any(c in existentes[q.clave] for c in r.claves):
                repetidos += 1
                continue
            con.execute(
                "INSERT INTO consolidado_casos (quincena, fecha, tipo, tipo_dia, unidad, ruta, "
                "circulacion, inicio, fin, usuarios, recorrido_m, distancia_km, "
                "distancia_manual, claves, servicios, usos, pso, agregado_en) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (q.clave, r.fecha.isoformat(), r.tipo, r.tipo_dia, r.unidad, r.ruta,
                 r.circulacion, f"{r.inicio:%Y-%m-%d %H:%M:%S}", f"{r.fin:%Y-%m-%d %H:%M:%S}",
                 int(r.usuarios), float(r.recorrido_m or 0), r.distancia_km,
                 int(r.distancia_manual), json.dumps(r.claves), tabla_a_json(r.servicios),
                 tabla_a_json(r.usos), tabla_a_json(r.pso), ahora))
            existentes[q.clave].update(r.claves)
            agregados += 1
    return agregados, repetidos


def _registro(fila: sqlite3.Row) -> CasoReclamo:
    return CasoReclamo(
        id=fila["id"], fecha=date.fromisoformat(fila["fecha"]), tipo=fila["tipo"],
        tipo_dia=fila["tipo_dia"] or "", unidad=fila["unidad"], ruta=fila["ruta"] or "",
        circulacion=fila["circulacion"] or "", inicio=pd.Timestamp(fila["inicio"]),
        fin=pd.Timestamp(fila["fin"]), usuarios=int(fila["usuarios"] or 0),
        recorrido_m=float(fila["recorrido_m"] or 0), claves=json.loads(fila["claves"] or "[]"),
        servicios=tabla_desde_json(fila["servicios"]), usos=tabla_desde_json(fila["usos"]),
        pso=tabla_desde_json(fila["pso"]), distancia_km=fila["distancia_km"],
        distancia_manual=bool(fila["distancia_manual"]), agregado_en=fila["agregado_en"] or "")


def casos(quincena: Quincena, ruta: Path | None = None) -> list[CasoReclamo]:
    """Casos guardados de la quincena, ordenados por fecha y hora."""
    with closing(_conexion(ruta)) as con:
        con.row_factory = sqlite3.Row
        filas = con.execute("SELECT * FROM consolidado_casos WHERE quincena = ? "
                            "ORDER BY inicio, id", (quincena.clave,)).fetchall()
    return [_registro(f) for f in filas]


def resumen_quincena(quincena: Quincena, ruta: Path | None = None) -> dict:
    """Cantidad de registros, días incluidos y km de la quincena (sin leer la evidencia)."""
    with closing(_conexion(ruta)) as con:
        filas = con.execute("SELECT fecha, distancia_km, ruta FROM consolidado_casos "
                            "WHERE quincena = ?", (quincena.clave,)).fetchall()
    dias = sorted({date.fromisoformat(f) for f, _, _ in filas})
    return {"registros": len(filas), "dias": dias,
            "km": round(sum(d or 0 for _, d, _ in filas), 3),
            "sin_distancia": sum(1 for _, d, _ in filas if d is None)}


def quincenas(ruta: Path | None = None) -> list[Quincena]:
    with closing(_conexion(ruta)) as con:
        filas = con.execute("SELECT DISTINCT quincena FROM consolidado_casos "
                            "ORDER BY quincena DESC").fetchall()
    return [Quincena.desde_clave(q) for (q,) in filas]


def eliminar(ids: list[int], ruta: Path | None = None) -> None:
    with closing(_conexion(ruta)) as con, con:
        con.executemany("DELETE FROM consolidado_casos WHERE id = ?", [(int(i),) for i in ids])


def eliminar_quincenas(lista: list[Quincena], ruta: Path | None = None,
                       carpeta: Path | None = None) -> tuple[int, int]:
    """Borra por completo el consolidado de las quincenas elegidas: los registros de la
    base de datos y la copia del Excel en la carpeta 'consolidados'. Libera el espacio.
    Devuelve (registros borrados, archivos borrados)."""
    claves = [(q.clave,) for q in lista]
    if not claves:
        return 0, 0
    with closing(_conexion(ruta)) as con, con:
        registros = con.executemany("DELETE FROM consolidado_casos WHERE quincena = ?",
                                    claves).rowcount
    # El nombre del Excel no lleva el año: solo se borra si ninguna quincena que queda lo usa
    en_uso = {q.nombre_archivo for q in quincenas(ruta)}
    carpeta = Path(carpeta or CARPETA)
    archivos = 0
    for nombre in {q.nombre_archivo for q in lista} - en_uso:
        copia = carpeta / nombre
        try:
            if copia.exists():
                copia.unlink()
                archivos += 1
        except OSError:            # abierto en Excel o sin permiso: se deja
            pass
    compactar(ruta)
    return registros, archivos


def actualizar(id_caso: int, ruta_bus: str, circulacion: str, distancia_km: float | None,
               pso_estandar: pd.DataFrame | None, ruta: Path | None = None) -> CasoReclamo:
    """Corrige ruta, circulación o distancia de un registro guardado.

    Si cambian la ruta o la circulación se vuelven a buscar los itinerarios del PSO.
    Si solo cambia la distancia, queda como distancia escrita a mano.
    """
    with closing(_conexion(ruta)) as con:
        con.row_factory = sqlite3.Row
        actual = _registro(con.execute("SELECT * FROM consolidado_casos WHERE id = ?",
                                       (int(id_caso),)).fetchone())
    ruta_bus, circulacion = (ruta_bus or "").strip().upper(), (circulacion or "").strip()
    cambio_ruta = (ruta_bus, circulacion) != (actual.ruta, actual.circulacion)
    if cambio_ruta:
        actual.ruta, actual.circulacion = ruta_bus, circulacion
        actual.pso = pd.DataFrame(columns=modulo_pso.COLUMNAS_PSO)
        if pso_estandar is not None and REVISION_DETALLADA not in (ruta_bus, circulacion):
            actual.pso = modulo_pso.itinerarios_del_caso(
                pso_estandar, actual.tipo_dia, ruta_bus, circulacion, actual.inicio,
                actual.fin, actual.fecha)
        actual.distancia_km, actual.distancia_manual = \
            _distancia(actual.pso, actual.recorrido_m), False
    if distancia_km is not None and pd.notna(distancia_km) and (
            actual.distancia_km is None or abs(float(distancia_km) - actual.distancia_km) > 1e-9):
        actual.distancia_km, actual.distancia_manual = round(float(distancia_km), 3), True
    elif (distancia_km is None or pd.isna(distancia_km)) and not cambio_ruta \
            and actual.distancia_km is not None:
        actual.distancia_km, actual.distancia_manual = None, True
    with closing(_conexion(ruta)) as con, con:
        con.execute("UPDATE consolidado_casos SET ruta = ?, circulacion = ?, pso = ?, "
                    "distancia_km = ?, distancia_manual = ? WHERE id = ?",
                    (actual.ruta, actual.circulacion, tabla_a_json(actual.pso),
                     actual.distancia_km, int(actual.distancia_manual), int(id_caso)))
    return actual


def guardar_copia(contenido: bytes, quincena: Quincena) -> Path:
    """Copia del Excel en la carpeta 'consolidados'. Falla si el archivo está abierto."""
    CARPETA.mkdir(parents=True, exist_ok=True)
    destino = CARPETA / quincena.nombre_archivo
    destino.write_bytes(contenido)
    return destino
