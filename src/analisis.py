"""
Análisis viaje por viaje.

Un VIAJE es cada registro del informe de servicios. Reglas:
  - Duración del viaje = Fin Servicio Efectivo − Inicio Servicio Efectivo (columnas O y P).
  - Mínimo del viaje   = duración (min) × distancia al 95 % por minuto de su ruta.
  - Usos del viaje     = usos del mismo bus cuya hora está entre "Inicio de Servicio" y
                         "Fin de Servicio" (columnas I y J), que incluyen el abordaje
                         previo al inicio efectivo. Si faltan, se usan O y P.
  - Validación del viaje:
        sin distancia y sin usos        -> No operó
        sin distancia y con usos        -> REVISAR - Distancia 0
        bajo el mínimo y con usos       -> REVISAR - Equivalencia
        cualquier otro caso             -> Operó
    (Si la ruta no tiene parámetros no hay mínimo y solo se revisa "sin distancia".)
  - Cada USO que no cae dentro de ningún viaje de su bus es "REVISAR - Uso sin viaje"
    con recorrido 0. Los usos sin viaje seguidos se AGRUPAN en una fila cuando son del
    mismo bus, de la misma ruta (si el archivo de usos la trae), no hay un viaje entre
    ellos y cada uno está a `minutos_agrupar_usos` o menos del anterior.
  - Si un bus tiene viajes duplicados (misma línea y misma hora de inicio
    efectivo) y uno tiene distancia 0 y otro mayor, el de distancia 0 se descarta.
"""
from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd

from config import USOS_DIA_SIGUIENTE_HASTA, Validacion
from src.lectura import DatosLeidos, ErrorDeArchivo, leer_servicios, leer_usos
from src.normalizacion import normalizar_linea, numero_bus, ordenar_lineas
from src.parametros import Parametros

COL_RECORRIDO = "Recorrido (m)"     # distancia del viaje
COL_MINIMO = "Mínimo (m)"           # distancia mínima exigida al viaje
COL_DIFERENCIA = "Diferencia (m)"   # recorrido − mínimo (negativo = metros faltantes)
COL_DURACION = "Duración (min)"

COLUMNAS_VIAJES = [
    "N° viaje", "Vehículo", "Línea", "Circulación", "Fecha", "Inicio servicio", "Fin servicio",
    "Inicio", "Fin", COL_DURACION,
    COL_RECORRIDO, COL_MINIMO, COL_DIFERENCIA, "Usos", "Validación",
]
COLUMNAS_USOS_SIN_VIAJE = ["Vehículo", "Línea", "Fecha", "Hora", COL_RECORRIDO, "Validación"]
COLUMNAS_GRUPOS_SIN_VIAJE = ["Vehículo", "Línea", "Fecha", "Inicio", "Fin", COL_DURACION,
                             "Usos", COL_RECORRIDO, "Validación"]


@dataclass
class ResultadoAnalisis:
    fecha: date
    parametros: Parametros             # parámetros con los que se calculó
    viajes: pd.DataFrame               # un registro por viaje
    usos_sin_viaje: pd.DataFrame       # un registro por uso que no cae en ningún viaje
    grupos_sin_viaje: pd.DataFrame     # usos sin viaje seguidos, agrupados
    resumen: pd.DataFrame              # viajes a revisar + grupos de usos sin viaje
    servicios: pd.DataFrame            # informe de servicios original, ordenado
    usos: pd.DataFrame                 # usos del día, ordenados por hora
    columnas_servicios: dict           # clave lógica -> encabezado real
    indicadores: dict
    avisos: list = field(default_factory=list)
    tipo_dia: str = ""                 # HABIL, SABADO o DOMINGO (parámetros usados)
    # Datos de cada fila del resumen (misma posición) para armar el consolidado:
    # filas del informe de servicios, usos y horas reales de cada caso.
    casos: list = field(default_factory=list)
    # Todos los viajes del día (bus, inicio, fin) para saber si dos casos son seguidos
    horarios_viajes: pd.DataFrame | None = None


