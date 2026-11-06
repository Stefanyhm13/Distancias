"""
Aviso "Tipo de día" que sale al presionar Analizar día.

Muestra el tipo detectado con el calendario colombiano (HÁBIL, SÁBADO o DOMINGO;
los festivos cuentan como DOMINGO) y deja confirmarlo o cambiarlo, por si hay un
festivo por decreto que el calendario aún no tiene.
"""
from datetime import date
from html import escape

import streamlit as st

from src.calendario import NOMBRES_TIPO, TIPOS_DIA, fecha_larga, fuente_calendario, tipo_de_dia

CLAVE_CONFIRMADO = "_analizar_como"        # tipo elegido: el análisis corre en la recarga
CLAVE_CAMBIANDO = "_tipo_dia_cambiando"    # True mientras se elige otro tipo
CLAVE_ELEGIDO = "_tipo_dia_elegido"        # valor del selector al cambiar

ICONOS = {"HABIL": "🏢", "SABADO": "🛍️", "DOMINGO": "⛪"}


def _html(contenido: str) -> None:
    st.markdown(contenido, unsafe_allow_html=True)


def _empezar_cambio() -> None:
    st.session_state[CLAVE_CAMBIANDO] = True


def _volver() -> None:
    st.session_state[CLAVE_CAMBIANDO] = False


def _confirmar(tipo: str, fecha: date) -> None:
    st.session_state[CLAVE_CONFIRMADO] = {"tipo": tipo, "fecha": fecha}
    st.session_state[CLAVE_CAMBIANDO] = False
    st.rerun()


def _contenido(fecha: date) -> None:
    detectado, motivo = tipo_de_dia(fecha)
    nombre = NOMBRES_TIPO[detectado]

    # Debajo de la fecha solo se aclara cuando es festivo (con su nombre)
    detalle = (f'<div class="tipo-dia-motivo">{escape(motivo)}</div>'
               if motivo.startswith("Festivo") else "")
    # En una sola línea: si queda una línea vacía, Streamlit muestra el HTML como código
    _html('<div class="tipo-dia-aviso">'
          f'<div class="tipo-dia-chip tipo-{detectado.lower()}">{ICONOS[detectado]} {nombre}</div>'
          f'<div class="tipo-dia-fecha">📅 {escape(fecha_larga(fecha))}</div>'
          f'{detalle}'
          '<div class="tipo-dia-pregunta">¿Desea confirmar o cambiar?</div>'
          '</div>')

    if not st.session_state.get(CLAVE_CAMBIANDO):
        c_cambiar, c_confirmar = st.columns(2)
        with c_cambiar:
            st.button("✏️ Cambiar", key="tipo_dia_cambiar", on_click=_empezar_cambio,
                      use_container_width=True)
        with c_confirmar:
            if st.button("✅ Confirmar", key="tipo_dia_confirmar", type="primary",
                         use_container_width=True):
                _confirmar(detectado, fecha)
        _html(f'<div class="tipo-dia-nota">Detectado con el {escape(fuente_calendario())}. '
              'Los festivos se analizan como DOMINGO.</div>')
        return

    st.session_state.setdefault(CLAVE_ELEGIDO, detectado)
    elegido = st.radio("¿Cómo se debe analizar este día?", TIPOS_DIA, key=CLAVE_ELEGIDO,
                       format_func=lambda t: f"{ICONOS[t]} {NOMBRES_TIPO[t]}",
                       horizontal=True)
    c_volver, c_analizar = st.columns(2)
    with c_volver:
        st.button("↩️ Volver", key="tipo_dia_volver", on_click=_volver,
                  use_container_width=True)
    with c_analizar:
        if st.button(f"✅ Analizar como {NOMBRES_TIPO[elegido]}", key="tipo_dia_analizar",
                     type="primary", use_container_width=True):
            _confirmar(elegido, fecha)


def _crear_ventana():
    dialogo = getattr(st, "dialog", None) or getattr(st, "experimental_dialog", None)
    if dialogo is None:
        return None
    return dialogo("Tipo de día", width="small")(_contenido)


_ventana = _crear_ventana()


def preguntar(fecha: date) -> None:
    """Abre el aviso. Al confirmar queda el tipo en `confirmado()` y la app se recarga."""
    st.session_state[CLAVE_CAMBIANDO] = False
    st.session_state.pop(CLAVE_ELEGIDO, None)
    if _ventana:
        _ventana(fecha)
    else:                                   # Streamlit muy antiguo: se usa lo detectado
        st.session_state[CLAVE_CONFIRMADO] = {"tipo": tipo_de_dia(fecha)[0], "fecha": fecha}
        st.rerun()


def confirmado() -> dict | None:
    """{"tipo": ..., "fecha": ...} si el usuario acaba de confirmar; se usa una sola vez."""
    return st.session_state.pop(CLAVE_CONFIRMADO, None)
