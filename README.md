# Recuperación de Km · SAO

Aplicación web (Streamlit) que cruza el **informe de servicios** con el **archivo de usos**
para detectar viajes en los que un vehículo tuvo pasajeros pero no reportó kilómetros
(o reportó muy pocos), y usos que no coinciden con ningún viaje. Son km potencialmente
recuperables.

## Instalación

Requiere Python 3.10 o superior y Streamlit 1.37 o superior.

```bash
pip install -r requirements.txt
```

## Uso

```bash
streamlit run app.py
```

1. (Opcional) **⚙️ Modificar parámetros**: la ventana tiene una pestaña por tipo de día
   (**HÁBIL**, **SÁBADO** y **DOMINGO**), cada una con su cumplimiento exigido (%),
   distancia y tiempo de ciclo por ruta (el tiempo de ciclo cambia según el tipo de día)
   y minutos para agrupar usos sin viaje. Los cambios se guardan en `parametros.json` y se
   conservan para los próximos usos.
2. Cargar el **archivo de usos** (`Usos.xlsx`).
3. Cargar el **archivo de servicios** (`PlantillaGestionServicios`).
4. Clic en **Analizar día**. La app lee la fecha del informe, detecta con el calendario
   colombiano si es día HÁBIL (lunes a viernes), SÁBADO o DOMINGO (los festivos cuentan
   como domingo) y muestra un aviso para **confirmar** o **cambiar** el tipo de día
   (por ejemplo, si hay un festivo nuevo por decreto que el calendario aún no tiene).
5. Revisar los resultados en pantalla y descargar el informe Excel.

En las tablas:
- Clic en el título de una columna para ordenarla (los números se ordenan como números:
  en "Diferencia (m)", *de menor a mayor* muestra primero los viajes a los que más metros
  les faltaron).
- **🔎 Buscar por columna** abre un campo de búsqueda para cada columna.
- Los textos de Streamlit (cargador de archivos, menús de las tablas, etc.) se muestran
  en español (`ui/traduccion.py`).

## Tipo de día y festivos

`src/calendario.py` usa la librería `holidays` (calendario oficial de festivos de
Colombia). Para tener los festivos más recientes basta con actualizarla:

```bash
pip install -U holidays
```

Si la librería no está instalada, los festivos se calculan con las reglas de la
Ley 51 de 1983 (Ley Emiliani) y la Ley 2578 de 2026. En cualquier caso el usuario
confirma el tipo de día antes de cada análisis.

## Archivos de entrada

**Servicios** — hoja `Hoja1`, encabezados en la fila 4.

| Dato | Encabezado | Columna de respaldo |
|---|---|---|
| N° de viaje | # | A |
| Circulación | H-T (ej. 0-503) | H |
| Vehículo | Vehículos | — |
| Ruta | Línea | E |
| Inicio de servicio (para usos) | Inicio de Servicio | I |
| Fin de servicio (para usos) | Fin de Servicio | J |
| Distancia (metros) | Distancia | L |
| Inicio servicio efectivo | Inicio Servicio Efectivo | O |
| Fin servicio efectivo | Fin Servicio Efectivo | P |

**Usos** — primera hoja, encabezados en la fila 1: `Fecha`, `Hora`, `Equipo` y, opcional,
`Línea` (si está, se usa para agrupar los usos sin viaje por ruta).

Las columnas se buscan por su encabezado. Si un encabezado no se encuentra se usa la
columna de respaldo y se muestra una observación. Si falta una columna obligatoria,
la app muestra un error claro en lugar de calcular con datos equivocados.

## Cómo se calcula

Se analiza **cada viaje por separado**. Un viaje es cada registro del informe de servicios.

- La fecha del informe es la que más se repite en el inicio de los servicios. Se usan los
  usos de esa fecha y los de la madrugada siguiente (hasta las 03:30), para los viajes que
  pasan de medianoche.
- **Duración del viaje** = Fin Servicio Efectivo − Inicio Servicio Efectivo (columnas O y P).
- **Mínimo del viaje** = duración en minutos × distancia al 95 % por minuto de su ruta,
  según el tipo de día. Ejemplo: viaje de la 6019 en día hábil de 25,9 minutos →
  4.130 m ÷ 59,4 min × 0,95 = 66,05 m por minuto → 25,9 × 66,05 = 1.711 m.