# ── Limpieza de servicios ─────────────────────────────────────────────────────

def descartar_duplicados_en_cero(servicios: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Quita los viajes con distancia 0 que tienen un "gemelo" con distancia mayor.

    Gemelos = mismo bus, misma línea y misma hora de inicio efectivo. El registro
    en 0 es un error del informe; si todos los gemelos están en 0 se conservan.
    """
    distancia = servicios["distancia_m"].fillna(0)
    clave = [servicios["bus"], servicios["linea"].fillna(""), servicios["inicio"]]
    maxima_del_grupo = distancia.groupby(clave, dropna=False).transform("max")
    en_cero_con_gemelo = (distancia == 0) & (maxima_del_grupo > 0) & servicios["inicio"].notna()
    return servicios[~en_cero_con_gemelo], int(en_cero_con_gemelo.sum())


# ── Usos por viaje ────────────────────────────────────────────────────────────

def _ns(serie) -> pd.Series:
    return pd.Series(serie).astype("datetime64[ns]")


def ventana_de_usos(viajes: pd.DataFrame) -> pd.DataFrame:
    """Viajes con `inicio`/`fin` = Inicio y Fin de Servicio (I y J), para cruzar usos.

    Si un viaje no tiene esas horas se usan las efectivas (O y P).
    """
    return viajes.assign(inicio=viajes["inicio_servicio"].fillna(viajes["inicio"]),
                         fin=viajes["fin_servicio"].fillna(viajes["fin"]))


def asignar_usos_a_viajes(usos: pd.DataFrame, viajes: pd.DataFrame) -> pd.Series:
    """Para cada uso, el índice del viaje de su bus que lo contiene (o NaN si ninguno).

    `viajes` debe traer en `inicio`/`fin` la ventana de usos (ver `ventana_de_usos`).
    Un uso pertenece a un viaje si su hora está entre ese inicio y ese fin.
    Si dos viajes del mismo bus se superponen, el uso va al que empezó más tarde.
    """
    resultado = pd.Series(np.nan, index=usos.index)
    u = usos.dropna(subset=["bus", "momento"])
    v = viajes.dropna(subset=["bus", "inicio", "fin"])
    if u.empty or v.empty:
        return resultado

    v = (v.assign(_id=v.index, inicio=_ns(v["inicio"]),
                  fin=_ns(v[["inicio", "fin"]].max(axis=1)))
          .sort_values("inicio"))
    # Para viajes largos que contienen a otros: fin máximo acumulado y su viaje
    v["_fin_max"] = v.groupby("bus")["fin"].cummax()
    v["_id_fin_max"] = v["_id"].where(v["fin"] == v["_fin_max"])
    v["_id_fin_max"] = v.groupby("bus")["_id_fin_max"].ffill()

    cruce = pd.merge_asof(
        u.assign(_uso=u.index, momento=_ns(u["momento"])).sort_values("momento"),
        v[["bus", "inicio", "fin", "_id", "_fin_max", "_id_fin_max"]],
        left_on="momento", right_on="inicio", by="bus", direction="backward",
    )
    viaje = np.where(cruce["momento"] <= cruce["fin"], cruce["_id"],
                     np.where(cruce["momento"] <= cruce["_fin_max"], cruce["_id_fin_max"], np.nan))
    resultado.loc[cruce["_uso"].to_numpy()] = viaje
    return resultado


def viaje_anterior_de_cada_uso(usos: pd.DataFrame, viajes: pd.DataFrame) -> pd.Series:
    """Índice del último viaje del bus que empezó antes de cada uso (NaN si ninguno).

    Dos usos sin viaje con distinto "viaje anterior" tienen un viaje entre ellos.
    """
    resultado = pd.Series(np.nan, index=usos.index)
    u = usos.dropna(subset=["bus", "momento"])
    v = viajes.dropna(subset=["bus", "inicio"])
    if u.empty or v.empty:
        return resultado
    cruce = pd.merge_asof(
        u.assign(_uso=u.index, momento=_ns(u["momento"])).sort_values("momento"),
        v.assign(_id=v.index, inicio=_ns(v["inicio"]))[["bus", "inicio", "_id"]]
         .sort_values("inicio"),
        left_on="momento", right_on="inicio", by="bus", direction="backward",
    )
    resultado.loc[cruce["_uso"].to_numpy()] = cruce["_id"].to_numpy()
    return resultado


# ── Clasificación ─────────────────────────────────────────────────────────────

def clasificar(distancia_m: pd.Series, minimo_m: pd.Series, usos: pd.Series) -> np.ndarray:
    condiciones = [
        (distancia_m == 0) & (usos == 0),
        (distancia_m == 0) & (usos > 0),
        minimo_m.notna() & (distancia_m < minimo_m) & (usos > 0),
    ]
    valores = [Validacion.NO_OPERO, Validacion.REVISAR, Validacion.KM_BAJO]
    return np.select(condiciones, valores, default=Validacion.OPERO)


# ── Tablas de resultado ───────────────────────────────────────────────────────

def _hora(momento: pd.Series, referencia: pd.Series | None = None) -> pd.Series:
    """'HH:MM:SS'; si cae en un día posterior a `referencia` agrega ' (+1 día)'."""
    texto = momento.dt.strftime("%H:%M:%S")
    if referencia is not None:
        dias = (momento.dt.normalize() - referencia.dt.normalize()).dt.days
        texto = texto.where(~(dias > 0), texto + " (+" + dias.astype("Int64").astype(str) + " día)")
    return texto


def _ordenar(tabla: pd.DataFrame, vehiculo: pd.Series, momento: pd.Series) -> pd.DataFrame:
    """Orden natural por vehículo (SAO-2 antes que SAO-10) y luego por hora."""
    claves = pd.DataFrame({"_n": vehiculo.map(numero_bus).to_numpy(),
                           "_v": vehiculo.astype(str).to_numpy(),
                           "_t": _ns(momento).to_numpy()}, index=tabla.index)
    orden = claves.sort_values(["_n", "_v", "_t"], na_position="last").index
    return tabla.loc[orden].reset_index(drop=True)


def construir_viajes(viajes: pd.DataFrame, usos_por_viaje: pd.Series,
                     parametros: Parametros) -> pd.DataFrame:
    v = viajes.dropna(subset=["bus", "inicio", "fin"])
    distancia = v["distancia_m"].fillna(0)
    duracion = ((v["fin"] - v["inicio"]).dt.total_seconds() / 60).clip(lower=0)
    minimo = duracion * v["linea"].map(parametros.distancia_95_por_linea())
    usos = usos_por_viaje.value_counts().reindex(v.index, fill_value=0).astype(int)

    tabla = pd.DataFrame({
        "N° viaje": v["numero"].map(normalizar_linea).fillna(""),   # texto: '05585', '4451'

        "Vehículo": v["vehiculo"],
        "Línea": v["linea"].fillna(""),
        "Circulación": (v["circulacion"].fillna("") if "circulacion" in v
                        else pd.Series("", index=v.index)),
        "Fecha": v["inicio"].dt.strftime("%d/%m/%Y"),
        "Inicio servicio": _hora(v["inicio_servicio"]).fillna(""),
        "Fin servicio": _hora(v["fin_servicio"], v["inicio_servicio"]).fillna(""),
        "Inicio": _hora(v["inicio"]),
        "Fin": _hora(v["fin"], v["inicio"]),
        COL_DURACION: duracion.round(1),
        COL_RECORRIDO: distancia.round().astype(int),
        COL_MINIMO: minimo.round().astype("Int64"),              # vacío si no hay parámetros
        "Usos": usos,
    }, index=v.index)
    tabla[COL_DIFERENCIA] = tabla[COL_RECORRIDO] - tabla[COL_MINIMO]
    tabla["Validación"] = clasificar(distancia, minimo, usos)
    tabla["_origen"] = v.index                   # fila del informe (se quita en analizar)
    return _ordenar(tabla[COLUMNAS_VIAJES + ["_origen"]], v["vehiculo"], v["inicio"])


def construir_usos_sin_viaje(usos: pd.DataFrame, vehiculo: pd.Series) -> pd.DataFrame:
    """Una fila por uso sin viaje. `vehiculo`: nombre a mostrar de cada uso."""
    tabla = pd.DataFrame({
        "Vehículo": vehiculo,
        "Línea": usos["linea"].fillna("") if "linea" in usos else "",
        "Fecha": usos["momento"].dt.strftime("%d/%m/%Y").fillna(""),
        "Hora": usos["momento"].dt.strftime("%H:%M:%S").fillna(""),
        COL_RECORRIDO: 0,
        "Validación": Validacion.USO_SIN_VIAJE,
    }, index=usos.index)
    return _ordenar(tabla[COLUMNAS_USOS_SIN_VIAJE], vehiculo, usos["momento"])


def agrupar_usos_sin_viaje(usos: pd.DataFrame, vehiculo: pd.Series,
                           viaje_anterior: pd.Series, minutos: int) -> pd.DataFrame:
    """Agrupa usos sin viaje seguidos del mismo bus y ruta, sin un viaje entre ellos."""
    if usos.empty:
        return pd.DataFrame(columns=COLUMNAS_GRUPOS_SIN_VIAJE + ["_origen"])
    u = pd.DataFrame({
        "bus": usos["bus"], "vehiculo": vehiculo,
        "linea": usos["linea"].fillna("") if "linea" in usos else "",
        "momento": usos["momento"], "anterior": viaje_anterior.fillna(-1),
    }).dropna(subset=["momento"]).sort_values(["bus", "momento"])

    previo = u.shift()
    nuevo_grupo = ((u["bus"] != previo["bus"]) | (u["linea"] != previo["linea"])
                   | (u["anterior"] != previo["anterior"])
                   | ((u["momento"] - previo["momento"]) > pd.Timedelta(minutes=minutos)))
    u["grupo"] = nuevo_grupo.cumsum()

    g = u.groupby("grupo").agg(vehiculo=("vehiculo", "first"), linea=("linea", "first"),
                               inicio=("momento", "min"), fin=("momento", "max"),
                               usos=("momento", "size"))
    indices_por_grupo = {k: list(x.index) for k, x in u.groupby("grupo")}
    tabla = pd.DataFrame({
        "Vehículo": g["vehiculo"],
        "Línea": g["linea"],
        "Fecha": g["inicio"].dt.strftime("%d/%m/%Y"),
        "Inicio": g["inicio"].dt.strftime("%H:%M:%S"),
        "Fin": _hora(g["fin"], g["inicio"]),
        COL_DURACION: ((g["fin"] - g["inicio"]).dt.total_seconds() / 60).round(1),
        "Usos": g["usos"].astype(int),
        COL_RECORRIDO: 0,
        "Validación": Validacion.USO_SIN_VIAJE,
    })
    tabla["_origen"] = [tuple(indices_por_grupo[k]) for k in g.index]   # usos del grupo
    return _ordenar(tabla[COLUMNAS_GRUPOS_SIN_VIAJE + ["_origen"]], g["vehiculo"], g["inicio"])


def construir_resumen(viajes: pd.DataFrame, grupos_sin_viaje: pd.DataFrame) -> pd.DataFrame:
    """Viajes a revisar + grupos de usos sin viaje, ordenados por bus y hora."""
    a_revisar = viajes[viajes["Validación"].str.startswith("REVISAR")]
    extra = ["_origen"] if "_origen" in viajes.columns else []
    resumen = pd.concat([a_revisar, grupos_sin_viaje],
                        ignore_index=True).reindex(columns=COLUMNAS_VIAJES + extra)
    for col in ("N° viaje", "Línea", "Circulación", "Inicio servicio", "Fin servicio", "Fin"):
        resumen[col] = resumen[col].fillna("").astype(str)
    for col in (COL_MINIMO, COL_DIFERENCIA):
        resumen[col] = resumen[col].astype("Int64")
    momento = pd.to_datetime(resumen["Fecha"] + " " + resumen["Inicio"].str[:8],
                             format="%d/%m/%Y %H:%M:%S", errors="coerce")
    return _ordenar(resumen, resumen["Vehículo"], momento)


# ── Proceso completo ──────────────────────────────────────────────────────────

def detectar_fecha(servicios: pd.DataFrame) -> date:
    fechas = servicios["inicio"].dropna().dt.date
    if fechas.empty:
        raise ErrorDeArchivo("No se pudo detectar la fecha del informe de servicios.")
    return fechas.mode()[0]


def _usos_del_dia(usos: pd.DataFrame, fecha: date) -> pd.DataFrame:
    """Usos de la fecha del informe y de la madrugada siguiente (viajes después de 00:00)."""
    desde = pd.Timestamp(fecha)
    h, m = map(int, USOS_DIA_SIGUIENTE_HASTA.split(":"))
    hasta = desde + pd.Timedelta(days=1, hours=h, minutes=m)
    en_ventana = (usos["momento"] >= desde) & (usos["momento"] < hasta)
    return usos[en_ventana | ((usos["fecha"] == fecha) & usos["momento"].isna())]


def _avisos_rutas_sin_parametros(servicios: pd.DataFrame, parametros: Parametros) -> list:
    sin_param = set(servicios["linea"].dropna()) - set(parametros.distancia_95_por_linea())
    if not sin_param:
        return []
    return [f"Rutas sin parámetros de distancia (solo se revisa 'sin distancia'): "
            f"{', '.join(ordenar_lineas(sin_param))}. Agrégalas en 'Modificar parámetros'."]


def _ordenar_servicios(datos: DatosLeidos, validos: pd.DataFrame) -> pd.DataFrame:
    orden = validos.assign(_num=validos["vehiculo"].map(numero_bus)) \
                   .sort_values(["_num", "inicio", "fin"], na_position="last").index
    return datos.original.loc[orden].reset_index(drop=True)


def _detalle_de_casos(origenes: pd.Series, resumen: pd.DataFrame, validos: pd.DataFrame,
                      servicios: DatosLeidos, usos: DatosLeidos, usos_dia: pd.DataFrame,
                      viaje_de_cada_uso: pd.Series) -> list[dict]:
    """Para cada fila del resumen: sus filas del informe de servicios, sus usos y sus horas.

    Es lo que se pega como evidencia en el consolidado de reclamación.
    """
    casos = []
    for origen, (_, fila) in zip(origenes, resumen.iterrows()):
        if isinstance(origen, tuple):                       # grupo de usos sin viaje
            indices_usos = list(origen)
            momentos = usos_dia.loc[indices_usos, "momento"]
            casos.append({
                "tipo": "sin_sae",
                "bus": usos_dia.loc[indices_usos[0], "bus"],
                "vehiculo": fila["Vehículo"],
                "linea": "", "circulacion": "",
                "inicio": momentos.min(), "fin": momentos.max(),
                "recorrido_m": 0,
                "servicios": servicios.original.iloc[0:0],
                "usos": usos.original.loc[momentos.sort_values().index],
            })
            continue
        viaje = validos.loc[origen]
        indices_usos = viaje_de_cada_uso.index[viaje_de_cada_uso == origen]
        momentos = usos_dia.loc[indices_usos, "momento"].sort_values()
        casos.append({
            "tipo": "viaje",
            "bus": viaje["bus"],
            "vehiculo": fila["Vehículo"],
            "linea": fila["Línea"],
            "circulacion": fila["Circulación"],
            "inicio": viaje["inicio"], "fin": viaje["fin"],
            "recorrido_m": fila[COL_RECORRIDO],
            "servicios": servicios.original.loc[[origen]],
            "usos": usos.original.loc[momentos.index],
        })
    return casos


def fecha_del_informe(archivo_servicios) -> date:
    """Fecha del informe de servicios, para saber qué tipo de día es antes de analizar."""
    return detectar_fecha(leer_servicios(archivo_servicios).tabla)


def analizar(archivo_usos, archivo_servicios, parametros: Parametros,
             tipo_dia: str = "") -> ResultadoAnalisis:
    servicios = leer_servicios(archivo_servicios)
    usos = leer_usos(archivo_usos)

    fecha = detectar_fecha(servicios.tabla)
    usos_dia = _usos_del_dia(usos.tabla, fecha)
    if usos_dia.empty:
        raise ErrorDeArchivo(
            f"El archivo de usos no tiene registros del {fecha:%d/%m/%Y}, "
            "que es la fecha del informe de servicios."
        )

    validos, descartados = descartar_duplicados_en_cero(servicios.tabla)
    avisos = list(servicios.avisos)
    if descartados:
        avisos.append(f"Se descartaron {descartados} viaje(s) con distancia 0 duplicados "
                      "(mismo bus, línea y hora de inicio que otro viaje con distancia).")

    ventana = ventana_de_usos(validos)
    viaje_de_cada_uso = asignar_usos_a_viajes(usos_dia, ventana)
    viajes = construir_viajes(validos, viaje_de_cada_uso.dropna(), parametros)

    # Usos sin viaje: se muestra el vehículo como en el informe de servicios si existe
    sin_viaje = usos_dia[viaje_de_cada_uso.isna() & usos_dia["bus"].notna()]
    nombres = dict(zip(validos["bus"], validos["vehiculo"]))
    equipo = usos.original.loc[sin_viaje.index, usos.columnas["equipo"]]
    vehiculo = sin_viaje["bus"].map(nombres).fillna(equipo.astype(str).str.strip())
    usos_sin_viaje = construir_usos_sin_viaje(sin_viaje, vehiculo)
    grupos_sin_viaje = agrupar_usos_sin_viaje(
        sin_viaje, vehiculo, viaje_anterior_de_cada_uso(sin_viaje, ventana),
        parametros.minutos_agrupar_usos)

    resumen = construir_resumen(viajes, grupos_sin_viaje)
    casos = _detalle_de_casos(resumen.pop("_origen"), resumen, validos, servicios, usos,
                              usos_dia, viaje_de_cada_uso)
    viajes = viajes.drop(columns="_origen")
    grupos_sin_viaje = grupos_sin_viaje.drop(columns="_origen")
    usos_export = usos.original.loc[usos_dia.sort_values("momento").index].reset_index(drop=True)
    estados = viajes["Validación"].value_counts()

    indicadores = {
        "vehiculos": validos["bus"].nunique(),
        "viajes": len(viajes),
        "total_usuarios": len(usos_dia),
        "total_km": round(validos["distancia_m"].sum() / 1000, 1),
        "revisar": int(estados.get(Validacion.REVISAR, 0)),
        "km_bajo": int(estados.get(Validacion.KM_BAJO, 0)),
        "usos_sin_viaje": len(usos_sin_viaje),
        "grupos_sin_viaje": len(grupos_sin_viaje),
        "total_revisar": len(resumen),
    }

    return ResultadoAnalisis(
        fecha=fecha,
        parametros=parametros,
        viajes=viajes,
        usos_sin_viaje=usos_sin_viaje,
        grupos_sin_viaje=grupos_sin_viaje,
        resumen=resumen,
        servicios=_ordenar_servicios(servicios, validos),
        usos=usos_export,
        columnas_servicios=servicios.columnas,
        indicadores=indicadores,
        avisos=avisos + usos.avisos + _avisos_rutas_sin_parametros(validos, parametros),
        tipo_dia=tipo_dia,
        casos=casos,
        horarios_viajes=validos[["bus", "inicio", "fin"]].reset_index(drop=True),
    )
