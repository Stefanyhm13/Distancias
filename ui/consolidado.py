"""Interfaz del consolidado de reclamación: PSO, casillas "Reclamar" y botón para generar.

- Panel izquierdo: tarjeta del PSO (hoja Horarios) con el campo para cargarlo o actualizarlo.
- Pestaña "Resumen REVISAR": tabla con una casilla por caso y, debajo, el panel del
  consolidado de la quincena con el botón "Generar consolidado reclamación".
- Dentro del panel: los casos que ya están en el consolidado, para corregir ruta,
  circulación o distancia, o quitarlos.
"""
from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from config import REVISION_DETALLADA
from src import consolidado as bd
from src import pso as modulo_pso
from src.consolidado import Quincena
from src.lectura import ErrorDeArchivo
from src.reporte_consolidado import generar_consolidado
from ui import componentes as ui

CLAVE_SELECCION = "reclamar_seleccion"
CLAVE_GENERADO = "consolidado_generado"
CLAVE_PSO_PROCESADO = "_pso_procesado"
MIME_EXCEL = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _html(contenido: str) -> None:
    st.markdown(contenido, unsafe_allow_html=True)


def _num(valor, decimales: int = 3) -> str:
    texto = f"{valor:,.{decimales}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def reiniciar_seleccion() -> None:
    """Se llama al analizar un día nuevo."""
    st.session_state[CLAVE_SELECCION] = set()


# ── PSO ──────────────────────────────────────────────────────────────────────

def _procesar_pso(archivo) -> None:
    identificador = (archivo.name, archivo.size)
    if st.session_state.get(CLAVE_PSO_PROCESADO) == identificador:
        return
    st.session_state[CLAVE_PSO_PROCESADO] = identificador
    try:
        with st.spinner("⏳ Leyendo el PSO (hoja Horarios)..."):
            hoja = modulo_pso.leer_pso(archivo)
            bd.guardar_pso(hoja, archivo.name)
        st.toast(f"✅ PSO actualizado: {len(hoja):,} salidas".replace(",", "."))
    except ErrorDeArchivo as e:
        st.error(f"❌ {e}")
    except Exception as e:
        st.error(f"❌ No se pudo leer el PSO: {e}")


def tarjeta_pso() -> None:
    """Estado del PSO guardado y campo para cargar uno nuevo."""
    info = bd.info_pso()
    if info:
        cargado = pd.Timestamp(info["cargado_en"]).strftime("%d/%m/%Y %H:%M")
        _html(f"""<div class="pso-estado ok">
            <div class="pso-icono">📘</div>
            <div><div class="pso-nombre">{escape(info['nombre'])}</div>
            <div class="pso-detalle">{_num(info['filas'], 0)} salidas · cargado el {cargado}</div>
            </div></div>""")
    else:
        _html("""<div class="pso-estado pendiente">
            <div class="pso-icono">📙</div>
            <div><div class="pso-nombre">Aún no hay PSO cargado</div>
            <div class="pso-detalle">Se necesita para calcular la distancia a reclamar.</div>
            </div></div>""")
    with st.expander("📤 Cargar o actualizar PSO", expanded=info is None):
        st.caption("Archivo con la hoja **Horarios** (por ejemplo, un consolidado anterior). "
                   "Se lee la hoja completa y se copia igual en el consolidado; para calcular "
                   "la distancia se usan Tipo día, Ruta, Circulación, Hora y Distancia Media "
                   "(columnas O a S). Queda guardado: solo hay que cargarlo de nuevo si el PSO "
                   "cambia.")
        archivo = st.file_uploader("PSO", type=["xlsx", "xlsm", "xls"], key="archivo_pso",
                                   label_visibility="collapsed")
        if archivo is not None:
            _procesar_pso(archivo)


# ── Selección de casos ───────────────────────────────────────────────────────

def _incluidos(resultado, quincena: Quincena) -> set[int]:
    guardadas = bd.claves_guardadas(quincena)
    return {i for i, caso in enumerate(resultado.casos) if bd.clave_caso(caso) in guardadas}


