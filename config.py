"""
Configuración central de la aplicación.

Todas las reglas de negocio y la estructura esperada de los archivos viven aquí.
Si cambia una regla (umbral, horario, rutas) o la plantilla de un informe,
solo se modifica este archivo.
"""
from dataclasses import dataclass


# ── Reglas de negocio ─────────────────────────────────────────────────────────

# El día operativo se extiende hasta esta hora del día siguiente: los usos de
# madrugada (por ejemplo 00:20) se cruzan con los viajes que pasan de medianoche.
USOS_DIA_SIGUIENTE_HASTA = "03:30"


# Rutas (Línea) del sistema
LINEAS_SAO = [
    "6001", "6002", "6002A", "6003", "6004", "6004A", "6005", "6006C",
    "6007", "6008", "6009", "6010C", "6011", "6012", "6012A", "6013",
    "6014", "6014A", "6015A", "6016", "6016A", "6017", "6018", "6019",
    "6019A", "6020", "6021", "6022", "6022A", "6023", "6024", "6025", "6025B",
]


# ── Parámetros modificables desde la interfaz ─────────────────────────────────
# Estos son los valores INICIALES. Los que se guardan desde la ventana
# "Modificar parámetros" quedan en ARCHIVO_PARAMETROS y tienen prioridad.

ARCHIVO_PARAMETROS = "parametros.json"

# Base de datos del historial de días revisados (se crea sola la primera vez)
ARCHIVO_BASE_DATOS = "datos/historial.db"

# Porcentaje de la distancia por minuto de cada ruta que se exige en cada viaje (95 %)
PORCENTAJE_EXIGIDO_INICIAL = 0.95

# Usos sin viaje del mismo bus (y ruta) separados por esta cantidad de minutos o
# menos, sin un viaje entre ellos, se agrupan en una sola fila.
MINUTOS_AGRUPAR_USOS_INICIAL = 15

# (Línea, Distancia de ciclo en metros, Tiempo de ciclo en minutos para HÁBIL, SÁBADO y
# DOMINGO/festivo). El tiempo de ciclo es integración → cabecera → integración (dos
# itinerarios), tomado de la tabla de tiempos de viaje por tipo de día.
RUTAS_INICIALES = [
    ("6001", 5549, 36, 36, 30),
    ("6002", 14151, 70.8, 70.4, 66),
    ("6002A", 10844, 66, 64, 56),
    ("6003", 7808, 38, 38, 36),
    ("6004", 13240, 64.4, 62, 58),
    ("6004A", 14865, 66, 64, 60),
    ("6005", 10230, 63, 63, 58),
    ("6006C", 3213, 17, 18, 24),
    ("6007", 7680, 63, 62, 60),
    ("6008", 9079, 61.2, 64.24, 58),
    ("6009", 9770, 72, 72, 57.6),
    ("6010C", 12701, 83.12, 78.6, 71),
    ("6011", 3970, 35.4, 32.55, 32),
    ("6012", 5748, 34.2, 34.788, 40),
    ("6012A", 4438, 33.3, 33, 30.8),
    ("6013", 8285, 63.18, 62.4, 55.68),
    ("6014", 5104, 28.4, 28.2, 26),
    ("6014A", 5352, 30, 30, 30),
    ("6015A", 10022, 66.12, 64.6, 60.4),
    ("6016", 12671, 72.6, 75.24, 63.6),
    ("6016A", 10974, 48.9474, 48.9474, 48.9474),
    ("6018", 7423, 56.52, 54.7232, 52.7232),
    ("6019", 4130, 59.4, 57.94, 51.94),
    ("6019A", 4318, 39.6, 35.2, 33),
    ("6020", 8588, 55.5, 54.6, 52.6),
    ("6021", 8161, 64.4, 61.56, 55.2),
    ("6022", 12643, 91.4, 89.2, 86.8),
    ("6022A", 13582, 98.4, 95, 90.4),
    ("6023", 3970, 28.34, 28.418, 28.496),
    ("6024", 5175, 28.7, 28.24, 28.2),
    ("6025", 6340, 26.28, 25.4, 24.6),
    ("6025B", 2585, 16.96, 16.96, 16.96),
]


# ── Consolidado de reclamación (por quincena) ─────────────────────────────────

