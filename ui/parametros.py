"""Ventana "Modificar parámetros": una pestaña por tipo de día (HÁBIL, SÁBADO, DOMINGO).

Cada pestaña tiene su propio cumplimiento exigido, cuadro de distancias por ruta y
minutos para agrupar usos sin viaje. Al analizar se usan los del tipo de día detectado.
"""
import copy

import pandas as pd
import streamlit as st

from src import parametros as modelo
from src.calendario import HABIL, NOMBRES_TIPO, TIPOS_DIA
from src.normalizacion import normalizar_linea

CLAVE_ACTIVOS = "parametros_por_dia"      # {tipo: parámetros} con los que se analiza
CLAVE_BORRADOR = "_parametros_borrador"   # copia que se edita en la ventana
CLAVE_VERSION = "_parametros_version"     # cambia para refrescar los cuadros
CLAVE_ERRORES = "_parametros_errores"

ICONOS_TIPO = {"HABIL": "🏢", "SABADO": "🛍️", "DOMINGO": "⛪"}


def _clave_porcentaje(tipo: str) -> str:
    return f"_porcentaje_exigido_{tipo}"   # valor del campo, en % (95.0)


def _clave_minutos(tipo: str) -> str:
    return f"_minutos_agrupar_{tipo}"


def _columnas_editor(pct: str) -> dict:
    """Configuración de las columnas del cuadro; los títulos llevan el % exigido vigente."""
    return {
        "linea": st.column_config.TextColumn(
            "✏️ Línea", help="Código de la ruta", required=True, width="small"),
        "distancia_ciclo_m": st.column_config.NumberColumn(
            "✏️ Distancia de ciclo (m)", min_value=0, step=1, format="%d"),
        "tiempo_ciclo_min": st.column_config.NumberColumn(
            "✏️ Tiempo de ciclo (min)", min_value=0, format="%.2f"),
        "distancia_x_min": st.column_config.NumberColumn(
            "Distancia x min (m)", format="%.2f",
            help="Distancia de ciclo ÷ Tiempo de ciclo"),
        "distancia_95": st.column_config.NumberColumn(
            f"Distancia al {pct} x min (m)", format="%.2f",
            help=f"Distancia x min × {pct}. Cada viaje debe recorrer al menos "
                 "este valor por cada minuto que dure."),
    }


EDITABLES = list(modelo.COLUMNAS_RUTAS)
CALCULADAS = list(modelo.COLUMNAS_CALCULADAS)


# ── Estado ────────────────────────────────────────────────────────────────────

def inicializar() -> None:
    """Carga los parámetros guardados la primera vez que se abre la app."""
    if CLAVE_ACTIVOS not in st.session_state:
        por_dia, aviso = modelo.cargar_por_dia()
        st.session_state[CLAVE_ACTIVOS] = por_dia
        if aviso:
            st.toast(f"⚠️ {aviso}")


def por_dia() -> dict[str, modelo.Parametros]:
    return st.session_state[CLAVE_ACTIVOS]


def activos(tipo: str = HABIL) -> modelo.Parametros:
    """Parámetros vigentes de un tipo de día."""
    return por_dia()[tipo]


def _borrador(tipo: str) -> modelo.Parametros:
    return st.session_state[CLAVE_BORRADOR][tipo]


def _refrescar() -> None:
    st.session_state[CLAVE_VERSION] = st.session_state.get(CLAVE_VERSION, 0) + 1


def _clave_editor(tipo: str) -> str:
    return f"_editor_rutas_{tipo}_{st.session_state.get(CLAVE_VERSION, 0)}"


def _cargar_campos(tipo: str, parametros: modelo.Parametros) -> None:
    st.session_state[_clave_porcentaje(tipo)] = parametros.porcentaje_exigido * 100
    st.session_state[_clave_minutos(tipo)] = parametros.minutos_agrupar_usos


# ── Callbacks ─────────────────────────────────────────────────────────────────

def _al_editar_cuadro(tipo: str, clave: str) -> None:
    """Aplica al borrador lo editado en el cuadro y recalcula las columnas."""
    cambios = st.session_state.get(clave, {})
    rutas = _borrador(tipo).rutas.copy()

    for posicion, valores in cambios.get("edited_rows", {}).items():
        for columna, valor in valores.items():
            if columna in EDITABLES:
                rutas.at[rutas.index[int(posicion)], columna] = valor
    eliminadas = [rutas.index[int(p)] for p in cambios.get("deleted_rows", [])]
    rutas = rutas.drop(index=eliminadas)
    nuevas = [{c: v for c, v in fila.items() if c in EDITABLES}
              for fila in cambios.get("added_rows", [])]
    if nuevas:
        rutas = pd.concat([rutas, pd.DataFrame(nuevas, columns=EDITABLES)], ignore_index=True)

    rutas["linea"] = rutas["linea"].map(normalizar_linea)
    for columna in ("distancia_ciclo_m", "tiempo_ciclo_min"):
        rutas[columna] = pd.to_numeric(rutas[columna], errors="coerce")
    _borrador(tipo).rutas = rutas.reset_index(drop=True)
    st.session_state.pop(CLAVE_ERRORES, None)
    _refrescar()


