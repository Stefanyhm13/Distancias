"""
Sección "Historial de días revisados" (parte de abajo de la página).

Consulta lo guardado en la base de datos por año, mes y día; muestra indicadores,
días destacados y gráficos; y permite ver el detalle y descargar el Excel de un día.

Este archivo es igual en la versión por viajes y en la versión por franjas.
"""

from __future__ import annotations
from html import escape

import altair as alt
import pandas as pd
import streamlit as st

from config import Validacion
from src import historial as bd
from src.calendario import NOMBRES_TIPO
from ui import ilustraciones as il

TODOS = "Todos"
MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto",
         "Septiembre", "Octubre", "Noviembre", "Diciembre"]
DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

# Colores: verde = km recorridos, naranja = km por recuperar; los tipos de caso usan
# los mismos colores de la leyenda de la app.
COLOR_RECORRIDO = "#1B7A3E"
COLOR_RECUPERAR = "#E8710A"
COLORES_CASOS = {
    "Distancia 0": "#E53935",
    "Equivalencia": "#FF8C00",
    "Usos sin información en SAE": "#8E24AA",
}
FUENTE = "Source Sans Pro, sans-serif"


def _html(contenido: str) -> None:
    st.markdown(contenido, unsafe_allow_html=True)


def _num(valor, decimales: int = 0) -> str:
    """Número con punto de miles y coma decimal (formato colombiano)."""
    texto = f"{valor:,.{decimales}f}"
    return texto.replace(",", "_").replace(".", ",").replace("_", ".")


def _fecha_larga(fecha) -> str:
    f = pd.Timestamp(fecha)
    return f"{DIAS_SEMANA[f.weekday()]} {f.day} de {MESES[f.month - 1].lower()} de {f.year}"


def _fecha_corta(fecha) -> str:
    return pd.Timestamp(fecha).strftime("%d/%m/%Y")


# ── Encabezado y estados ──────────────────────────────────────────────────────

def _encabezado_seccion() -> None:
    """Separador tipo mapa de ruta: línea con paradas y un bus que la recorre."""
    paradas = "".join(f'<span class="parada" style="left:{p}%"></span>'
                      for p in (0, 20, 40, 60, 80, 100))
    _html(f"""
    <div class="hist-sep">
        <div class="hist-sep-linea">
            {paradas}
            <img class="hist-sep-bus" src="{il.uri(il.bus_alimentador())}" alt="">
        </div>
        <div class="hist-sep-cuerpo">
            <div class="hist-sep-icono">📚</div>
            <div class="hist-sep-texto">
                <h2>Historial de días revisados</h2>
                <p>Consulta los días guardados, compara los km recorridos y los km por
                   recuperar, y descarga el informe de cualquier día.</p>
            </div>
        </div>
    </div>""")


def _vacio(texto: str) -> None:
    _html(f"""
    <div class="empty-state">
        <img src="{il.uri(il.operadores())}" class="empty-ilustracion" alt="Operadores SAO">
        <p>{texto}</p>
    </div>""")


# ── Filtros ───────────────────────────────────────────────────────────────────