- **Usos del viaje**: usos del mismo bus cuya hora está entre **"Inicio de Servicio" y
  "Fin de Servicio"** (columnas I y J), que incluyen el abordaje antes del inicio efectivo.
  La duración y el mínimo de distancia sí usan el inicio y fin **efectivos** (O y P).
- **Usos sin viaje**: cada uso que no cae dentro de ningún viaje de su bus va a revisar con
  recorrido 0. Los usos seguidos se **agrupan** en una fila cuando son del mismo bus, de la
  misma ruta (si el archivo de usos trae la columna "Línea"), no hay un viaje entre ellos y
  cada uno está a 15 minutos o menos del anterior (configurable en "Modificar parámetros").
  En la app se pueden ver agrupados o uno por uno.
- **Viajes duplicados:** si un bus tiene dos viajes en la misma línea con la misma hora de
  inicio efectivo, y uno tiene distancia 0 y el otro mayor, el de 0 se descarta por ser un
  error del informe. Se avisa en "Observaciones".

| Recorrido del viaje (m) | Usos en el viaje | Validación |
|---|---|---|
| 0 | 0 | No operó |
| 0 | > 0 | **REVISAR - Distancia 0** |
| menor al mínimo | > 0 | **REVISAR - Equivalencia** |
| cualquier otro caso | | Operó |
| (usos fuera de todo viaje) | ≥ 1 | **REVISAR - Uso sin viaje** (recorrido 0) |

### Distancia por ruta

Configurable en **Modificar parámetros**, una tabla por tipo de día:

| Columna | Cálculo |
|---|---|
| Distancia de ciclo (m) | Dato editable |
| Tiempo de ciclo (min) | Dato editable, distinto para hábil, sábado y domingo/festivo |
| Distancia x min | Distancia de ciclo ÷ Tiempo de ciclo |
| Distancia al 95% x min | Distancia x min × cumplimiento exigido (0,95 por defecto) |

El **tiempo de ciclo** es integración → cabecera → integración (dos itinerarios). Los valores
iniciales salen de la tabla de tiempos de viaje por tipo de día (tiempo de ciclo = tiempo de
itinerario × 2) y están en `RUTAS_INICIALES` de `config.py`. La distancia de ciclo es la misma
para los tres tipos de día. Las rutas 6014A y 6016A no estaban en esa tabla y conservan el
tiempo anterior en los tres días.

Las rutas **sin parámetros** (por ejemplo 6017) solo se revisan por "sin distancia" y
aparecen en "Observaciones".

## Informe Excel

Diseño con los colores corporativos de la app: cada hoja tiene título, una línea que explica
su contenido, fecha del informe, encabezados verdes con filtros, filas alternadas y paneles
fijos. Las hojas con validación traen una **leyenda de colores**:

| Color | Validación |
|---|---|
| Verde | Operó: cumplió la distancia mínima |
| Gris | No operó: viaje sin distancia ni usos |
| Rojo | REVISAR - Distancia 0: registro sin distancia con usos |
| Naranja | REVISAR - Equivalencia: menos del mínimo y con usos |
| Morado | REVISAR - Uso sin viaje: uso fuera de todo viaje (km 0) |

Las filas a revisar llevan un tinte suave de su color y la diferencia negativa sale en rojo.

| Hoja | Contenido |
|---|---|
| Informe de Servicios | Servicios originales ordenados por vehículo y hora (sin los duplicados en 0) |
| Usos | Usos del día ordenados por hora |
| Usos sin viaje | Usos sin viaje agrupados: Vehículo, Línea, Fecha, Inicio y Fin (primer y último uso), Duración, Usos, Recorrido 0 |
| Usos sin viaje - detalle | Un registro por uso sin viaje |
| Viajes | Un registro por viaje: Inicio y Fin de servicio (usos), Inicio y Fin efectivo (duración), Recorrido, Mínimo, Diferencia, Usos, Validación |
| Resumen | Tarjetas de indicadores (fórmulas) y la lista de viajes y grupos de usos a revisar. El archivo se abre en esta hoja |
| Parámetros | Distancias por ruta y supuestos del análisis; las columnas calculadas son fórmulas |