def _al_cambiar_minutos_agrupar(tipo: str) -> None:
    _borrador(tipo).minutos_agrupar_usos = int(st.session_state[_clave_minutos(tipo)])


def _al_cambiar_porcentaje(tipo: str) -> None:
    _borrador(tipo).porcentaje_exigido = float(st.session_state[_clave_porcentaje(tipo)]) / 100
    st.session_state.pop(CLAVE_ERRORES, None)
    _refrescar()                                   # recalcula las columnas del cuadro


def _restaurar(tipo: str) -> None:
    st.session_state[CLAVE_BORRADOR][tipo] = modelo.parametros_iniciales()
    _cargar_campos(tipo, _borrador(tipo))
    st.session_state.pop(CLAVE_ERRORES, None)
    _refrescar()


def _copiar_a_todos(tipo: str) -> None:
    """Copia los parámetros de esta pestaña a los otros dos tipos de día."""
    for otro in TIPOS_DIA:
        if otro != tipo:
            st.session_state[CLAVE_BORRADOR][otro] = copy.deepcopy(_borrador(tipo))
            _cargar_campos(otro, _borrador(otro))
    st.session_state.pop(CLAVE_ERRORES, None)
    _refrescar()


# ── Ventana ───────────────────────────────────────────────────────────────────

def _pestana(tipo: str) -> None:
    """Contenido de la pestaña de un tipo de día."""
    borrador = _borrador(tipo)
    nombre = NOMBRES_TIPO[tipo]

    st.markdown(f'<div class="param-ayuda">Estos parámetros se usan cuando el día analizado '
                f'es <b>{nombre}</b>'
                + (" (domingos y festivos)" if tipo == "DOMINGO" else "")
                + ".</div>", unsafe_allow_html=True)

    st.markdown('<div class="param-seccion">📏 Cumplimiento exigido</div>',
                unsafe_allow_html=True)
    col_pct, col_pct_texto = st.columns([1, 3], vertical_alignment="center")
    with col_pct:
        st.number_input(
            "Cumplimiento exigido (%)", key=_clave_porcentaje(tipo),
            min_value=modelo.PORCENTAJE_MIN * 100, max_value=modelo.PORCENTAJE_MAX * 100,
            step=1.0, format="%.1f", on_change=_al_cambiar_porcentaje, args=(tipo,),
            label_visibility="collapsed")
    with col_pct_texto:
        st.markdown(
            '<div class="param-ayuda">% de la distancia por minuto de cada ruta que se exige. '
            'Ejemplo: con 95, una ruta de 200 m por minuto debe hacer al menos 190 m por '
            'minuto.</div>', unsafe_allow_html=True)

    st.markdown('<div class="param-seccion">🛣️ Distancias por ruta</div>',
                unsafe_allow_html=True)
    st.markdown(
        '<div class="param-ayuda">Edita las columnas marcadas con ✏️; las demás se calculan '
        'solas. Usa la última fila para agregar una ruta, o selecciónala y bórrala para '
        'quitarla.<br>Cada viaje debe recorrer al menos: <b>minutos del viaje × '
        f'distancia al {borrador.pct} x min</b> de su ruta.</div>', unsafe_allow_html=True)

    clave = _clave_editor(tipo)
    st.data_editor(
        borrador.tabla_calculada()[EDITABLES + CALCULADAS],
        key=clave, column_config=_columnas_editor(borrador.pct), disabled=CALCULADAS,
        num_rows="dynamic", hide_index=True, use_container_width=True, height=380,
        on_change=_al_editar_cuadro, args=(tipo, clave),
    )

    st.markdown('<div class="param-seccion">🙋 Usos sin viaje</div>', unsafe_allow_html=True)
    col_num, col_texto = st.columns([1, 3], vertical_alignment="center")
    with col_num:
        st.number_input(
            "Minutos para agrupar usos", key=_clave_minutos(tipo),
            min_value=modelo.MINUTOS_AGRUPAR_MIN, max_value=modelo.MINUTOS_AGRUPAR_MAX,
            step=5, on_change=_al_cambiar_minutos_agrupar, args=(tipo,),
            label_visibility="collapsed")
    with col_texto:
        st.markdown(
            '<div class="param-ayuda">minutos máximos entre dos usos sin viaje para agruparlos '
            '(mismo bus y ruta, sin un viaje entre ellos).</div>', unsafe_allow_html=True)

    c_restaurar, c_copiar, _ = st.columns([1.3, 1.6, 1])
    with c_restaurar:
        st.button("↺ Valores iniciales", key=f"_restaurar_{tipo}", on_click=_restaurar,
                  args=(tipo,), use_container_width=True,
                  help=f"Vuelve a los valores iniciales solo en la pestaña {nombre}")
    with c_copiar:
        st.button(f"📋 Copiar {nombre} a los otros días", key=f"_copiar_{tipo}",
                  on_click=_copiar_a_todos, args=(tipo,), use_container_width=True,
                  help="Deja los otros dos tipos de día iguales a esta pestaña")