def _filtros(dias: pd.DataFrame) -> tuple[pd.DataFrame, str, str]:
    """Año / Mes / Día / Agrupar por. Devuelve los días filtrados, el período y un título."""
    c_anio, c_mes, c_dia, c_grupo = st.columns([1, 1, 1, 1.4])
    with c_anio:
        anios = sorted(dias["anio"].unique(), reverse=True)
        anio = st.selectbox("📅 Año", [TODOS] + [int(a) for a in anios], key="hist_anio")
    filtrado = dias if anio == TODOS else dias[dias["anio"] == anio]

    with c_mes:
        meses = sorted(filtrado["mes"].unique())
        mes = st.selectbox("🗓️ Mes", [TODOS] + [MESES[m - 1] for m in meses], key="hist_mes")
    if mes != TODOS:
        filtrado = filtrado[filtrado["mes"] == MESES.index(mes) + 1]

    with c_dia:
        dias_mes = sorted(filtrado["dia"].unique())
        dia = st.selectbox("📆 Día", [TODOS] + [int(d) for d in dias_mes], key="hist_dia",
                           disabled=mes == TODOS,
                           help="Elige primero un mes para consultar un día puntual.")
    if mes != TODOS and dia != TODOS:
        filtrado = filtrado[filtrado["dia"] == dia]

    # Período sugerido según lo que se filtró
    if mes != TODOS:
        sugerido = "Día"
    elif filtrado["fecha"].dt.to_period("M").nunique() > 1:
        sugerido = "Mes"
    else:
        sugerido = "Día"
    opciones = ["Día", "Mes", "Año"]
    with c_grupo:
        periodo = st.radio("📊 Ver gráficos por", opciones, index=opciones.index(sugerido),
                           horizontal=True, key=f"hist_periodo_{sugerido}")

    partes = [p for p in (dia if dia != TODOS else None, mes if mes != TODOS else None,
                          anio if anio != TODOS else None) if p is not None]
    titulo = " de ".join(str(p) for p in partes) if partes else "Todos los días guardados"
    return filtrado, periodo, titulo


# ── Indicadores ───────────────────────────────────────────────────────────────

def _tarjeta(icono: str, valor: str, etiqueta: str, color: str = "") -> str:
    return f"""
    <div class="metric-card {color}">
        <span class="metric-icon">{icono}</span>
        <div class="metric-number {color}">{valor}</div>
        <div class="metric-label">{etiqueta}</div>
    </div>"""


def _indicadores(dias: pd.DataFrame) -> None:
    n = len(dias)
    tarjetas = [
        ("🗂️", _num(n), "Días revisados", "blue"),
        ("🛣️", _num(dias["km_recorridos"].sum(), 1), "Km recorridos", "teal"),
        ("🎯", _num(dias["km_por_recuperar"].sum(), 1), "Km por recuperar", "orange"),
        ("⚠️", _num(dias["casos_revisar"].sum()), "Casos a revisar", "red"),
        ("📈", _num(dias["km_por_recuperar"].mean(), 1), "Km por recuperar / día", ""),
    ]
    for col, t in zip(st.columns(len(tarjetas)), tarjetas):
        with col:
            _html(_tarjeta(*t))


def _destacado(icono: str, titulo: str, fecha, valor: str, clase: str) -> str:
    return f"""
    <div class="destacado {clase}">
        <div class="destacado-icono">{icono}</div>
        <div>
            <div class="destacado-titulo">{titulo}</div>
            <div class="destacado-fecha">{_fecha_larga(fecha)}</div>
            <div class="destacado-valor">{valor}</div>
        </div>
    </div>"""


def _destacados(dias: pd.DataFrame) -> None:
    if len(dias) < 2:
        return
    mas_perdido = dias.loc[dias["km_por_recuperar"].idxmax()]
    menos_perdido = dias.loc[dias["km_por_recuperar"].idxmin()]
    mas_km = dias.loc[dias["km_recorridos"].idxmax()]
    menos_km = dias.loc[dias["km_recorridos"].idxmin()]
    piezas = [
        ("📉", "Día con más km por recuperar", mas_perdido["fecha"],
         f"{_num(mas_perdido['km_por_recuperar'], 1)} km", "malo"),
        ("✅", "Día con menos km por recuperar", menos_perdido["fecha"],
         f"{_num(menos_perdido['km_por_recuperar'], 1)} km", "bueno"),
        ("🏆", "Día con más km recorridos", mas_km["fecha"],
         f"{_num(mas_km['km_recorridos'], 1)} km", "bueno"),
        ("🐢", "Día con menos km recorridos", menos_km["fecha"],
         f"{_num(menos_km['km_recorridos'], 1)} km", "neutro"),
    ]
    for col, p in zip(st.columns(len(piezas)), piezas):
        with col:
            _html(_destacado(*p))


# ── Gráficos ──────────────────────────────────────────────────────────────────

