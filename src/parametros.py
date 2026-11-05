"""
Parámetros de revisión modificables por el usuario: por cada ruta (línea),
la distancia de ciclo (m) y el tiempo de ciclo (min).

Con ellos se calcula, por ruta:
  Distancia x min    = Distancia de ciclo / Tiempo de ciclo
  Distancia al 95 %  = Distancia x min × porcentaje exigido   (metros por minuto exigidos)

Cada viaje debe recorrer al menos: minutos del viaje × Distancia al 95 %.
El porcentaje exigido (95 % inicial) también se modifica desde la interfaz.

También guarda cuántos minutos pueden separar dos usos sin viaje para agruparlos.

Hay un juego de parámetros por cada tipo de día (HÁBIL, SÁBADO y DOMINGO/festivo),
porque el cumplimiento exigido cambia según el día. Se guardan en un archivo JSON
para conservarlos entre usos.
"""
import copy
import json
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from config import (
    ARCHIVO_PARAMETROS, MINUTOS_AGRUPAR_USOS_INICIAL, PORCENTAJE_EXIGIDO_INICIAL, RUTAS_INICIALES,
)
from src.calendario import HABIL, TIPOS_DIA
from src.normalizacion import normalizar_linea, ordenar_lineas

RUTA_ARCHIVO = Path(__file__).resolve().parent.parent / ARCHIVO_PARAMETROS

PORCENTAJE_MIN = 0.01
PORCENTAJE_MAX = 1.0


def formato_pct(valor: float) -> str:
    """0.95 -> '95%', 0.925 -> '92,5%'."""
    return f"{round(valor * 100, 2):g}".replace(".", ",") + "%"

# Columnas de la tabla de rutas (nombre interno -> título en pantalla y en Excel)
COLUMNAS_RUTAS = {
    "linea": "Línea",
    "distancia_ciclo_m": "Distancia de ciclo (m)",
    "tiempo_ciclo_min": "Tiempo de ciclo (min)",
}
COLUMNAS_CALCULADAS = {
    "distancia_x_min": "Distancia x min (m)",
    "distancia_95": "Distancia exigida x min (m)",     # el título real lleva el porcentaje
}


MINUTOS_AGRUPAR_MIN = 1
MINUTOS_AGRUPAR_MAX = 240


@dataclass
class Parametros:
    rutas: pd.DataFrame = field(default_factory=lambda: rutas_iniciales())
    minutos_agrupar_usos: int = MINUTOS_AGRUPAR_USOS_INICIAL
    porcentaje_exigido: float = PORCENTAJE_EXIGIDO_INICIAL     # 0.95 = 95 %

    # ── Cálculos ──────────────────────────────────────────────────────────────
    def tabla_calculada(self) -> pd.DataFrame:
        """Rutas con las columnas calculadas (nombres internos)."""
        t = self.rutas.copy()
        tiempo = t["tiempo_ciclo_min"].where(t["tiempo_ciclo_min"] > 0)
        t["distancia_x_min"] = t["distancia_ciclo_m"] / tiempo
        t["distancia_95"] = t["distancia_x_min"] * self.porcentaje_exigido
        return t

    def tabla_para_mostrar(self) -> pd.DataFrame:
        """Tabla con títulos legibles, para pantalla y Excel."""
        nombres = {**COLUMNAS_RUTAS, **COLUMNAS_CALCULADAS,
                   "distancia_95": f"Distancia al {self.pct} x min (m)"}
        return self.tabla_calculada()[list(nombres)].rename(columns=nombres)

    def distancia_95_por_linea(self) -> dict:
        """{línea: metros por minuto exigidos}. Solo rutas con datos válidos."""
        t = self.tabla_calculada().dropna(subset=["linea", "distancia_95"])
        return dict(zip(t["linea"], t["distancia_95"]))

    @property
    def pct(self) -> str:
        """Porcentaje exigido como texto: '95%', '92,5%'."""
        return formato_pct(self.porcentaje_exigido)

    # ── Validación ────────────────────────────────────────────────────────────
    def errores(self) -> list:
        errores = []
        if not PORCENTAJE_MIN <= self.porcentaje_exigido <= PORCENTAJE_MAX:
            errores.append(f"El cumplimiento exigido debe estar entre {PORCENTAJE_MIN:.0%} "
                           f"y {PORCENTAJE_MAX:.0%}.")
        if not MINUTOS_AGRUPAR_MIN <= self.minutos_agrupar_usos <= MINUTOS_AGRUPAR_MAX:
            errores.append(f"Los minutos para agrupar usos deben estar entre "
                           f"{MINUTOS_AGRUPAR_MIN} y {MINUTOS_AGRUPAR_MAX}.")
        r = self.rutas
        if r["linea"].isna().any():
            errores.append("Hay filas sin línea.")
        repetidas = r["linea"].dropna()[r["linea"].dropna().duplicated()].unique()
        if len(repetidas):
            errores.append(f"Líneas repetidas: {', '.join(repetidas)}.")
        invalidas = r[(r["distancia_ciclo_m"].isna()) | (r["distancia_ciclo_m"] <= 0) |
                      (r["tiempo_ciclo_min"].isna()) | (r["tiempo_ciclo_min"] <= 0)]
        if len(invalidas):
            lineas = ", ".join(invalidas["linea"].fillna("(sin línea)").astype(str))
            errores.append(f"Distancia y tiempo de ciclo deben ser mayores a 0 en: {lineas}.")
        return errores