# Carpeta donde se guarda una copia de cada consolidado generado
CARPETA_CONSOLIDADOS = "consolidados"

# Itinerarios del PSO que se reclaman en un caso: los que tienen al menos esta parte de
# su duración dentro del rango del caso (hora de inicio a hora de fin). Un itinerario
# empieza a la hora de su salida y termina cuando sale el siguiente de su circulación.
# 0.5 = la mitad o más del itinerario ocurrió durante la novedad.
PSO_PARTE_MINIMA_ITINERARIO = 0.5

# Casos seleccionados de la misma unidad, ruta y circulación se unen en un solo registro
# si el siguiente empieza a esta cantidad de minutos o menos después de que termina el otro.
MINUTOS_CASOS_SEGUIDOS = 15

# Texto para los casos de usos sin información en SAE (no se sabe ruta ni circulación)
REVISION_DETALLADA = "REVISION DETALLADA"


# ── Estados de validación ─────────────────────────────────────────────────────

class Validacion:
    NO_OPERO = "No operó"
    OPERO = "Operó"
    REVISAR = "REVISAR - Distancia 0"           # viaje sin distancia pero con usos
    KM_BAJO = "REVISAR - Equivalencia"          # viaje con usos y distancia bajo el mínimo
    USO_SIN_VIAJE = "REVISAR - Uso sin viaje"   # uso que no coincide con ningún viaje

    # Nombres que se usaban antes (para actualizar los días ya guardados en el historial)
    ANTERIORES = {"REVISAR": "REVISAR - Distancia 0", "REVISAR - Km bajo": "REVISAR - Equivalencia"}

    @staticmethod
    def es_revisar(valor) -> bool:
        """True para cualquier caso a revisar (Distancia 0, Equivalencia o Uso sin viaje)."""
        return str(valor).startswith("REVISAR")


# ── Estructura de los archivos de entrada ─────────────────────────────────────

@dataclass(frozen=True)
class Columna:
    """Columna esperada en un archivo.

    Se busca primero por nombre de encabezado (sin importar mayúsculas, tildes
    ni espacios). Si no se encuentra y hay letra de respaldo, se usa la letra.
    """
    descripcion: str
    nombres: tuple
    letra: str | None = None
    obligatoria: bool = True


# Informe de servicios (PlantillaGestionServicios)
SERVICIOS_HOJA = "Hoja1"
SERVICIOS_FILA_ENCABEZADO = 4          # fila de Excel donde están los títulos
SERVICIOS_FORMATO_FECHA = "%d/%m/%Y %H:%M:%S"

SERVICIOS_COLUMNAS = {
    "numero":    Columna("# (número de viaje)", ("#",), letra="A"),
    # H-T: circulación del servicio ('0-503' -> circulación 503 del PSO)
    "circulacion": Columna("H-T (circulación)", ("H-T", "HT", "Circulación", "Circulacion"),
                           letra="H", obligatoria=False),
    "vehiculo":  Columna("Vehículos", ("Vehículos", "Vehiculo", "Vehículo")),
    "linea":     Columna("Línea", ("Línea", "Linea"), letra="E"),
    "distancia": Columna("Distancia (m)", ("Distancia",), letra="L"),
    # Inicio y Fin de Servicio: ventana para asociar los usos a cada viaje
    "inicio_servicio": Columna("Inicio de Servicio", ("Inicio de Servicio",), letra="I"),
    "fin_servicio":    Columna("Fin de Servicio", ("Fin de Servicio",), letra="J"),
    # Inicio y Fin efectivos: duración del viaje y distancia mínima
    "inicio":    Columna("Inicio servicio efectivo",
                         ("Inicio Servicio Efectivo", "Inicio servicio"), letra="O"),
    "fin":       Columna("Fin servicio efectivo",
                         ("Fin Servicio Efectivo", "Fin servicio"), letra="P"),
}

# Archivo de usos (Usos.xlsx)
USOS_COLUMNAS = {
    "fecha":  Columna("Fecha", ("Fecha",)),
    "hora":   Columna("Hora", ("Hora",)),
    "equipo": Columna("Equipo", ("Equipo",)),
    # Opcional: si el archivo de usos trae la ruta, se usa para agrupar usos sin viaje
    "linea":  Columna("Línea", ("Línea", "Linea", "Ruta"), obligatoria=False),
}