def _estilo(grafico: alt.Chart, alto: int = 280) -> alt.Chart:
    if grafico.height is alt.Undefined:
        grafico = grafico.properties(height=alto)
    return (grafico
            .configure(font=FUENTE, background="transparent")
            .configure_view(strokeWidth=0)
            .configure_axis(labelColor="#555", titleColor="#555", gridColor="#ECEFEC",
                            domainColor="#CFD8D3", tickColor="#CFD8D3", labelFontSize=11,
                            titleFontSize=11, titleFontWeight=600)
            .configure_legend(labelColor="#444", titleColor="#444", orient="top",
                              labelFontSize=11, titleFontSize=11))


def _por_periodo(dias: pd.DataFrame, periodo: str) -> pd.DataFrame:
    tabla = dias.copy()
    if periodo == "Día":
        tabla["periodo"] = tabla["fecha"].dt.strftime("%d/%m/%Y")
        tabla["orden"] = tabla["fecha"]
    elif periodo == "Mes":
        tabla["periodo"] = tabla["fecha"].dt.month.map(lambda m: MESES[m - 1][:3]) + \
            " " + tabla["fecha"].dt.year.astype(str)
        tabla["orden"] = tabla["fecha"].dt.to_period("M").dt.start_time
    else:
        tabla["periodo"] = tabla["fecha"].dt.year.astype(str)
        tabla["orden"] = tabla["fecha"].dt.to_period("Y").dt.start_time
    return (tabla.groupby(["orden", "periodo"], as_index=False)
                 .agg(km_recorridos=("km_recorridos", "sum"),
                      km_por_recuperar=("km_por_recuperar", "sum"),
                      sin_km=("sin_km", "sum"), km_bajo=("km_bajo", "sum"),
                      usos_sin_viaje=("usos_sin_viaje", "sum"),
                      casos=("casos_revisar", "sum"), dias=("fecha", "size"))
                 .sort_values("orden"))


EJE_NUMERO = "replace(format(datum.value, ',.0f'), regexp(',', 'g'), '.')"


def _eje_y(titulo: str) -> alt.Axis:
    return alt.Axis(title=titulo, labelExpr=EJE_NUMERO)


def _barras(tabla: pd.DataFrame, x: str, y: str, color: str, titulo_y: str,
            orden_x=None, horizontal: bool = False, extra_tooltip=None) -> alt.Chart:
    tabla = tabla.assign(_valor=tabla[y].map(lambda v: _num(v, 1)))
    tooltip = [alt.Tooltip(f"{x}:N", title=" "), alt.Tooltip("_valor:N", title=titulo_y)]
    tooltip += extra_tooltip or []
    if horizontal:
        enc = dict(y=alt.Y(f"{x}:N", sort="-x", title=None,
                           axis=alt.Axis(labelOverlap=False, labelLimit=120)),
                   x=alt.X(f"{y}:Q", axis=_eje_y(titulo_y)))
        marca = alt.Chart(tabla).mark_bar(color=color, cornerRadiusEnd=4, height={"band": 0.7})
    else:
        enc = dict(x=alt.X(f"{x}:N", sort=orden_x, title=None,
                           axis=alt.Axis(labelAngle=-40 if len(tabla) > 8 else 0)),
                   y=alt.Y(f"{y}:Q", axis=_eje_y(titulo_y)))
        marca = alt.Chart(tabla).mark_bar(color=color, cornerRadiusEnd=4, width={"band": 0.7})
    grafico = marca.encode(**enc, tooltip=tooltip)
    if horizontal:
        grafico = grafico.properties(height=max(280, 24 * len(tabla)))
    return grafico


def _tarjeta_grafico(titulo: str, subtitulo: str, grafico: alt.Chart | None,
                     vacio: str = "Sin datos para mostrar") -> None:
    with st.container(border=True):
        _html(f'<div class="chart-title">{titulo}</div><div class="chart-sub">{subtitulo}</div>')
        if grafico is None:
            st.caption(vacio)
        else:
            st.altair_chart(_estilo(grafico), use_container_width=True)