def _contenido_ventana() -> None:
    pestanas = st.tabs([f"{ICONOS_TIPO[t]} {NOMBRES_TIPO[t]}" for t in TIPOS_DIA])
    for pestana, tipo in zip(pestanas, TIPOS_DIA):
        with pestana:
            _pestana(tipo)

    for error in st.session_state.get(CLAVE_ERRORES, []):
        st.error(error)

    _, c_cancelar, c_guardar = st.columns([2, 1, 1.2])
    with c_cancelar:
        if st.button("Cancelar", use_container_width=True):
            st.rerun()
    with c_guardar:
        if st.button("💾 Guardar y aplicar", type="primary", use_container_width=True):
            _guardar()


def _guardar() -> None:
    finales, errores = {}, []
    for tipo in TIPOS_DIA:
        b = _borrador(tipo)
        final = modelo.Parametros(modelo.limpiar_rutas(b.rutas), b.minutos_agrupar_usos,
                                  b.porcentaje_exigido)
        errores += [f"{NOMBRES_TIPO[tipo]}: {e}" for e in final.errores()]
        finales[tipo] = final
    if errores:
        st.session_state[CLAVE_ERRORES] = errores
        st.rerun(scope="fragment")
        return
    modelo.guardar_por_dia(finales)
    st.session_state[CLAVE_ACTIVOS] = finales
    st.session_state.pop("resultado", None)          # el análisis anterior ya no aplica
    st.session_state["_parametros_guardados"] = True
    st.rerun()


def _crear_ventana():
    """st.dialog en versiones recientes de Streamlit; experimental_dialog en anteriores."""
    dialogo = getattr(st, "dialog", None) or getattr(st, "experimental_dialog", None)
    if dialogo is None:
        return None
    return dialogo("⚙️ Modificar parámetros", width="large")(_contenido_ventana)


_ventana = _crear_ventana()


def abrir_ventana() -> None:
    st.session_state[CLAVE_BORRADOR] = copy.deepcopy(por_dia())
    for tipo in TIPOS_DIA:
        _cargar_campos(tipo, activos(tipo))
    st.session_state.pop(CLAVE_ERRORES, None)
    _refrescar()
    if _ventana:
        _ventana()
    else:
        st.error("Esta versión de Streamlit no tiene ventanas emergentes. "
                 "Actualízala con: python -m pip install -U streamlit")


# ── Tarjeta del panel izquierdo ───────────────────────────────────────────────

def _resumen(valores: dict) -> str:
    """'95%' si los tres tipos son iguales; si no 'Hábil 95% · Sábado 90% · Domingo 85%'."""
    if len(set(valores.values())) == 1:
        return f"<b>{next(iter(valores.values()))}</b>"
    return " · ".join(f"{NOMBRES_TIPO[t].capitalize()} <b>{v}</b>" for t, v in valores.items())


def tarjeta() -> None:
    """Resumen de los parámetros vigentes y botón para modificarlos."""
    todos = por_dia()
    rutas = _resumen({t: len(p.distancia_95_por_linea()) for t, p in todos.items()})
    pct = _resumen({t: p.pct for t, p in todos.items()})
    minutos = _resumen({t: f"{p.minutos_agrupar_usos} min" for t, p in todos.items()})
    st.markdown(
        f'<div class="param-resumen">'
        f'<span>📅 Parámetros por tipo de día: <b>Hábil · Sábado · Domingo</b></span>'
        f'<span>🛣️ Rutas con distancia: {rutas}</span>'
        f'<span>📏 Exigencia: {pct} de la distancia por minuto</span>'
        f'<span>🙋 Usos sin viaje agrupados cada {minutos}</span></div>',
        unsafe_allow_html=True)
    _, centro, _ = st.columns([0.5, 3, 0.5])
    with centro:
        if st.button("⚙️ Modificar parámetros", key="abrir_parametros",
                     use_container_width=True):
            abrir_ventana()
    if st.session_state.pop("_parametros_guardados", False):
        st.toast("✅ Parámetros guardados. Vuelve a presionar Analizar día.")