def tabla_resumen(sesion: dict, filtros: list[str]) -> None:
    """Tabla del resumen con casillas "Reclamar" y, debajo, el panel del consolidado."""
    r = sesion["analisis"]
    quincena = Quincena.de(r.fecha)
    incluidos = _incluidos(r, quincena)
    _html('<div class="guia-reclamar">✔ Marca en la columna <b>Reclamar</b> (al final de la tabla) los casos que '
          'vas a incluir en el consolidado de reclamación. Puedes filtrar y buscar; las marcas '
          'se conservan.</div>')
    seleccion = st.session_state.get(CLAVE_SELECCION, set())
    seleccion = ui.tabla_seleccionable(r.resumen, "resumen", filtros, seleccion, incluidos,
                                       colorear="Validación")
    st.session_state[CLAVE_SELECCION] = seleccion
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    panel_consolidado(r, quincena, seleccion, incluidos)


# ── Panel del consolidado ────────────────────────────────────────────────────

def _estado_quincena(quincena: Quincena) -> str:
    datos = bd.resumen_quincena(quincena)
    if not datos["registros"]:
        return (f'<div class="cons-estado nuevo">🆕 Aún no hay consolidado de '
                f'<b>{quincena.nombre}</b>: se creará con los casos que marques.</div>')
    dias = ", ".join(f"{d:%d}" for d in datos["dias"])
    pendientes = (f' · <span class="cons-alerta">{datos["sin_distancia"]} sin distancia</span>'
                  if datos["sin_distancia"] else "")
    return (f'<div class="cons-estado existe">📑 Ya existe el consolidado de '
            f'<b>{quincena.nombre}</b> con <b>{datos["registros"]}</b> registro(s) de los días '
            f'{dias} · <b>{_num(datos["km"])} km</b>{pendientes}. '
            f'Los casos nuevos se agregan en orden de fecha.</div>')


def _generar(quincena: Quincena, mensaje: str) -> None:
    """Arma el Excel con todos los casos de la quincena y guarda una copia."""
    pso = bd.cargar_pso()
    contenido = generar_consolidado(quincena, bd.casos(quincena), pso[0] if pso else None)
    copia = None
    try:
        copia = bd.guardar_copia(contenido, quincena)
    except PermissionError:
        mensaje += (" No se pudo actualizar la copia en la carpeta 'consolidados' porque el "
                    "archivo está abierto en Excel; descárgalo con el botón.")
    except OSError as e:
        mensaje += f" No se pudo guardar la copia en la carpeta 'consolidados': {e}."
    st.session_state[CLAVE_GENERADO] = {
        "quincena": quincena.clave, "contenido": contenido, "nombre": quincena.nombre_archivo,
        "mensaje": mensaje, "copia": str(copia) if copia else "",
    }


CLAVE_PENDIENTE = "_consolidado_pendiente"


def _pedir_generacion(clave_quincena: str, posiciones: list[int]) -> None:
    """Al presionar el botón: se guarda el pedido y se limpian las casillas.

    El trabajo se hace en `_generar_pendiente`. Si la página se recarga a mitad de camino,
    el pedido sigue pendiente y se termina en la siguiente vuelta sin repetir casos.
    """
    st.session_state[CLAVE_PENDIENTE] = {"quincena": clave_quincena,
                                         "posiciones": list(posiciones)}
    st.session_state[CLAVE_SELECCION] = set()
    st.session_state["resumen_version"] = st.session_state.get("resumen_version", 0) + 1


def _generar_pendiente(resultado, quincena: Quincena, pso) -> None:
    pedido = st.session_state.get(CLAVE_PENDIENTE)
    if not pedido or pedido["quincena"] != quincena.clave:
        return
    try:
        with st.spinner("⏳ Generando el consolidado de la quincena..."):
            if "agregados" not in pedido:
                casos = bd.preparar_casos(resultado, pedido["posiciones"], pso[1] if pso else None)
                pedido["agregados"], pedido["ya_estaban"] = bd.agregar(casos)
            mensaje = (f"Se agregaron {pedido['agregados']} registro(s) al consolidado de "
                       f"{quincena.nombre}.")
            if pedido["ya_estaban"]:
                mensaje += f" {pedido['ya_estaban']} ya estaban y no se repitieron."
            _generar(quincena, mensaje)
        st.session_state.pop(CLAVE_PENDIENTE, None)
        st.rerun()
    except Exception as e:
        st.session_state.pop(CLAVE_PENDIENTE, None)
        st.error(f"❌ No se pudo generar el consolidado: {e}")