## Configuración

- **Desde la app** (⚙️ Modificar parámetros): por cada tipo de día, cumplimiento exigido
  (95 % inicial), distancia y tiempo de ciclo por ruta y minutos para agrupar los usos sin viaje.
  Se guardan en `parametros.json`. El botón "Valores iniciales" vuelve a los de `config.py`
  solo en la pestaña donde se presiona (con el tiempo de ciclo de ese tipo de día).
- **En [`config.py`](config.py)**: valores iniciales de las rutas (distancia y tiempo de ciclo
  hábil, sábado y domingo), porcentaje exigido inicial (95 %),
  hora límite de la madrugada siguiente, listado de líneas y estructura esperada de los archivos.

## Estructura del proyecto

```
app.py                  Interfaz: arma la página y conecta las piezas
config.py               Reglas de negocio y estructura de los archivos
src/
  normalizacion.py      Limpieza de valores (buses, líneas, horas)
  calendario.py         Tipo de día (hábil, sábado, domingo/festivo) con festivos de Colombia
  lectura.py            Lectura y validación de los Excel de entrada
  parametros.py         Parámetros por ruta: cálculos, validación, guardar y cargar
  analisis.py           Análisis por viaje: mínimo, usos por viaje, usos sin viaje
  pso.py                Lectura del PSO (hoja Horarios) e itinerarios a reclamar
  consolidado.py        Consolidado por quincena: unir casos, guardar en la base
  reporte_consolidado.py  Excel del consolidado (Horarios, Resumen, Evidencia)
  reporte_excel.py      Generación y formato del informe Excel
  filtros.py            Filtros de las tablas
  historial.py          Base de datos SQLite del historial de días revisados
ui/
  componentes.py        Tarjetas, leyenda, tablas con filtros
  parametros.py         Ventana "Modificar parámetros" (una pestaña por tipo de día)
  tipo_dia.py           Aviso para confirmar o cambiar el tipo de día
  consolidado.py        PSO, casillas "Reclamar" y botón del consolidado
  historial.py          Sección "Historial de días revisados"
  ilustraciones.py      Ilustraciones de los buses (SVG)
  traduccion.py         Textos de Streamlit en español
  estilos.css           Estilos visuales
assets/logo.png
parametros.json         Parámetros guardados desde la app (por tipo de día)
tests/                  Pruebas automáticas con datos de ejemplo
datos/                  historial.db (se crea sola; no se sube a git)
consolidados/           Copias de los consolidados generados (no se sube a git)
```

## Pruebas

```bash
pip install -r requirements-dev.txt
python -m pytest
```

Ejecutar las pruebas después de cada cambio en la lógica.

## Consolidado de reclamación (por quincena)

La empresa reclama los km perdidos por quincena: **Q1** del 01 al 15 y **Q2** del 16 al
último día del mes. La app arma ese consolidado a partir de los casos que se revisan cada día.

1. **PSO:** en el panel izquierdo, tarjeta **📘 PSO · Horarios**, se carga una vez un archivo
   con la hoja **Horarios** (por ejemplo, un consolidado anterior). Se usan las columnas
   O a S: Tipo día, Ruta, Circulación, Hora y Distancia Media. Queda guardado en la base
   de datos; solo se vuelve a cargar cuando el PSO cambia.
2. Se analiza el día y se revisan los casos (en pantalla o en el Excel del día).
3. En la pestaña **Resumen REVISAR** se marcan en la columna **✔ Reclamar** los casos que se
   van a reclamar. La columna **📑 Consolidado** dice cuáles ya están incluidos.
4. Debajo de la tabla, **📑 Generar consolidado reclamación**: los casos se agregan al
   consolidado de la quincena de ese día (si ya existe, se agregan a los que ya tiene, en
   orden de fecha; un caso que ya estaba no se repite) y se descarga el Excel
   `Acumulado GPS <Mes> Q1.xlsx` / `Q2.xlsx`. También queda una copia en la carpeta
   `consolidados/`.