def _graficos(dias: pd.DataFrame, detalle: pd.DataFrame, periodo: str) -> None:
    serie = _por_periodo(dias, periodo)
    orden = list(serie["periodo"])
    etiqueta = {"Día": "día", "Mes": "mes", "Año": "año"}[periodo]
    dias_tt = [alt.Tooltip("dias:Q", title="Días revisados")]

    c1, c2 = st.columns(2)
    with c1:
        _tarjeta_grafico(
            f"🎯 Km por recuperar por {etiqueta}",
            "Km que les faltaron a los casos Distancia 0 y Equivalencia para llegar al mínimo",
            _barras(serie, "periodo", "km_por_recuperar", COLOR_RECUPERAR, "Km por recuperar",
                    orden, extra_tooltip=dias_tt))
    with c2:
        _tarjeta_grafico(
            f"🛣️ Km recorridos por {etiqueta}",
            "Distancia total reportada en el informe de servicios",
            _barras(serie, "periodo", "km_recorridos", COLOR_RECORRIDO, "Km recorridos",
                    orden, extra_tooltip=dias_tt))

    c3, c4 = st.columns(2)
    con_km = detalle[detalle["km_por_recuperar"] > 0]
    with c3:
        por_ruta = None
        if not con_km.empty:
            rutas = (con_km.assign(linea=con_km["linea"].replace("", "Sin ruta"))
                           .groupby("linea", as_index=False)
                           .agg(km=("km_por_recuperar", "sum"), casos=("fecha", "size"))
                           .nlargest(15, "km"))
            por_ruta = _barras(rutas, "linea", "km", COLOR_RECUPERAR, "Km por recuperar",
                               horizontal=True,
                               extra_tooltip=[alt.Tooltip("casos:Q", title="Casos")])
        _tarjeta_grafico("🗺️ Rutas con más km por recuperar", "Las 15 rutas con más km faltantes",
                         por_ruta, "No hay km por recuperar en este período 🎉")
    with c4:
        por_bus = None
        if not con_km.empty:
            buses = (con_km.groupby("vehiculo", as_index=False)
                           .agg(km=("km_por_recuperar", "sum"), casos=("fecha", "size"))
                           .nlargest(10, "km"))
            por_bus = _barras(buses, "vehiculo", "km", COLOR_RECUPERAR, "Km por recuperar",
                              horizontal=True,
                              extra_tooltip=[alt.Tooltip("casos:Q", title="Casos")])
        _tarjeta_grafico("🚌 Unidades con más km por recuperar",
                         "Las 10 unidades con más km faltantes", por_bus,
                         "No hay km por recuperar en este período 🎉")

    c5, c6 = st.columns(2)
    with c5:
        casos = serie.melt(id_vars=["orden", "periodo"],
                           value_vars=["sin_km", "km_bajo", "usos_sin_viaje"],
                           var_name="tipo", value_name="cantidad")
        casos["tipo"] = casos["tipo"].map({"sin_km": "Distancia 0", "km_bajo": "Equivalencia",
                                           "usos_sin_viaje": "Usos sin información en SAE"})
        if casos.loc[casos["tipo"] == "Usos sin información en SAE", "cantidad"].sum() == 0:
            casos = casos[casos["tipo"] != "Usos sin información en SAE"]
        tipos = [t for t in COLORES_CASOS if t in set(casos["tipo"])]
        grafico = (alt.Chart(casos).mark_bar(width={"band": 0.7}, stroke="#FFFFFF",
                                             strokeWidth=1)
                   .encode(x=alt.X("periodo:N", sort=orden, title=None,
                                   axis=alt.Axis(labelAngle=-40 if len(serie) > 8 else 0)),
                           y=alt.Y("cantidad:Q", stack="zero", axis=_eje_y("Casos")),
                           color=alt.Color("tipo:N", title=None,
                                           scale=alt.Scale(domain=tipos,
                                                           range=[COLORES_CASOS[t] for t in tipos])),
                           order=alt.Order("tipo:N"),
                           tooltip=[alt.Tooltip("periodo:N", title=" "),
                                    alt.Tooltip("tipo:N", title="Tipo"),
                                    alt.Tooltip("cantidad:Q", title="Casos", format=",")]))
        _tarjeta_grafico(f"⚠️ Casos a revisar por {etiqueta}",
                         "Cuántos casos de cada tipo se encontraron", grafico)
    with c6:
        por_hora = None
        if not con_km.empty:
            horas = con_km.assign(hora_n=pd.to_numeric(con_km["hora"].str[:2], errors="coerce"))
            horas = (horas.dropna(subset=["hora_n"])
                          .groupby("hora_n", as_index=False)
                          .agg(km=("km_por_recuperar", "sum"), casos=("fecha", "size")))
            horas["hora"] = horas["hora_n"].astype(int).map(lambda h: f"{h:02d}:00")
            por_hora = _barras(horas, "hora", "km", COLOR_RECUPERAR, "Km por recuperar",
                               list(horas["hora"]),
                               extra_tooltip=[alt.Tooltip("casos:Q", title="Casos")])
        _tarjeta_grafico("🕐 ¿A qué hora se pierden más km?",
                         "Km por recuperar según la hora de inicio del viaje o franja", por_hora,
                         "No hay km por recuperar en este período 🎉")

    if len(dias) >= 7:
        semana = dias.assign(dia_semana=dias["fecha"].dt.weekday)
        semana = (semana.groupby("dia_semana", as_index=False)
                        .agg(km=("km_por_recuperar", "mean"), dias=("fecha", "size")))
        semana["nombre"] = semana["dia_semana"].map(lambda d: DIAS_SEMANA[d])
        _tarjeta_grafico("📅 Promedio de km por recuperar según el día de la semana",
                         "¿Qué día de la semana suele quedar más km por recuperar?",
                         _barras(semana, "nombre", "km", COLOR_RECUPERAR,
                                 "Km por recuperar (promedio)", DIAS_SEMANA,
                                 extra_tooltip=dias_tt))


