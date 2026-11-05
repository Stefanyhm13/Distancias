"""
Lectura y validación de los archivos de entrada.

Cada lector devuelve:
  - `original`: el archivo tal cual (para exportarlo en el Excel final)
  - `tabla`:    columnas estandarizadas con nombres fijos para el análisis
  - `avisos`:   observaciones no bloqueantes para mostrar al usuario

Si el archivo no se puede usar, se lanza `ErrorDeArchivo` con un mensaje
claro para el usuario (en lugar de dar resultados equivocados).
"""
from dataclasses import dataclass, field

import pandas as pd
from openpyxl.utils import column_index_from_string

from config import (
    LINEAS_SAO, SERVICIOS_COLUMNAS, SERVICIOS_FILA_ENCABEZADO,
    SERVICIOS_FORMATO_FECHA, SERVICIOS_HOJA, USOS_COLUMNAS, Columna,
)
from src.normalizacion import (
    normalizar_bus, normalizar_circulacion, normalizar_linea, normalizar_texto, parsear_hora,
)

# pandas 3 avisa que cambiará el lector de .xlsx por defecto; se mantiene openpyxl.
# (En pandas 2 esta opción no existe y no hace falta.)
try:
    pd.set_option("io.excel.xlsx.reader", "openpyxl")
except Exception:
    pass


class ErrorDeArchivo(Exception):
    """El archivo no tiene la estructura esperada. El mensaje es para el usuario."""


@dataclass
class DatosLeidos:
    original: pd.DataFrame
    tabla: pd.DataFrame
    columnas: dict                       # clave lógica -> encabezado real
    avisos: list = field(default_factory=list)


# ── Utilidades internas ───────────────────────────────────────────────────────

def _leer_excel(archivo, nombre_archivo: str, **opciones) -> pd.DataFrame:
    if hasattr(archivo, "seek"):        # un archivo subido puede leerse más de una vez
        archivo.seek(0)
    try:
        df = pd.read_excel(archivo, **opciones)
    except ValueError as e:
        hoja = opciones.get("sheet_name")
        if hoja and "not found" in str(e).lower():
            raise ErrorDeArchivo(
                f"El archivo de {nombre_archivo} no tiene la hoja '{hoja}'."
            ) from e
        raise ErrorDeArchivo(f"No se pudo leer el archivo de {nombre_archivo}: {e}") from e
    except Exception as e:
        raise ErrorDeArchivo(f"No se pudo leer el archivo de {nombre_archivo}: {e}") from e

    df.columns = [str(c).strip() for c in df.columns]
    return df.dropna(how="all")


def resolver_columnas(df: pd.DataFrame, esperadas: dict[str, Columna],
                      nombre_archivo: str) -> tuple[dict, list]:
    """Ubica cada columna esperada por su encabezado (o por su letra de respaldo)."""
    por_nombre = {normalizar_texto(c): c for c in df.columns}
    resueltas, faltantes, avisos = {}, [], []

    for clave, col in esperadas.items():
        encontrada = next(
            (por_nombre[n] for n in map(normalizar_texto, col.nombres) if n in por_nombre),
            None,
        )
        if encontrada is None and col.letra:
            indice = column_index_from_string(col.letra) - 1
            if indice < len(df.columns):
                encontrada = df.columns[indice]
                avisos.append(
                    f"{nombre_archivo}: '{col.descripcion}' se tomó de la columna "
                    f"{col.letra} ('{encontrada}') porque no se encontró su encabezado."
                )
        if encontrada is None and not col.obligatoria:
            continue
        if encontrada is None:
            faltantes.append(col.descripcion + (f" (columna {col.letra})" if col.letra else ""))
        else:
            resueltas[clave] = encontrada

    if faltantes:
        encontrados = [c for c in df.columns if not c.startswith("Unnamed")][:12]
        raise ErrorDeArchivo(
            f"Al archivo de {nombre_archivo} le faltan columnas: {', '.join(faltantes)}. "
            f"Encabezados encontrados: {', '.join(encontrados) or '(ninguno)'}. "
            "Verifica que sea el archivo correcto y que no se haya modificado la plantilla."
        )
    return resueltas, avisos


def _tiene_columnas(archivo, columnas: dict[str, Columna], **opciones) -> bool:
    """True si el archivo, leído con `opciones`, tiene todas esas columnas por nombre."""
    try:
        df = _leer_excel(archivo, "", nrows=0, **opciones)
    except ErrorDeArchivo:
        return False
    encabezados = {normalizar_texto(c) for c in df.columns}
    return all(any(normalizar_texto(n) in encabezados for n in col.nombres)
               for col in columnas.values() if col.obligatoria)


def _verificar_archivo_correcto(archivo, nombre: str, error: ErrorDeArchivo) -> None:
    """Si el archivo parece ser el del otro cargador, lo dice claramente."""
    if nombre == "servicios":
        es_el_otro = _tiene_columnas(archivo, USOS_COLUMNAS, header=0)
        otro = "usos"
    else:
        es_el_otro = _tiene_columnas(archivo, {"vehiculo": SERVICIOS_COLUMNAS["vehiculo"]},
                                     sheet_name=SERVICIOS_HOJA,
                                     header=SERVICIOS_FILA_ENCABEZADO - 1)
        otro = "servicios"
    if es_el_otro:
        raise ErrorDeArchivo(
            f"Parece que en el espacio de '{nombre.capitalize()}' cargaste el archivo de {otro}. "
            "Revisa que cada archivo esté en su lugar."
        ) from error
    raise error


