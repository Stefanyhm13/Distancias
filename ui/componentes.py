"""Piezas visuales reutilizables de la interfaz."""
import base64
import inspect
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from config import Validacion
from src.calendario import NOMBRES_TIPO
from src.filtros import TODOS, aplicar_filtros, opciones
from ui import ilustraciones as il

# Las tablas de viajes y usos pueden tener muchas celdas para colorear
pd.set_option("styler.render.max_elements", 2_000_000)

RAIZ = Path(__file__).resolve().parent.parent
ARCHIVO_CSS = RAIZ / "ui" / "estilos.css"
ARCHIVO_LOGO = RAIZ / "assets" / "logo.png"
ARCHIVO_FUENTE = RAIZ / "assets" / "fonts" / "Outfit.ttf"   # Google Fonts, licencia OFL


def _css_fuente() -> str:
    """Letra Outfit incrustada en la página (funciona sin internet)."""
    if not ARCHIVO_FUENTE.exists():
        return ""
    datos = base64.b64encode(ARCHIVO_FUENTE.read_bytes()).decode()
    return f"""
    @font-face {{
        font-family: "Outfit"; font-style: normal; font-weight: 100 900; font-display: swap;
        src: url("data:font/ttf;base64,{datos}") format("truetype");
    }}
    html, body, .stApp,
    .stApp *:not([data-testid="stIconMaterial"]):not(.material-symbols-rounded):not(code):not(pre),
    [role="dialog"] *:not([data-testid="stIconMaterial"]):not(.material-symbols-rounded):not(code):not(pre) {{
        font-family: "Outfit", "Source Sans Pro", sans-serif !important;
    }}"""

ESTILO_VALIDACION = {
    Validacion.REVISAR: "background-color: #FFCCCC; color: #B71C1C; font-weight: bold",
    Validacion.KM_BAJO: "background-color: #FFE0B2; color: #E65100; font-weight: bold",
    Validacion.USO_SIN_VIAJE: "background-color: #E1BEE7; color: #6A1B9A; font-weight: bold",
    Validacion.OPERO: "background-color: #E8F5E9; color: #1B5E20",
    Validacion.NO_OPERO: "color: #999",
}

SUBTITULO = "Sistema Alimentador Oriental · Validación de km y usos por viaje"


def _html(contenido: str) -> None:
    st.markdown(contenido, unsafe_allow_html=True)


def cargar_estilos() -> None:
    fondo = il.uri(il.fondo_pagina())
    paisaje = il.uri(il.paisaje())
    _html(f"""<style>{_css_fuente()}
    {ARCHIVO_CSS.read_text(encoding='utf-8')}
    .stApp {{ background: url("{fondo}") center bottom / 100% auto no-repeat fixed, #E8EDE8; }}
    .header-escena {{ background-image: url("{paisaje}"); }}
    </style>""")


def encabezado() -> None:
    if ARCHIVO_LOGO.exists():
        logo_b64 = base64.b64encode(ARCHIVO_LOGO.read_bytes()).decode()
        logo = (f'<img class="header-logo" src="data:image/png;base64,{logo_b64}" alt="SAO">')
    else:
        logo = '<span style="font-size:2rem;">🌿</span>'
    _html(f"""
    <div class="header-bar">
        <div class="header-escena"></div>
        <div class="header-via">
            <img class="bus-anim bus-1" src="{il.uri(il.bus_alimentador())}" alt="">
            <img class="bus-anim bus-2" src="{il.uri(il.bus_electrico())}" alt="">
        </div>
        <div class="header-contenido">
            {logo}
            <div class="header-textos">
                <h1>Recuperación de Km · SAO</h1>
                <p>{SUBTITULO}</p>
            </div>
        </div>
    </div>""")


def titulo_seccion(texto: str) -> None:
    _html(f'<div class="section-title">{texto}</div>')


def selector_archivo(titulo: str, detalle: str, clave: str, tipos: list, icono: str):
    """Etiqueta + cargador de archivo + tarjeta de confirmación."""
    _html(f'<div class="archivo-titulo"><span>{icono} {titulo}</span>'
          f'<small>{detalle}</small></div>')
    archivo = st.file_uploader(clave, type=tipos, key=clave, label_visibility="collapsed")
    if archivo:
        tamano = round(archivo.size / 1024 / 1024, 1)
        _html(f"""
        <div class="file-card">
            <div class="file-icon">{icono}</div>
            <div><div class="file-name">{escape(archivo.name)}</div>
                 <div class="file-size">{tamano} MB</div></div>
            <div class="file-check">✅</div>
        </div>
        <div class="file-ok">✔ Cargado correctamente</div>""")
    return archivo