# ── Consultar un día guardado ─────────────────────────────────────────────────

CLAVE_CONFIRMAR_BORRADO = "_hist_confirmar_borrado"


def _mb(bytes_: int) -> str:
    return f"{bytes_ / 1024 / 1024:,.1f} MB".replace(",", "X").replace(".", ",").replace("X", ".")


def _lista_fechas(fechas: list, maximo: int = 8) -> str:
    textos = [_fecha_corta(f) for f in sorted(fechas)]
    if len(textos) > maximo:
        return ", ".join(textos[:maximo]) + f" y {len(textos) - maximo} más"
    return ", ".join(textos)


def _dialogo_borrar_dias(elegido) -> None:
    """Ventana para escoger qué días borrar del historial, con confirmación."""
    st.session_state[CLAVE_CONFIRMAR_BORRADO] = False

    @st.dialog("🗑️ Borrar días revisados", width="large")
    def dialogo():
        todos_los_dias = sorted(bd.dias()["fecha"], reverse=True)
        _html('<div class="borrar-ayuda">Escoge los días que quieres borrar del historial. '
              'Se borran su resumen, sus casos y el Excel guardado, y se libera el espacio '
              f'en el servidor. La base de datos ocupa hoy <b>{_mb(bd.tamano_bd())}</b>.</div>')
        todos = st.checkbox(f"Seleccionar todos los días guardados ({len(todos_los_dias)})",
                            key="hist_borrar_todos")
        seleccion = st.multiselect(
            "Días a borrar", todos_los_dias, format_func=_fecha_larga,
            default=[elegido] if elegido in todos_los_dias else [],
            key="hist_borrar_dias", disabled=todos, placeholder="Escoge uno o varios días")
        if todos:
            seleccion = todos_los_dias
        if not seleccion:
            st.caption("No hay días seleccionados.")
            return

        if not st.session_state.get(CLAVE_CONFIRMAR_BORRADO):
            st.button(f"🗑️ Borrar {len(seleccion)} día(s)", type="primary",
                      key="hist_borrar_pedir", use_container_width=True,
                      on_click=lambda: st.session_state.update({CLAVE_CONFIRMAR_BORRADO: True}))
            return

        _html(f'<div class="aviso-reemplazo">⚠️ ¿Seguro que quieres borrar <b>{len(seleccion)} '
              f'día(s)</b> del historial?<br><span class="borrar-lista">'
              f'{escape(_lista_fechas(seleccion))}</span><br>'
              '<b>Esta acción no se puede deshacer.</b> Si los necesitas de nuevo tendrás que '
              'volver a analizarlos.</div>')
        no, si = st.columns(2)
        no.button("Cancelar", key="hist_borrar_no", use_container_width=True,
                  on_click=lambda: st.session_state.update({CLAVE_CONFIRMAR_BORRADO: False}))
        if si.button("Sí, borrar definitivamente", type="primary", key="hist_borrar_si",
                     use_container_width=True):
            antes = bd.tamano_bd()
            with st.spinner("Borrando y liberando espacio..."):
                borrados = bd.eliminar_varios(seleccion)
            liberado = max(antes - bd.tamano_bd(), 0)
            st.session_state["hist_mensaje"] = (
                f"Se borraron {borrados} día(s) del historial · espacio liberado: {_mb(liberado)}.")
            st.session_state[CLAVE_CONFIRMAR_BORRADO] = False
            st.rerun()

    dialogo()