def panel_consolidado(resultado, quincena: Quincena, seleccion: set, incluidos: set) -> None:
    pso = bd.cargar_pso()
    with st.container(border=True):
        ui.titulo_seccion("📑 Consolidado de reclamación")
        if "cons_mensaje" in st.session_state:
            st.success(f"✅ {st.session_state.pop('cons_mensaje')}")
        _html(f'<div class="cons-quincena"><span class="cons-chip">{quincena.nombre}</span>'
              f'<span>Quincena del {quincena.rango}</span>'
              f'<span class="cons-archivo">📄 {escape(quincena.nombre_archivo)}</span></div>')
        _html(_estado_quincena(quincena))

        nuevos = sorted(seleccion - incluidos)
        repetidos = len(seleccion & incluidos)
        registros = bd.unir_seguidos([resultado.casos[i] for i in nuevos],
                                      resultado.horarios_viajes) if nuevos else []
        sin_sae = sum(1 for i in nuevos if resultado.casos[i]["tipo"] != "viaje")

        c1, c2, c3 = st.columns(3)
        with c1:
            ui.tarjeta_metrica("✔", str(len(seleccion)), "Casos marcados", "blue")
        with c2:
            ui.tarjeta_metrica("🧾", str(len(registros)), "Registros a agregar", "teal")
        with c3:
            ui.tarjeta_metrica("🔎", str(sin_sae), REVISION_DETALLADA.capitalize(), "orange")
        notas = []
        if len(registros) < len(nuevos):
            notas.append(f"Los {len(nuevos)} casos nuevos quedan en {len(registros)} registro(s): "
                         "se unen los casos seguidos de la misma unidad, ruta y circulación.")
        if repetidos:
            notas.append(f"{repetidos} caso(s) marcado(s) ya están en el consolidado y no se "
                         "repiten.")
        if sin_sae:
            notas.append(f"Los usos sin información en SAE quedan con ruta y circulación "
                         f"'{REVISION_DETALLADA}' y sin distancia.")
        if pso is None:
            notas.append("⚠️ Carga el PSO (panel izquierdo) para calcular la distancia a reclamar.")
        for nota in notas:
            _html(f'<div class="cons-nota">• {escape(nota)}</div>')

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        _, centro, _ = st.columns([1, 2, 1])
        with centro:
            st.button("📑 Generar consolidado reclamación", type="primary",
                      use_container_width=True, key="generar_consolidado",
                      disabled=not nuevos or pso is None, on_click=_pedir_generacion,
                      args=(quincena.clave, nuevos),
                      help="Agrega los casos marcados al consolidado de la quincena "
                           "y descarga el Excel.")
        _generar_pendiente(resultado, quincena, pso)

        generado = st.session_state.get(CLAVE_GENERADO)
        if generado and generado["quincena"] == quincena.clave:
            st.success(f"✅ {generado['mensaje']}")
            _, centro, _ = st.columns([1, 2, 1])
            with centro:
                st.download_button(f"⬇️  Descargar {generado['nombre']}", generado["contenido"],
                                   file_name=generado["nombre"], mime=MIME_EXCEL,
                                   use_container_width=True, key="descargar_consolidado")
            if generado["copia"]:
                st.caption(f"Copia guardada en: {generado['copia']}")

        _casos_guardados(quincena, pso)

        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        _, c_borrar = st.columns([3, 1.2])
        with c_borrar:
            if st.button("🗑️ Borrar consolidados", key="cons_borrar", use_container_width=True,
                         disabled=not bd.quincenas(),
                         help="Escoge una o varias quincenas para borrar su consolidado."):
                _dialogo_borrar_consolidados(quincena)