5. En **📂 Ver y corregir los registros** se puede corregir ruta, circulación o distancia
   (por ejemplo en los casos *REVISION DETALLADA*) o quitar registros. El Excel se arma
   siempre de nuevo con lo guardado, así que **las correcciones se hacen en la app** (lo que
   se cambie a mano en el Excel se pierde la próxima vez que se genere).

### Cómo se arma cada registro

| Columna (hoja Resumen) | De dónde sale |
|---|---|
| Unidad | Número del vehículo (SAO-008 → 8) |
| Fecha | Fecha del informe |
| Ruta / Circulación H-T | Línea y columna H-T del informe de servicios (0-503 → 503) |
| Hora inicio / Hora fin | Inicio y Fin del caso en la app |
| Usuarios | Usos del caso en ese rango |
| Hipervinculo | Lleva al bloque del caso en la hoja Evidencia |
| Distancia | Km a reclamar: fórmula al total de la evidencia (suma del PSO ÷ 1000) |

- **Distancia a reclamar:** del PSO se filtran las salidas del mismo tipo de día (Hábil,
  Sábado o Domingo; festivo = Domingo), ruta y circulación. Un itinerario empieza en su
  salida y termina cuando sale el siguiente de esa circulación. Se reclaman los itinerarios
  que tienen **al menos la mitad de su duración dentro del rango del caso**
  (`PSO_PARTE_MINIMA_ITINERARIO` en `config.py`).
  Ejemplo, domingo, 6016, circulación 503, caso 06:30:00 – 07:00:28: el de 06:34 (termina
  06:59) se reclama → 6.117 m = 6,117 km; el de 06:59 no.
- **Casos Equivalencia** (SAE registró algo de distancia, pero menos de la programada): se
  reclama lo que falta, es decir, distancia del PSO − distancia registrada en SAE. En la
  evidencia se ven las tres cifras: según PSO, registrado en SAE y a reclamar.
- **PSO:** se lee la hoja Horarios completa (todas sus columnas, que se copian igual en el
  consolidado); para el cálculo solo se usan Tipo día, Ruta, Circulación, Hora y Distancia Media.
- **Casos seguidos:** si se marcan casos de la misma unidad, ruta y circulación que van uno
  tras otro (el siguiente empieza 15 minutos o menos después; `MINUTOS_CASOS_SEGUIDOS`), se
  unen en un solo registro con usuarios y distancia sumados.
- **Usos sin información en SAE:** ruta y circulación quedan como **REVISION DETALLADA**,
  sin distancia, y la evidencia son solo los usos.
- **Evidencia:** por cada registro, la descripción de la novedad, las filas del informe de
  servicios, el recorte del PSO con la distancia en km debajo y los usos del rango.

## Historial de días revisados (base de datos)

Cada día que se analiza se guarda automáticamente en `datos/historial.db`
(SQLite: un solo archivo, no hay que instalar nada; se crea solo la primera vez).

- **Día repetido:** si se analiza un día que ya está guardado, aparece la ventana
  *"Este día ya está guardado — ¿Desea reemplazar los valores que ya están de ese día?"*
  con la comparación entre lo guardado y lo nuevo. Si se elige *No, conservar*, se puede
  reemplazar después con el botón **🔁 Reemplazar** junto al aviso del resultado.
- **Consultar:** bajando en la página está la sección **📚 Historial de días revisados**,
  con filtros por **año, mes y día** y opción de ver los gráficos por día, mes o año.
- **Métricas:** días revisados, km recorridos, km por recuperar, casos a revisar, días
  destacados (más y menos km por recuperar / recorridos) y gráficos por período, por ruta,
  por vehículo, por tipo de caso, por hora del día y por día de la semana.
- **Km por recuperar** = lo que les faltó para llegar al mínimo a los casos *REVISAR - Distancia 0* y
  *REVISAR - Equivalencia* (la diferencia negativa, en km).
- **Descargar:** en *🔎 Consultar un día guardado* se elige el día y se descarga su Excel
  tal como se generó. También se pueden ver sus casos a revisar o eliminarlo.

**Respaldo:** para no perder el historial, el PSO y los consolidados basta con copiar la
carpeta `datos/`.
