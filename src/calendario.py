"""
Tipo de día según el calendario colombiano.

  HABIL    lunes a viernes que no son festivo
  SABADO   sábados que no son festivo
  DOMINGO  domingos y festivos

Los festivos se toman de la librería `holidays` (calendario oficial de Colombia,
se actualiza con `pip install -U holidays`). Si la librería no está instalada se
calculan aquí con las mismas reglas de la Ley 51 de 1983 ("Ley Emiliani").

Un festivo nuevo por decreto puede no estar en el calendario todavía: por eso la
app siempre muestra el tipo detectado y deja cambiarlo antes de analizar.
"""
from datetime import date, timedelta

HABIL = "HABIL"
SABADO = "SABADO"
DOMINGO = "DOMINGO"
TIPOS_DIA = [HABIL, SABADO, DOMINGO]

# Cómo se muestra cada tipo en pantalla y en el Excel
NOMBRES_TIPO = {HABIL: "HÁBIL", SABADO: "SÁBADO", DOMINGO: "DOMINGO"}
DIAS_SEMANA = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


# ── Festivos calculados (respaldo si no está la librería holidays) ────────────

def _pascua(anio: int) -> date:
    """Domingo de Pascua (algoritmo de Butcher / Meeus)."""
    a, b, c = anio % 19, anio // 100, anio % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = (h + l - 7 * m + 114) % 31 + 1
    return date(anio, mes, dia)


def _al_lunes(d: date) -> date:
    """Ley Emiliani: el festivo se pasa al lunes siguiente si no cae en lunes."""
    return d + timedelta(days=(7 - d.weekday()) % 7)


def festivos_calculados(anio: int) -> dict[date, str]:
    pascua = _pascua(anio)
    fijos = {
        date(anio, 1, 1): "Año Nuevo",
        date(anio, 5, 1): "Día del Trabajo",
        date(anio, 7, 20): "Día de la Independencia",
        date(anio, 8, 7): "Batalla de Boyacá",
        date(anio, 12, 8): "Inmaculada Concepción",
        date(anio, 12, 25): "Navidad",
        pascua - timedelta(days=3): "Jueves Santo",
        pascua - timedelta(days=2): "Viernes Santo",
    }
    trasladables = {
        date(anio, 1, 6): "Día de los Reyes Magos",
        date(anio, 3, 19): "Día de San José",
        date(anio, 6, 29): "San Pedro y San Pablo",
        date(anio, 8, 15): "La Asunción de la Virgen",
        date(anio, 10, 12): "Día de la Raza",
        date(anio, 11, 1): "Todos los Santos",
        date(anio, 11, 11): "Independencia de Cartagena",
        pascua + timedelta(days=39): "Ascensión del Señor",
        pascua + timedelta(days=60): "Corpus Christi",
        pascua + timedelta(days=68): "Sagrado Corazón",
    }
    if anio >= 2026:                                    # Ley 2578 de 2026
        trasladables[date(anio, 7, 9)] = "Nuestra Señora del Rosario de Chiquinquirá"
    festivos = dict(fijos)
    for dia, nombre in trasladables.items():
        festivos.setdefault(_al_lunes(dia), nombre)
    return festivos


# ── Consulta ──────────────────────────────────────────────────────────────────

def nombre_festivo(fecha: date) -> str | None:
    """Nombre del festivo colombiano de esa fecha, o None si no es festivo."""
    try:
        import holidays
        calendario = holidays.country_holidays("CO", years=fecha.year, language="es")
        nombre = calendario.get(fecha)
        if nombre:
            return str(nombre)
        return None
    except Exception:              # librería no instalada o sin idioma: cálculo propio
        return festivos_calculados(fecha.year).get(fecha)


def fuente_calendario() -> str:
    try:
        import holidays  # noqa: F401
        return "calendario oficial de festivos de Colombia (librería holidays)"
    except Exception:
        return "calendario de festivos de Colombia (Ley 51 de 1983)"


def tipo_de_dia(fecha: date) -> tuple[str, str]:
    """(tipo, explicación). Ej: ('DOMINGO', 'Festivo: Día de la Raza')."""
    festivo = nombre_festivo(fecha)
    if festivo:
        return DOMINGO, f"Festivo: {festivo}"
    dia = fecha.weekday()
    if dia == 6:
        return DOMINGO, "Domingo"
    if dia == 5:
        return SABADO, "Sábado"
    return HABIL, f"Día hábil ({DIAS_SEMANA[dia]})"


def fecha_larga(fecha: date) -> str:
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
             "septiembre", "octubre", "noviembre", "diciembre"]
    return (f"{DIAS_SEMANA[fecha.weekday()].capitalize()} {fecha.day} de "
            f"{meses[fecha.month - 1]} de {fecha.year}")