def _consultar_dia(dias: pd.DataFrame) -> None:
    with st.container(border=True):
        _html('<div class="section-title">🔎 Consultar un día guardado</div>')
        tabla = dias.sort_values("fecha", ascending=False)
        fechas = list(tabla["fecha"])
        c_sel, _ = st.columns([1.2, 2])
        with c_sel:
            elegido = st.selectbox("Día", fechas, format_func=_fecha_larga, key="hist_consulta",
                                   label_visibility="collapsed")
        fila = tabla[tabla["fecha"] == elegido].iloc[0]
        tipo = fila.get("tipo_dia")
        tipo_guardado = (f"Analizado como día <b>{NOMBRES_TIPO.get(tipo, tipo)}</b> · "
                         if isinstance(tipo, str) and tipo else "")

        _html(f"""
        <div class="dia-ficha">
            <div><span>Km recorridos</span><b>{_num(fila['km_recorridos'], 1)}</b></div>
            <div><span>Km por recuperar</span><b class="naranja">{_num(fila['km_por_recuperar'], 1)}</b></div>
            <div><span>Casos a revisar</span><b class="rojo">{_num(fila['casos_revisar'])}</b></div>
            <div><span>Unidades</span><b>{_num(fila['vehiculos'])}</b></div>
            <div><span>Total usuarios día</span><b>{_num(fila['usuarios'])}</b></div>
        </div>
        <div class="dia-origen">{tipo_guardado}Guardado el {escape(str(fila['guardado_en']))} · archivos:
            <em>{escape(str(fila['archivo_usos'] or '—'))}</em> +
            <em>{escape(str(fila['archivo_servicios'] or '—'))}</em></div>""")

        c_desc, c_elim, _ = st.columns([1.3, .7, 2])
        with c_desc:
            archivo = bd.excel(elegido)
            if archivo:
                contenido, nombre = archivo
                st.download_button("⬇️  Descargar Excel de este día", data=contenido,
                                   file_name=nombre, key="hist_descargar",
                                   mime="application/vnd.openxmlformats-officedocument."
                                        "spreadsheetml.sheet",
                                   use_container_width=True)
        with c_elim:
            if st.button("🗑️ Borrar días", key="hist_eliminar", use_container_width=True,
                         help="Escoge uno o varios días guardados para borrarlos."):
                _dialogo_borrar_dias(elegido)

        revisar = bd.detalle([elegido])
        revisar = revisar[revisar["validacion"].str.startswith("REVISAR")]
        with st.expander(f"Ver casos a revisar guardados de este día ({len(revisar):,})"):
            vista = (revisar.sort_values("km_por_recuperar", ascending=False)
                            .rename(columns={"vehiculo": "Vehículo", "linea": "Línea",
                                             "hora": "Inicio", "validacion": "Validación",
                                             "recorrido_m": "Recorrido (m)",
                                             "minimo_m": "Mínimo (m)",
                                             "diferencia_m": "Diferencia (m)", "usos": "Usos",
                                             "km_por_recuperar": "Km por recuperar"})
                            .drop(columns=["fecha"]))
            st.dataframe(vista, hide_index=True, use_container_width=True, height=520,
                         column_config={
                             "Km por recuperar": st.column_config.NumberColumn(format="%.2f"),
                             "Recorrido (m)": st.column_config.NumberColumn(format="%d"),
                             "Mínimo (m)": st.column_config.NumberColumn(format="%d"),
                             "Diferencia (m)": st.column_config.NumberColumn(format="%d"),
                         })