CLAVE_CONFIRMAR_BORRADO = "_cons_confirmar_borrado"


def _mb(bytes_: int) -> str:
    return f"{bytes_ / 1024 / 1024:,.1f} MB".replace(",", "X").replace(".", ",").replace("X", ".")


def _dialogo_borrar_consolidados(actual: Quincena) -> None:
    """Ventana para escoger qué consolidados (por quincena) borrar, con confirmación."""
    from src import historial as bd_historial
    st.session_state[CLAVE_CONFIRMAR_BORRADO] = False

    @st.dialog("🗑️ Borrar consolidados", width="large")
    def dialogo():
        lista = bd.quincenas()
        datos = {q.clave: bd.resumen_quincena(q)["registros"] for q in lista}
        _html('<div class="borrar-ayuda">Escoge las quincenas cuyo consolidado quieres borrar. '
              'Se borran sus registros, la evidencia guardada y la copia del Excel en la carpeta '
              'de consolidados, y se libera el espacio en el servidor. La base de datos ocupa hoy '
              f'<b>{_mb(bd_historial.tamano_bd())}</b>.</div>')
        todos = st.checkbox(f"Seleccionar todos los consolidados ({len(lista)})",
                            key="cons_borrar_todos")
        seleccion = st.multiselect(
            "Consolidados a borrar", lista,
            format_func=lambda q: f"{q.nombre} {q.anio} · {datos[q.clave]} registro(s)",
            default=[actual] if actual in lista else [], key="cons_borrar_sel",
            disabled=todos, placeholder="Escoge una o varias quincenas")
        if todos:
            seleccion = lista
        if not seleccion:
            st.caption("No hay consolidados seleccionados.")
            return

        if not st.session_state.get(CLAVE_CONFIRMAR_BORRADO):
            st.button(f"🗑️ Borrar {len(seleccion)} consolidado(s)", type="primary",
                      key="cons_borrar_pedir", use_container_width=True,
                      on_click=lambda: st.session_state.update({CLAVE_CONFIRMAR_BORRADO: True}))
            return

        nombres = ", ".join(f"{q.nombre} {q.anio}" for q in seleccion)
        total = sum(datos[q.clave] for q in seleccion)
        _html(f'<div class="aviso-reemplazo">⚠️ ¿Seguro que quieres borrar <b>{len(seleccion)} '
              f'consolidado(s)</b> con <b>{total} registro(s)</b>?<br>'
              f'<span class="borrar-lista">{escape(nombres)}</span><br>'
              '<b>Esta acción no se puede deshacer.</b> Si ya descargaste el Excel, ese archivo '
              'no se ve afectado.</div>')
        no, si = st.columns(2)
        no.button("Cancelar", key="cons_borrar_no", use_container_width=True,
                  on_click=lambda: st.session_state.update({CLAVE_CONFIRMAR_BORRADO: False}))
        if si.button("Sí, borrar definitivamente", type="primary", key="cons_borrar_si",
                     use_container_width=True):
            antes = bd_historial.tamano_bd()
            with st.spinner("Borrando y liberando espacio..."):
                registros, archivos = bd.eliminar_quincenas(seleccion)
            liberado = max(antes - bd_historial.tamano_bd(), 0)
            borradas = {q.clave for q in seleccion}
            generado = st.session_state.get(CLAVE_GENERADO)
            if generado and generado["quincena"] in borradas:
                st.session_state.pop(CLAVE_GENERADO, None)
            st.session_state[CLAVE_CONFIRMAR_BORRADO] = False
            st.session_state["cons_mensaje"] = (f"Se borraron {len(seleccion)} consolidado(s) ({registros} registro(s), "
                     f"{archivos} archivo(s) Excel) · espacio liberado: {_mb(liberado)}.")
            st.rerun()

    dialogo()


# ── Casos guardados de la quincena ───────────────────────────────────────────