def aviso_pequeno(texto: str) -> None:
    _html(f'<div class="aviso-pequeno">{texto}</div>')


def leyenda(pct: str = "95%") -> None:
    """pct: porcentaje exigido vigente, para la explicación de Equivalencia."""
    _html(f"""<div class="leyenda-grid">
    <div class="leyenda-item"><span class="dot verde"></span> Operó: cumplió la distancia mínima</div>
    <div class="leyenda-item"><span class="dot blanco"></span> No operó: viaje sin distancia ni usos</div>
    <div class="leyenda-item"><span class="dot rojo"></span> REVISAR – Distancia 0: registro sin distancia con usos</div>
    <div class="leyenda-item"><span class="dot naranja"></span> REVISAR – Equivalencia: menos del mínimo
        (minutos del viaje × distancia al {pct} x min de la ruta)</div>
    <div class="leyenda-item"><span class="dot morado"></span> REVISAR – Uso sin viaje: uso fuera de
        todo viaje del bus (km 0)</div>
    </div>""")


def estado_vacio() -> None:
    _html(f"""
    <div class="empty-state">
        <img src="{il.uri(il.operadores())}" class="empty-ilustracion" alt="Operadores SAO">
        <p class="empty-titulo">¡Listos para revisar el día!</p>
        <div class="pasos">
            <div class="paso"><b>1</b><span>Carga el archivo de <strong>Usos</strong></span></div>
            <div class="paso"><b>2</b><span>Carga el informe de <strong>Servicios</strong></span></div>
            <div class="paso"><b>3</b><span>Presiona <strong>Analizar día</strong></span></div>
        </div>
        <p class="empty-nota">Los resultados aparecerán aquí y el día se guardará en el historial.</p>
    </div>""")


def banner_exito(fecha, nombre_usos: str, nombre_servicios: str, tipo_dia: str = "") -> None:
    tipo = (f" &nbsp;|&nbsp; Analizado como día <strong>{NOMBRES_TIPO.get(tipo_dia, tipo_dia)}"
            f"</strong>" if tipo_dia else "")
    _html(f"""
    <div class="success-banner">
        ✅ <strong>¡Hecho!</strong> Análisis completado correctamente.<br>
        <span style="font-weight:400;">Fecha: <strong>{fecha:%d/%m/%Y}</strong>{tipo}
        &nbsp;|&nbsp; <em>{escape(nombre_usos)}</em> + <em>{escape(nombre_servicios)}</em></span>
    </div>""")


def tarjeta_metrica(icono: str, valor: str, etiqueta: str, color: str = "") -> None:
    _html(f"""
    <div class="metric-card {color}">
        <span class="metric-icon">{icono}</span>
        <div class="metric-number {color}">{valor}</div>
        <div class="metric-label">{etiqueta}</div>
    </div>""")


def panel_metricas(filas: list[list[tuple]]) -> None:
    """Varias filas de tarjetas [(icono, valor, etiqueta, color, nota), ...] en una sola
    cuadrícula: mismo alto y bordes alineados. Una fila de 3 usa tarjetas más anchas."""
    tarjetas = ""
    for fila in filas:
        ancho = " ancho" if len(fila) == 3 else ""
        for icono, valor, etiqueta, color, *nota in fila:
            extra = f"<small>{nota[0]}</small>" if nota and nota[0] else ""
            tarjetas += (f'<div class="metric-card {color}{ancho}">'
                         f'<span class="metric-icon">{icono}</span>'
                         f'<div class="metric-number {color}">{valor}</div>'
                         f'<div class="metric-label">{etiqueta}{extra}</div></div>')
    _html(f'<div class="metric-panel">{tarjetas}</div>')


def numero(valor, decimales: int = 0) -> str:
    """Número al estilo colombiano: 28.243 / 20.163,9"""
    texto = f"{valor:,.{decimales}f}"
    return texto.replace(",", "_").replace(".", ",").replace("_", ".")


def fila_metricas(metricas: list[tuple]) -> None:
    """metricas: [(icono, valor, etiqueta, color), ...] en una fila."""
    for columna, metrica in zip(st.columns(len(metricas)), metricas):
        with columna:
            tarjeta_metrica(*metrica)


def _formato_metros(v) -> str:
    return f"{v:,.0f}".replace(",", ".")          # 2.579 / -1.314


def _formato_minutos(v) -> str:
    return f"{v:.1f}".replace(".", ",")          # 11,4


