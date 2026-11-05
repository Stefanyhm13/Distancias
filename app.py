"""
Recuperación de Km · SAO
Punto de entrada de la aplicación:  streamlit run app.py

Al presionar "Analizar día" se detecta el tipo de día (HÁBIL, SÁBADO o DOMINGO/festivo)
con el calendario colombiano, se pide confirmarlo y se analiza con los parámetros de
ese tipo de día.

En la pestaña "Resumen REVISAR" se marcan los casos a reclamar y, debajo de la tabla,
se genera el consolidado de reclamación de la quincena (ui/consolidado.py).

Abajo de los resultados está el historial de días revisados (base de datos SQLite).
"""
import traceback

import streamlit as st

from src.analisis import analizar, fecha_del_informe
from src.calendario import NOMBRES_TIPO
from src.lectura import ErrorDeArchivo
from src.reporte_excel import generar_excel, nombre_archivo
from ui import componentes as ui
from ui import consolidado
from ui import historial
from ui import parametros as ventana_parametros
from ui import tipo_dia
from ui import traduccion

st.set_page_config(
    page_title="SAO · Recuperación de Km",
    page_icon="🚌",
    layout="wide",
    initial_sidebar_state="collapsed",
)
ui.cargar_estilos()
traduccion.instalar()
ui.encabezado()
ventana_parametros.inicializar()


def _mostrar_error(e: Exception) -> None:
    st.session_state.pop("resultado", None)
    if isinstance(e, ErrorDeArchivo):
        st.error(f"❌ {e}")
        return
    st.error(f"❌ Error inesperado durante el análisis: {e}")
    with st.expander("Detalle técnico"):
        st.code(traceback.format_exc())


def preguntar_tipo_de_dia(archivo_servicios) -> None:
    """Lee la fecha del informe y abre el aviso para confirmar el tipo de día."""
    try:
        with st.spinner("⏳ Leyendo la fecha del informe..."):
            fecha = fecha_del_informe(archivo_servicios)
    except Exception as e:
        _mostrar_error(e)
        return
    tipo_dia.preguntar(fecha)


def ejecutar_analisis(archivo_usos, archivo_servicios, tipo: str) -> None:
    """Corre el análisis con los parámetros del tipo de día y guarda el resultado."""
    try:
        with st.spinner(f"⏳ Realizando análisis (día {NOMBRES_TIPO[tipo]})..."):
            resultado = analizar(archivo_usos, archivo_servicios,
                                 ventana_parametros.activos(tipo), tipo)
            excel = generar_excel(resultado)
    except Exception as e:
        _mostrar_error(e)
        return

    consolidado.reiniciar_seleccion()
    st.session_state["resultado"] = {
        "analisis": resultado,
        "excel": excel,
        "nombre_usos": archivo_usos.name,
        "nombre_servicios": archivo_servicios.name,
    }
    # Se guarda en la base de datos; si el día ya existe se pregunta si se reemplaza
    historial.guardar_o_preguntar(st.session_state["resultado"])


def panel_archivos():
    with st.container(border=True):
        ui.titulo_seccion("⚙️ Parámetros de revisión")
        ventana_parametros.tarjeta()

    with st.container(border=True):
        ui.titulo_seccion("📁 Archivos")
        usos = ui.selector_archivo("Archivo de Usos", "Usos.xlsx", "usos",
                                   ["xlsx", "xls"], "📊")
        servicios = ui.selector_archivo("Archivo de Servicios", "PlantillaGestionServicios",
                                        "servicios", ["xlsx", "xls", "xlt"], "📋")

        listos = usos is not None and servicios is not None
        if not listos:
            st.info("⬆️ Carga los dos archivos para continuar")
        _, centro, _ = st.columns([0.3, 3, 0.3])
        with centro:
            pulsado = st.button("🔍 Analizar día", disabled=not listos,
                                use_container_width=True)

    with st.container(border=True):
        ui.titulo_seccion("📘 PSO · Horarios")
        consolidado.tarjeta_pso()

    return usos, servicios, pulsado and listos