def _a_fecha_hora(serie: pd.Series) -> pd.Series:
    """Convierte a fecha-hora aceptando el formato del informe o fechas reales de Excel."""
    if pd.api.types.is_datetime64_any_dtype(serie):
        return serie
    resultado = pd.to_datetime(serie, format=SERVICIOS_FORMATO_FECHA, errors="coerce")
    pendientes = resultado.isna() & serie.notna()
    if pendientes.any():
        resultado[pendientes] = pd.to_datetime(
            serie[pendientes], dayfirst=True, errors="coerce", format="mixed"
        )
    return resultado


def _a_fecha(serie: pd.Series) -> pd.Series:
    """Fecha sin hora. Acepta fechas de Excel, 'aaaa-mm-dd' o 'dd/mm/aaaa'."""
    if pd.api.types.is_datetime64_any_dtype(serie):
        return serie.dt.normalize()
    resultado = pd.to_datetime(serie, format="ISO8601", errors="coerce")
    pendientes = resultado.isna() & serie.notna()
    if pendientes.any():
        resultado[pendientes] = pd.to_datetime(
            serie[pendientes], dayfirst=True, errors="coerce", format="mixed"
        )
    return resultado.dt.normalize()


# ── Lectores públicos ─────────────────────────────────────────────────────────

def leer_servicios(archivo) -> DatosLeidos:
    nombre = "servicios"
    try:
        df = _leer_excel(archivo, nombre, sheet_name=SERVICIOS_HOJA,
                         header=SERVICIOS_FILA_ENCABEZADO - 1)
        cols, avisos = resolver_columnas(df, SERVICIOS_COLUMNAS, nombre)
    except ErrorDeArchivo as e:
        _verificar_archivo_correcto(archivo, nombre, e)

    tabla = pd.DataFrame({
        "numero": df[cols["numero"]],
        "vehiculo": df[cols["vehiculo"]],
        "bus": df[cols["vehiculo"]].map(normalizar_bus),
        "linea": df[cols["linea"]].map(normalizar_linea),
        "circulacion": (df[cols["circulacion"]].map(normalizar_circulacion)
                        if "circulacion" in cols else None),
        "distancia_m": pd.to_numeric(df[cols["distancia"]], errors="coerce"),
        "inicio": _a_fecha_hora(df[cols["inicio"]]),
        "fin": _a_fecha_hora(df[cols["fin"]]),
        "inicio_servicio": _a_fecha_hora(df[cols["inicio_servicio"]]),
        "fin_servicio": _a_fecha_hora(df[cols["fin_servicio"]]),
    }, index=df.index)

    if tabla["inicio"].notna().sum() == 0:
        raise ErrorDeArchivo(
            f"La columna '{cols['inicio']}' del archivo de servicios no tiene fechas válidas "
            "(formato esperado: dd/mm/aaaa hh:mm:ss)."
        )
    if tabla["distancia_m"].notna().sum() == 0:
        raise ErrorDeArchivo(
            f"La columna '{cols['distancia']}' del archivo de servicios no tiene distancias numéricas."
        )

    sin_horario = (tabla["bus"].notna() & (tabla["inicio"].isna() | tabla["fin"].isna())).sum()
    if sin_horario:
        avisos.append(f"{sin_horario} servicio(s) sin hora de inicio o fin válida: "
                      "no se tienen en cuenta en el análisis.")

    no_reconocidas = sorted(set(tabla["linea"].dropna()) - set(LINEAS_SAO))
    if no_reconocidas:
        avisos.append(f"Líneas que no están en el listado del sistema: {', '.join(no_reconocidas)}.")

    original = df.copy()
    original[cols["linea"]] = tabla["linea"]          # línea limpia en el informe exportado
    return DatosLeidos(original, tabla, cols, avisos)


def leer_usos(archivo) -> DatosLeidos:
    nombre = "usos"
    try:
        df = _leer_excel(archivo, nombre, header=0)
        cols, avisos = resolver_columnas(df, USOS_COLUMNAS, nombre)
    except ErrorDeArchivo as e:
        _verificar_archivo_correcto(archivo, nombre, e)

    fecha = _a_fecha(df[cols["fecha"]])

    # Se parsea cada hora distinta una sola vez (los archivos de usos son grandes)
    horas_unicas = df[cols["hora"]].drop_duplicates()
    mapa = {h: parsear_hora(h) for h in horas_unicas}
    horas = df[cols["hora"]].map(mapa)
    desfase = pd.to_timedelta(
        horas.map(lambda h: h.hour * 3600 + h.minute * 60 + h.second if h is not None else None),
        unit="s",
    )

    tabla = pd.DataFrame({
        "bus": df[cols["equipo"]].map(normalizar_bus),
        "linea": df[cols["linea"]].map(normalizar_linea) if "linea" in cols else None,
        "fecha": fecha.dt.date,
        "momento": fecha + desfase,
    }, index=df.index)

    if tabla["fecha"].notna().sum() == 0:
        raise ErrorDeArchivo(f"La columna '{cols['fecha']}' del archivo de usos no tiene fechas válidas.")

    return DatosLeidos(df, tabla, cols, avisos)