def _formatos(df: pd.DataFrame) -> dict:
    """{columna: función} para mostrar metros y minutos al estilo colombiano.

    Solo cambia cómo se VEN los números: por dentro siguen siendo números, así que al
    ordenar una columna (clic en su título) se ordena de menor a mayor de verdad
    (-1.639 antes que -200), no como texto."""
    formatos = {}
    for col in df.columns:
        if not pd.api.types.is_numeric_dtype(df[col]):
            continue
        if col.endswith("(m)"):
            formatos[col] = _formato_metros
        elif col.endswith("(min)"):
            formatos[col] = _formato_minutos
    return formatos


def _textos_para_buscar(df: pd.DataFrame) -> pd.DataFrame:
    """Cada celda como texto en minúsculas: el valor tal como se ve y el valor original.

    Así se encuentra '1.639' (como se ve), '-1639' (número) o '11,4' (minutos)."""
    formatos = _formatos(df)
    textos = {}
    for col in df.columns:
        crudo = df[col].astype(str).where(df[col].notna(), "")
        if col in formatos:
            visto = df[col].map(lambda v: "" if pd.isna(v) else formatos[col](v))
            crudo = visto + " " + crudo
        textos[col] = crudo.str.lower()
    return pd.DataFrame(textos, index=df.index)


def _negativo_en_rojo(valor) -> str:
    try:
        return "color: #C62828; font-weight: bold" if float(valor) < 0 else ""
    except (TypeError, ValueError):
        return ""


COLUMNAS_POR_FILA = 7

# Celdas vacías en blanco (si no, la tabla escribe "None"). Disponible en Streamlit reciente.
_SIN_NONE = ({"placeholder": ""}
             if "placeholder" in inspect.signature(st.dataframe).parameters else {})
SIN_NONE_EDITOR = ({"placeholder": ""}
                   if "placeholder" in inspect.signature(st.data_editor).parameters else {})


def _buscadores_por_columna(df: pd.DataFrame, clave: str) -> dict:
    """Un campo de texto por cada columna de la tabla. Devuelve {columna: texto}."""
    textos = {}
    with st.expander("🔎 Buscar por columna  ·  escribe en la columna que quieras filtrar"):
        columnas = list(df.columns)
        for inicio in range(0, len(columnas), COLUMNAS_POR_FILA):
            grupo = columnas[inicio:inicio + COLUMNAS_POR_FILA]
            for col_ui, (i, nombre) in zip(st.columns(COLUMNAS_POR_FILA),
                                           enumerate(grupo, start=inicio)):
                with col_ui:
                    textos[nombre] = st.text_input(
                        str(nombre), key=f"{clave}_col_{i}", placeholder="Buscar…")
        if any(t.strip() for t in textos.values()):
            st.caption("Se muestran las filas que cumplen con todo lo escrito.")
    return {c: t.strip().lower() for c, t in textos.items() if t and t.strip()}


def _filtrar(df: pd.DataFrame, clave: str, filtros: list[str], buscador: bool) -> pd.DataFrame:
    """Desplegables, buscador general y buscador por columna. Conserva el índice de `df`."""
    columnas = st.columns(len(filtros) + int(buscador))
    seleccion = {}
    for columna_ui, campo in zip(columnas, filtros):
        with columna_ui:
            seleccion[campo] = st.selectbox(
                campo, [TODOS] + opciones(df, campo), key=f"{clave}_{campo}"
            )
    texto = ""
    if buscador:
        with columnas[-1]:
            texto = st.text_input("🔍 Buscar en cualquier columna",
                                  key=f"{clave}_buscar", placeholder="Ej: SAO-001")
    por_columna = _buscadores_por_columna(df, clave)

    filtrado = aplicar_filtros(df, seleccion)
    if texto.strip() or por_columna:
        textos = _textos_para_buscar(filtrado)
        coincide = pd.Series(True, index=filtrado.index)
        if texto.strip():
            buscado = texto.strip().lower()
            coincide &= textos.apply(
                lambda c: c.str.contains(buscado, regex=False, na=False)).any(axis=1)
        for columna, buscado in por_columna.items():
            coincide &= textos[columna].str.contains(buscado, regex=False, na=False)
        filtrado = filtrado[coincide]
    return filtrado


def _con_estilo(df: pd.DataFrame, colorear: str | None):
    formatos = _formatos(df)
    if not (colorear or formatos):
        return df
    vista = df.style.format(formatos, na_rep="")
    if colorear:
        vista = vista.map(lambda v: ESTILO_VALIDACION.get(v, ""), subset=[colorear])
    if "Diferencia (m)" in df.columns:
        vista = vista.map(_negativo_en_rojo, subset=["Diferencia (m)"])
    return vista


