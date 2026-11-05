"""
PSO (Programa de Servicios de Operación): hoja "Horarios" del consolidado de reclamación.

De cada salida del PSO se usan las columnas O a S: Tipo día, Ruta, Circulación, Hora y
Distancia Media. Con ellas se calcula la distancia a reclamar de cada caso:

  - Se filtran las salidas del mismo tipo de día (Hábil, Sábado o Domingo), ruta y
    circulación del caso.
  - Un itinerario empieza a la hora de su salida y termina cuando sale el siguiente
    itinerario de esa circulación.
  - Se reclaman los itinerarios que tienen al menos la mitad de su duración
    (`PSO_PARTE_MINIMA_ITINERARIO`) dentro del rango del caso.
  - El último itinerario del día no tiene "siguiente": se usa la duración típica de los
    itinerarios de esa circulación.

Ejemplo (domingo, ruta 6016, circulación 503, caso de 06:30:00 a 07:00:28):
    06:34 -> termina 06:59 (sale el siguiente): completo dentro del caso  ✔ 6.117 m
    06:59 -> termina 07:29: solo 1,5 de sus 30 minutos están en el caso    ✘
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd

from config import PSO_PARTE_MINIMA_ITINERARIO, USOS_DIA_SIGUIENTE_HASTA
from src.lectura import ErrorDeArchivo
from src.normalizacion import (
    normalizar_circulacion, normalizar_linea, normalizar_texto, parsear_hora,
)

HOJA_PSO = "Horarios"
COLUMNAS_PSO = ["Tipo día", "Ruta", "Circulación", "Hora", "Distancia Media"]

# Tipo de día de la app -> como aparece en el PSO
TIPO_PSO = {"HABIL": "Hábil", "SABADO": "Sábado", "DOMINGO": "Domingo"}

# Respaldo si las columnas O-S son fórmulas sin valor guardado (columnas A-N del PSO)
_RESPALDO = {"ruta": "Código Línea", "circulacion": "Turno", "hora": "Expedición",
             "tipo": "Tipo Dia"}


def _tipo_desde_texto(valor) -> str | None:
    """'Hábil', 'LV  CUENCAS', 'SÁBADOS CUENCAS', 'DOM-FES CUENCAS' -> HABIL / SABADO / DOMINGO."""
    if pd.isna(valor):
        return None
    t = normalizar_texto(valor)
    if t.startswith(("habil", "lv", "lunes")):
        return "HABIL"
    if t.startswith("sab"):
        return "SABADO"
    if t.startswith(("dom", "fes")):
        return "DOMINGO"
    return None


def _minutos(valor) -> float | None:
    hora = parsear_hora(valor)
    if hora is None:
        return None
    return hora.hour * 60 + hora.minute + hora.second / 60


def _bloque_columnas(columnas: list[str]) -> dict | None:
    """Ubica las columnas Tipo día, Ruta, Circulación, Hora y Distancia Media.

    Si 'Tipo día' aparece dos veces (K 'Tipo Dia' y O 'Tipo día'), se usa la que va
    seguida de Ruta, Circulación, Hora y Distancia Media.
    """
    nombres = [normalizar_texto(c) for c in columnas]
    buscadas = [normalizar_texto(c) for c in COLUMNAS_PSO]
    for i in range(len(nombres) - len(buscadas), -1, -1):
        if nombres[i:i + len(buscadas)] == buscadas:
            return dict(zip(COLUMNAS_PSO, columnas[i:i + len(buscadas)]))
    # Sin el bloque seguido: cada columna por su nombre (la última que aparezca)
    encontradas = {}
    for nombre, buscada in zip(COLUMNAS_PSO, buscadas):
        coincidencias = [c for c, n in zip(columnas, nombres) if n == buscada]
        if not coincidencias:
            return None
        encontradas[nombre] = coincidencias[-1]
    return encontradas


def estandarizar(original: pd.DataFrame) -> pd.DataFrame:
    """Tabla del PSO lista para buscar: tipo, ruta, circulación, minuto y distancia."""
    columnas = [str(c) for c in original.columns]
    original = original.set_axis(columnas, axis=1)
    bloque = _bloque_columnas(columnas)
    if bloque is None:
        raise ErrorDeArchivo(
            "El archivo del PSO no tiene las columnas " + ", ".join(COLUMNAS_PSO) +
            f" (columnas O a S de la hoja '{HOJA_PSO}').")

    def columna(clave_bloque: str, clave_respaldo: str) -> pd.Series:
        serie = original[bloque[clave_bloque]]
        respaldo = _RESPALDO.get(clave_respaldo)
        if serie.isna().all() and respaldo in original:
            return original[respaldo]              # fórmulas sin valor guardado
        return serie

    tabla = pd.DataFrame({
        "tipo": columna("Tipo día", "tipo").map(_tipo_desde_texto),
        "ruta": columna("Ruta", "ruta").map(normalizar_linea),
        "circulacion": columna("Circulación", "circulacion").map(normalizar_circulacion),
        "hora": columna("Hora", "hora").map(parsear_hora),
        "distancia_m": pd.to_numeric(original[bloque["Distancia Media"]], errors="coerce"),
    })
    tabla["minuto"] = tabla["hora"].map(
        lambda h: None if h is None else h.hour * 60 + h.minute + h.second / 60)
    tabla = tabla.dropna(subset=["tipo", "ruta", "circulacion", "minuto"])
    # Salidas de madrugada (antes de las 03:30) son del final del día operativo
    corte = _minutos(USOS_DIA_SIGUIENTE_HASTA)
    tabla.loc[tabla["minuto"] < corte, "minuto"] += 24 * 60
    tabla["hora_texto"] = tabla["hora"].map(lambda h: h.strftime("%H:%M"))
    return tabla.drop(columns="hora")


def leer_pso(archivo) -> pd.DataFrame:
    """Lee la hoja Horarios completa (o la primera hoja con las columnas del PSO).

    Devuelve la hoja tal cual, con todas sus columnas, para copiarla en el consolidado.
    Solo se quitan las columnas sin título que están totalmente vacías."""
    if hasattr(archivo, "seek"):
        archivo.seek(0)
    try:
        libro = pd.ExcelFile(archivo)
    except Exception as e:
        raise ErrorDeArchivo(f"No se pudo leer el archivo del PSO: {e}") from e
    hojas = [HOJA_PSO] if HOJA_PSO in libro.sheet_names else libro.sheet_names
    for hoja in hojas:
        # Se lee la hoja completa (todas sus columnas y filas); para el cálculo solo se
        # usan Tipo día, Ruta, Circulación, Hora y Distancia Media (O a S).
        df = libro.parse(hoja, dtype=object)
        df.columns = [str(c).strip() for c in df.columns]
        vacias = [c for c in df.columns if c.startswith("Unnamed") and df[c].isna().all()]
        df = df.drop(columns=vacias)
        # Las filas se conservan tal cual (también las vacías intermedias); solo se quitan
        # las filas vacías del final de la hoja
        con_datos = df.notna().any(axis=1)
        df = df.loc[:con_datos[con_datos].index.max()] if con_datos.any() else df.iloc[0:0]
        if _bloque_columnas(list(df.columns)) is not None:
            if estandarizar(df).empty:
                raise ErrorDeArchivo("La hoja del PSO no tiene salidas con tipo de día, "
                                     "ruta, circulación y hora válidos.")
            return df.reset_index(drop=True)
    raise ErrorDeArchivo(
        f"No se encontró la hoja '{HOJA_PSO}' con las columnas " + ", ".join(COLUMNAS_PSO) +
        ". Carga el archivo del consolidado que tiene la hoja Horarios (PSO).")


def rutas_equivalentes(ruta: str) -> list[str]:
    """La ruta y sus otros nombres: '6006' <-> '6006C' (en el PSO algunas llevan C)."""
    ruta = normalizar_linea(ruta) or ""
    otros = [ruta[:-1]] if ruta.endswith("C") else [ruta + "C"]
    return [ruta] + otros


def itinerarios_del_caso(pso: pd.DataFrame, tipo_dia: str, ruta: str, circulacion: str,
                         inicio: datetime, fin: datetime, fecha,
                         parte_minima: float = PSO_PARTE_MINIMA_ITINERARIO) -> pd.DataFrame:
    """Salidas del PSO que se reclaman en un caso (ver la regla al inicio del archivo).

    `pso` es la tabla de `estandarizar`. Devuelve las columnas del PSO
    (Tipo día, Ruta, Circulación, Hora, Distancia Media) de los itinerarios elegidos.
    """
    vacio = pd.DataFrame(columns=COLUMNAS_PSO)
    if not ruta or not circulacion:
        return vacio
    del_tipo = pso[(pso["tipo"] == tipo_dia)
                   & (pso["circulacion"] == normalizar_circulacion(circulacion))]
    salidas = del_tipo.iloc[0:0]
    for nombre in rutas_equivalentes(ruta):          # 6006 y 6006C son la misma ruta
        salidas = del_tipo[del_tipo["ruta"] == nombre]
        if not salidas.empty:
            break
    if salidas.empty:
        return vacio
    salidas = salidas.sort_values("minuto").drop_duplicates("minuto")
    siguiente = salidas["minuto"].shift(-1)
    duracion = siguiente - salidas["minuto"]
    tipica = duracion.median()
    duracion = duracion.fillna(tipica if pd.notna(tipica) else 0)

    base = pd.Timestamp(fecha).normalize()
    desde = (pd.Timestamp(inicio) - base).total_seconds() / 60
    hasta = (pd.Timestamp(fin) - base).total_seconds() / 60
    if hasta < desde:                                  # el caso pasa de medianoche
        hasta += 24 * 60
    salida = salidas["minuto"]
    llegada = salida + duracion
    dentro = (llegada.clip(upper=hasta) - salida.clip(lower=desde)).clip(lower=0)
    elegidas = salidas[(dentro >= parte_minima * duracion) & (dentro > 0)]
    return pd.DataFrame({
        "Tipo día": TIPO_PSO.get(tipo_dia, tipo_dia),
        "Ruta": elegidas["ruta"],
        "Circulación": elegidas["circulacion"],
        "Hora": elegidas["hora_texto"],
        "Distancia Media": elegidas["distancia_m"],
    }).reset_index(drop=True)