def _tabla_dias(dias: pd.DataFrame) -> None:
    with st.container(border=True):
        _html('<div class="section-title">🗂️ Días guardados en el período</div>')
        vista = (dias.sort_values("fecha", ascending=False)
                     .assign(Fecha=lambda d: d["fecha"].dt.strftime("%d/%m/%Y"),
                             Día=lambda d: d["fecha"].dt.weekday.map(lambda x: DIAS_SEMANA[x]),
                             Tipo=lambda d: d["tipo_dia"].map(
                                 lambda t: NOMBRES_TIPO.get(t, "—") if isinstance(t, str) else "—"))
                     [["Fecha", "Día", "Tipo", "km_recorridos", "km_por_recuperar", "casos_revisar",
                       "sin_km", "km_bajo", "usos_sin_viaje", "vehiculos", "guardado_en"]]
                     .rename(columns={"km_recorridos": "Km recorridos",
                                      "km_por_recuperar": "Km por recuperar",
                                      "casos_revisar": "Casos a revisar", "sin_km": "Distancia 0",
                                      "km_bajo": "Equivalencia", "usos_sin_viaje": "Usos sin información en SAE",
                                      "vehiculos": "Unidades", "guardado_en": "Guardado el"}))
        if (vista["Usos sin información en SAE"] == 0).all():
            vista = vista.drop(columns=["Usos sin información en SAE"])
        maximo = float(max(vista["Km por recuperar"].max(), 1))
        st.dataframe(vista, hide_index=True, use_container_width=True,
                     height=min(38 + 35 * len(vista), 420),
                     column_config={
                         "Km recorridos": st.column_config.NumberColumn(format="%.1f"),
                         "Km por recuperar": st.column_config.ProgressColumn(
                             format="%.1f", min_value=0, max_value=maximo),
                     })


# ── Sección completa ──────────────────────────────────────────────────────────

def seccion() -> None:
    _html('<div id="historial"></div>')
    _encabezado_seccion()

    if "hist_mensaje" in st.session_state:
        st.success(st.session_state.pop("hist_mensaje"))

    try:
        dias = bd.dias()
    except Exception as e:  # base dañada o bloqueada: la app sigue funcionando
        st.error(f"❌ No se pudo leer la base de datos del historial: {e}")
        return

    if dias.empty:
        with st.container(border=True):
            _vacio("Todavía no hay días guardados.<br>Cada día que analices se guarda "
                   "automáticamente y aparecerá aquí.")
        return

    with st.container(border=True):
        filtrado, periodo, titulo = _filtros(dias)
    if filtrado.empty:
        with st.container(border=True):
            _vacio("No hay días guardados con esos filtros.")
        return

    desde, hasta = filtrado["fecha"].min(), filtrado["fecha"].max()
    rango = (_fecha_larga(desde) if desde == hasta
             else f"del {_fecha_corta(desde)} al {_fecha_corta(hasta)}")
    _html(f'<div class="hist-rango"><b>{escape(titulo)}</b> · {rango} · '
          f'{len(filtrado)} día(s)</div>')

    _indicadores(filtrado)
    st.markdown("<br>", unsafe_allow_html=True)
    _destacados(filtrado)
    st.markdown("<br>", unsafe_allow_html=True)

    detalle = bd.detalle(list(filtrado["fecha"]))
    _graficos(filtrado, detalle, periodo)

    # Una debajo de la otra, a todo lo ancho
    _tabla_dias(filtrado)
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    _consultar_dia(filtrado)