def _pie_tabla(mostrados: int, total: int) -> None:
    st.caption(f"Mostrando {mostrados:,} de {total:,} registros · "
               "clic en el título de una columna para ordenarla".replace(",", "."))


# Alto de las tablas de resultados (píxeles)
ALTO_TABLA = 620


def tabla_filtrable(df: pd.DataFrame, clave: str, filtros: list[str],
                    buscador: bool = False, colorear: str | None = None,
                    alto: int = ALTO_TABLA) -> None:
    """Tabla con un desplegable por cada columna de `filtros`, buscador general opcional
    y un campo de búsqueda por cada columna."""
    filtrado = _filtrar(df, clave, filtros, buscador)
    st.dataframe(_con_estilo(filtrado, colorear), use_container_width=True, height=alto,
                 hide_index=True, **_SIN_NONE)
    _pie_tabla(len(filtrado), len(df))


COLUMNA_MARCA = "Reclamar"
COLUMNA_EN_CONSOLIDADO = "Consolidado"


def _ancho(pixeles: int, respaldo: str = "small"):
    """Ancho de columna en píxeles (Streamlit reciente) o 'small' en versiones anteriores."""
    try:
        version = tuple(int(x) for x in st.__version__.split(".")[:2])
    except ValueError:
        return respaldo
    return pixeles if version >= (1, 45) else respaldo


def tabla_seleccionable(df: pd.DataFrame, clave: str, filtros: list[str],
                        seleccion: set, incluidos: set, colorear: str | None = None,
                        alto: int | None = None) -> set:
    """Como `tabla_filtrable`, con una casilla "Reclamar" por fila.

    `seleccion`: posiciones (índice de `df`) marcadas. `incluidos`: posiciones que ya
    están en el consolidado. Devuelve la selección actualizada.
    """
    filtrado = _filtrar(df, clave, filtros, buscador=True)

    # Si cambian los filtros (u otras filas visibles) la tabla se arma de nuevo
    firma = hash(tuple(filtrado.index))
    version_clave, firma_clave = f"{clave}_version", f"{clave}_firma"
    if st.session_state.get(firma_clave) != firma:
        st.session_state[firma_clave] = firma
        st.session_state[version_clave] = st.session_state.get(version_clave, 0) + 1

    c_info, c_todos, c_limpiar = st.columns([3, 1.1, 1.1], vertical_alignment="center")
    with c_todos:
        if st.button("☑️ Marcar visibles", key=f"{clave}_todos", use_container_width=True,
                     help="Marca todos los casos que se ven en la tabla (según los filtros)."):
            seleccion = seleccion | set(filtrado.index)
            st.session_state[version_clave] = st.session_state.get(version_clave, 0) + 1
    with c_limpiar:
        if st.button("✖️ Limpiar selección", key=f"{clave}_limpiar", use_container_width=True,
                     disabled=not seleccion):
            seleccion = set()
            st.session_state[version_clave] = st.session_state.get(version_clave, 0) + 1

    # Las columnas de marcar van al final de la tabla
    base = filtrado.copy()
    base[COLUMNA_EN_CONSOLIDADO] = ["✔ Incluido" if i in incluidos else "" for i in base.index]
    base[COLUMNA_MARCA] = [i in seleccion for i in base.index]
    alto = alto or min(ALTO_TABLA, 40 + 35 * max(len(base), 1))
    editado = st.data_editor(
        _con_estilo(base, colorear), key=f"{clave}_editor_{st.session_state[version_clave]}",
        use_container_width=True, height=alto, hide_index=True,
        disabled=[c for c in base.columns if c != COLUMNA_MARCA], **SIN_NONE_EDITOR,
        column_config={
            COLUMNA_MARCA: st.column_config.CheckboxColumn(
                "✔ Reclamar", help="Marca los casos que vas a incluir en el consolidado "
                                   "de reclamación de la quincena.", width=_ancho(115)),
            COLUMNA_EN_CONSOLIDADO: st.column_config.TextColumn(
                "📑 Consolidado", help="Casos que ya están en el consolidado de la quincena.",
                width=_ancho(118)),
        },
    )
    marcados = set(editado.index[editado[COLUMNA_MARCA].astype(bool)])
    seleccion = (seleccion - set(filtrado.index)) | marcados
    with c_info:
        _html(f'<div class="seleccion-info"><b>{len(seleccion)}</b> caso(s) marcado(s) para '
              f'reclamar · {len(incluidos)} ya en el consolidado</div>')
    _pie_tabla(len(filtrado), len(df))
    return seleccion