# ── Construcción ──────────────────────────────────────────────────────────────

def limpiar_rutas(df: pd.DataFrame) -> pd.DataFrame:
    """Tipos correctos, líneas normalizadas, orden natural, sin filas vacías."""
    df = df.reindex(columns=list(COLUMNAS_RUTAS)).copy()
    df["linea"] = df["linea"].map(normalizar_linea)
    for col in ("distancia_ciclo_m", "tiempo_ciclo_min"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(how="all")
    orden = {l: i for i, l in enumerate(ordenar_lineas(df["linea"].dropna()))}
    df = df.assign(_o=df["linea"].map(orden)).sort_values("_o", na_position="last")
    return df.drop(columns="_o").reset_index(drop=True)


def rutas_iniciales() -> pd.DataFrame:
    return limpiar_rutas(pd.DataFrame(RUTAS_INICIALES, columns=list(COLUMNAS_RUTAS)))


def parametros_iniciales() -> Parametros:
    return Parametros(rutas_iniciales(), MINUTOS_AGRUPAR_USOS_INICIAL, PORCENTAJE_EXIGIDO_INICIAL)


# ── Persistencia ──────────────────────────────────────────────────────────────

def _a_dict(parametros: Parametros) -> dict:
    return {
        "minutos_agrupar_usos": int(parametros.minutos_agrupar_usos),
        "porcentaje_exigido": float(parametros.porcentaje_exigido),
        "rutas": parametros.rutas.astype(object).where(parametros.rutas.notna(), None)
                                 .to_dict(orient="records"),
    }


def _desde_dict(datos: dict) -> Parametros:
    """Acepta también datos de versiones anteriores (con "minutos_franja", que se ignora)."""
    return Parametros(
        limpiar_rutas(pd.DataFrame(datos["rutas"])),
        int(datos.get("minutos_agrupar_usos", MINUTOS_AGRUPAR_USOS_INICIAL)),
        float(datos.get("porcentaje_exigido", PORCENTAJE_EXIGIDO_INICIAL)),
    )


def guardar(parametros: Parametros, ruta: Path = RUTA_ARCHIVO) -> None:
    """Guarda un solo juego de parámetros (formato anterior, sin tipos de día)."""
    ruta.write_text(json.dumps(_a_dict(parametros), ensure_ascii=False, indent=2),
                    encoding="utf-8")


def cargar(ruta: Path = RUTA_ARCHIVO) -> tuple[Parametros, str | None]:
    """Devuelve (parámetros, aviso). Si el archivo no existe o está dañado usa los iniciales.

    Si el archivo tiene parámetros por tipo de día, devuelve los de día hábil.
    """
    todos, aviso = cargar_por_dia(ruta)
    return todos[HABIL], aviso


# ── Parámetros por tipo de día (hábil, sábado, domingo/festivo) ───────────────

def iniciales_por_dia() -> dict[str, Parametros]:
    return {tipo: parametros_iniciales() for tipo in TIPOS_DIA}


def guardar_por_dia(por_dia: dict[str, Parametros], ruta: Path = RUTA_ARCHIVO) -> None:
    contenido = {"tipos_dia": {tipo: _a_dict(por_dia[tipo]) for tipo in TIPOS_DIA}}
    ruta.write_text(json.dumps(contenido, ensure_ascii=False, indent=2), encoding="utf-8")


def cargar_por_dia(ruta: Path = RUTA_ARCHIVO) -> tuple[dict[str, Parametros], str | None]:
    """{tipo de día: parámetros}, aviso.

    Un archivo de versiones anteriores (un solo juego de parámetros) se usa igual para
    los tres tipos de día. Si falta un tipo se usan los de día hábil.
    """
    if not ruta.exists():
        return iniciales_por_dia(), None
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        if "tipos_dia" in datos:
            leidos = {t: _desde_dict(d) for t, d in datos["tipos_dia"].items() if t in TIPOS_DIA}
            base = leidos.get(HABIL) or parametros_iniciales()
            por_dia = {t: leidos.get(t) or copy.deepcopy(base) for t in TIPOS_DIA}
        else:
            unico = _desde_dict(datos)
            por_dia = {t: copy.deepcopy(unico) for t in TIPOS_DIA}
    except Exception as e:
        return iniciales_por_dia(), (
            f"No se pudo leer {ruta.name} ({e}); se usan los parámetros iniciales.")
    return por_dia, None