def panel_resultados(sesion: dict) -> None:
    r = sesion["analisis"]
    ind = r.indicadores

    with st.container(border=True):
        ui.banner_exito(r.fecha, sesion["nombre_usos"], sesion["nombre_servicios"],
                        getattr(r, "tipo_dia", ""))
        historial.estado_guardado(sesion)

    if r.avisos:
        with st.expander(f"⚠️ Observaciones de los archivos ({len(r.avisos)})"):
            for aviso in r.avisos:
                st.markdown(f"- {aviso}")

    ui.fila_metricas([
        ("🚌", ind["vehiculos"], "Unidades", "blue"),
        ("🧭", f"{ind['viajes']:,}", "Registros SAE", ""),
        ("👥", f"{ind['total_usuarios']:,}", "Total usuarios día", "purple"),
        ("🛣️", f"{ind['total_km']:,.1f}", "Total km del día", "teal"),
    ])
    st.markdown("<br>", unsafe_allow_html=True)
    ui.fila_metricas([
        ("⚠️", ind["revisar"], "Registros con distancia 0", "red"),
        ("📉", ind["km_bajo"], "Registros con km bajo (equivalencia distancia media)", "orange"),
        ("🙋", f"{ind['usos_sin_viaje']:,}",
         f"Usos sin información en SAE · {ind['grupos_sin_viaje']:,} grupos", "red"),
    ])
    st.markdown("<br>", unsafe_allow_html=True)

    with st.container(border=True):
        _, centro, _ = st.columns([1, 2, 1])
        with centro:
            st.download_button(
                label="⬇️  Descargar informe Excel",
                data=sesion["excel"],
                file_name=nombre_archivo(r),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

    with st.container(border=True):
        tab_resumen, tab_viajes, tab_sin_viaje, tab_servicios = st.tabs([
            f"🔴 Resumen REVISAR ({ind['total_revisar']:,})",
            f"🧭 Registros SAE ({len(r.viajes):,})",
            f"🙋 Usos sin información en SAE ({len(r.grupos_sin_viaje):,} grupos)",
            f"🚌 Informe Servicios ({len(r.servicios):,})",
        ])
        filtros_viaje = ["Vehículo", "Línea", "Validación"]

        with tab_resumen:
            if r.resumen.empty:
                st.success("🎉 ¡No hay casos que requieran revisión!")
            else:
                consolidado.tabla_resumen(sesion, filtros_viaje)

        with tab_viajes:
            ui.tabla_filtrable(r.viajes, "viajes", filtros_viaje,
                               buscador=True, colorear="Validación")

        with tab_sin_viaje:
            if r.usos_sin_viaje.empty:
                st.success("🎉 Todos los usos coinciden con un viaje.")
            else:
                minutos = r.parametros.minutos_agrupar_usos
                vista = st.radio(
                    "Ver", ["Agrupados", "Uno por uno"], horizontal=True,
                    key="vista_sin_viaje", label_visibility="collapsed",
                    help=f"Agrupados: usos seguidos del mismo bus y ruta, a {minutos} min "
                         "o menos uno del otro y sin un viaje entre ellos.")
                if vista == "Agrupados":
                    st.caption(f"Usos seguidos del mismo bus y ruta, separados por {minutos} "
                               "min o menos y sin un viaje entre ellos.")
                    ui.tabla_filtrable(r.grupos_sin_viaje, "grupos_sin_viaje",
                                       ["Vehículo", "Línea"], buscador=True,
                                       colorear="Validación")
                else:
                    ui.tabla_filtrable(r.usos_sin_viaje, "sin_viaje", ["Vehículo", "Línea"],
                                       buscador=True, colorear="Validación")

        with tab_servicios:
            cols = r.columnas_servicios
            ui.tabla_filtrable(r.servicios, "servicios",
                               [cols["vehiculo"], cols["linea"]], buscador=True)


# ── Página ────────────────────────────────────────────────────────────────────
col_izquierda, col_derecha = st.columns([1, 3], gap="medium")

with col_izquierda:
    archivo_usos, archivo_servicios, analizar_ahora = panel_archivos()

with col_derecha:
    confirmado = tipo_dia.confirmado()          # el usuario acaba de confirmar el tipo de día
    if analizar_ahora:
        preguntar_tipo_de_dia(archivo_servicios)
    elif confirmado and archivo_usos is not None and archivo_servicios is not None:
        ejecutar_analisis(archivo_usos, archivo_servicios, confirmado["tipo"])

    if "resultado" in st.session_state:
        panel_resultados(st.session_state["resultado"])
    else:
        with st.container(border=True):
            ui.estado_vacio()

    with st.container(border=True):
        ui.titulo_seccion("🎨 Leyenda")
        if "resultado" in st.session_state:
            pct = st.session_state["resultado"]["analisis"].parametros.pct
        else:
            porcentajes = {p.pct for p in ventana_parametros.por_dia().values()}
            pct = porcentajes.pop() if len(porcentajes) == 1 else "% exigido del tipo de día"
        ui.leyenda(pct)

# ── Historial (parte de abajo de la página, a todo lo ancho) ─────────────────
historial.seccion()