def _tabla_guardados(casos: list) -> pd.DataFrame:
    def origen(c):
        if c.distancia_km is None:
            return "Por definir"
        return "Escrita en la app" if c.distancia_manual else "PSO"
    return pd.DataFrame({
        "Fecha": [f"{c.fecha:%d/%m/%Y}" for c in casos],
        "Unidad": [c.unidad for c in casos],
        "Ruta": [c.ruta for c in casos],
        "Circulación": [c.circulacion for c in casos],
        "Hora inicio": [f"{c.inicio:%H:%M:%S}" for c in casos],
        "Hora fin": [f"{c.fin:%H:%M:%S}" for c in casos],
        "Usuarios": [c.usuarios for c in casos],
        "Distancia (km)": [c.distancia_km for c in casos],
        "Distancia según": [origen(c) for c in casos],
        "Quitar": False,
    }, index=[c.id for c in casos])


def _casos_guardados(quincena: Quincena, pso) -> None:
    casos = bd.casos(quincena)
    if not casos:
        return
    with st.expander(f"📂 Ver y corregir los registros del consolidado de {quincena.nombre} "
                     f"({len(casos)})"):
        st.caption("Puedes corregir **Ruta**, **Circulación** o **Distancia (km)** (por ejemplo, "
                   f"en los casos {REVISION_DETALLADA}). Si cambias la ruta o la circulación, la "
                   "distancia se vuelve a calcular con el PSO. Marca **Quitar** para sacar un "
                   "registro del consolidado.")
        tabla = _tabla_guardados(casos)
        editado = st.data_editor(
            tabla, key=f"guardados_{quincena.clave}_{st.session_state.get('_guardados_v', 0)}",
            use_container_width=True, hide_index=True,
            disabled=["Fecha", "Unidad", "Hora inicio", "Hora fin", "Usuarios", "Distancia según"],
            column_config={
                "Quitar": st.column_config.CheckboxColumn("🗑️ Quitar", width=ui._ancho(95)),
                "Ruta": st.column_config.TextColumn("✏️ Ruta"),
                "Circulación": st.column_config.TextColumn("✏️ Circulación"),
                "Distancia (km)": st.column_config.NumberColumn(
                    "✏️ Distancia (km)", format="%.3f", min_value=0),
                "Distancia según": st.column_config.TextColumn(width=ui._ancho(140)),
            }, **ui.SIN_NONE_EDITOR)
        c_guardar, c_quitar, c_excel = st.columns(3)
        cambios = editado[["Ruta", "Circulación", "Distancia (km)"]].compare(
            tabla[["Ruta", "Circulación", "Distancia (km)"]]).index if len(tabla) else []
        quitar = list(editado.index[editado["Quitar"].astype(bool)])
        with c_guardar:
            guardar = st.button("💾 Guardar cambios", use_container_width=True,
                                disabled=len(cambios) == 0, key="guardados_guardar")
        with c_quitar:
            eliminar = st.button(f"🗑️ Quitar marcados ({len(quitar)})", use_container_width=True,
                                 disabled=not quitar, key="guardados_quitar")
        with c_excel:
            regenerar = st.button("🔄 Volver a generar Excel", use_container_width=True,
                                  key="guardados_excel")
        if guardar or eliminar or regenerar:
            with st.spinner("⏳ Actualizando el consolidado..."):
                if guardar:
                    for id_caso in cambios:
                        fila = editado.loc[id_caso]
                        bd.actualizar(id_caso, fila["Ruta"], fila["Circulación"],
                                      fila["Distancia (km)"], pso[1] if pso else None)
                    mensaje = f"Se guardaron los cambios de {len(cambios)} registro(s)."
                elif eliminar:
                    bd.eliminar(quitar)
                    mensaje = f"Se quitaron {len(quitar)} registro(s) del consolidado."
                else:
                    mensaje = f"Consolidado de {quincena.nombre} generado de nuevo."
                _generar(quincena, mensaje)
            st.session_state["_guardados_v"] = st.session_state.get("_guardados_v", 0) + 1
            st.rerun()