# ── Guardar el día analizado (con confirmación si ya existe) ──────────────────

def _guardar(sesion: dict, estado: str) -> None:
    from src.reporte_excel import nombre_archivo
    r = sesion["analisis"]
    bd.guardar(r, sesion["excel"], nombre_archivo(r), sesion["nombre_usos"],
               sesion["nombre_servicios"])
    sesion["guardado"] = estado


def _comparacion(fecha, nuevo) -> str:
    anterior = bd.dias()
    anterior = anterior[anterior["fecha"] == pd.Timestamp(fecha)]
    if anterior.empty:
        return ""
    a = anterior.iloc[0]
    detalle = bd.detalle_del_dia(nuevo)
    n = bd.resumen_del_dia(nuevo, detalle)
    filas = [("Km recorridos", a["km_recorridos"], n["km_recorridos"], 1),
             ("Km por recuperar", a["km_por_recuperar"], n["km_por_recuperar"], 1),
             ("Casos a revisar", a["casos_revisar"], n["casos_revisar"], 0)]
    cuerpo = "".join(f"<tr><td>{t}</td><td>{_num(x, d)}</td><td><b>{_num(y, d)}</b></td></tr>"
                     for t, x, y, d in filas)
    return (f'<table class="tabla-comparar"><tr><th></th><th>Guardado</th><th>Nuevo</th></tr>'
            f'{cuerpo}</table>')


def _preguntar_reemplazo(sesion: dict) -> None:
    @st.dialog("⚠️ Este día ya está guardado")
    def dialogo():
        r = sesion["analisis"]
        cuando = bd.guardado_en(r.fecha) or ""
        _html(f"""
        <div class="aviso-reemplazo">
            El día <b>{_fecha_larga(r.fecha)}</b> ya está en la base de datos
            (guardado el {escape(cuando)}).<br><br>
            <b>¿Desea reemplazar los valores que ya están de ese día?</b>
        </div>
        {_comparacion(r.fecha, r)}""")
        si, no = st.columns(2)
        if si.button("🔁 Sí, reemplazar", type="primary", key="reemplazo_si"):
            _guardar(sesion, "reemplazado")
            st.rerun()
        if no.button("✋ No, conservar", key="reemplazo_no"):
            sesion["guardado"] = "conservado"
            st.rerun()
    dialogo()


def guardar_o_preguntar(sesion: dict) -> None:
    """Guarda el día recién analizado; si ya existe, pregunta si se reemplaza."""
    try:
        if bd.existe(sesion["analisis"].fecha):
            sesion["guardado"] = "pendiente"
            _preguntar_reemplazo(sesion)
        else:
            _guardar(sesion, "guardado")
    except Exception as e:
        sesion["guardado"] = "error"
        st.error(f"❌ No se pudo guardar el día en el historial: {e}")


def estado_guardado(sesion: dict) -> None:
    """Aviso de si el día quedó guardado, con botón para guardarlo si no."""
    estado = sesion.get("guardado", "pendiente")
    mensajes = {
        "guardado": ("💾", "Día guardado en el historial", "ok"),
        "reemplazado": ("🔁", "Se reemplazaron los datos guardados de este día", "ok"),
        "conservado": ("✋", "Se conservaron los datos que ya estaban guardados de este día", "info"),
        "pendiente": ("⏳", "Este día aún no se ha guardado en el historial", "info"),
        "error": ("❌", "No se pudo guardar este día en el historial", "error"),
    }
    icono, texto, clase = mensajes.get(estado, mensajes["pendiente"])
    c_texto, c_boton = st.columns([3, 1.2])
    with c_texto:
        _html(f'<div class="estado-guardado {clase}">{icono} {texto} · '
              f'<a href="#historial">ver historial ↓</a></div>')
    with c_boton:
        if estado in ("conservado", "pendiente", "error"):
            etiqueta = "🔁 Reemplazar" if estado == "conservado" else "💾 Guardar día"
            if st.button(etiqueta, key="guardar_manual", use_container_width=True):
                guardar_o_preguntar(sesion)
                if sesion.get("guardado") == "guardado":
                    st.rerun()
