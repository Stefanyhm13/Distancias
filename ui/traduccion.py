"""
Textos de Streamlit en español.

Streamlit trae en inglés los textos de sus controles (cargador de archivos, menú de
las columnas de las tablas, buscador de la tabla, desplegables, menú de la app...).
Este módulo agrega a la página un pequeño script que reemplaza esos textos por su
versión en español cada vez que aparecen. No toca los datos de las tablas.
"""
import json

import streamlit as st

# Texto exacto en inglés -> español
TEXTOS = {
    # Cargador de archivos
    "Drag and drop file here": "Arrastra y suelta el archivo aquí",
    "Drag and drop files here": "Arrastra y suelta los archivos aquí",
    "Browse files": "Buscar archivo",
    "Browse file": "Buscar archivo",
    "Upload": "Cargar",
    "Upload file": "Cargar archivo",
    "Remove file": "Quitar archivo",
    "Delete": "Eliminar",
    "Clear": "Borrar",
    # Menú de cada columna de las tablas
    "Sort ascending": "Ordenar de menor a mayor",
    "Sort descending": "Ordenar de mayor a menor",
    "Format": "Formato",
    "Autosize": "Ajustar ancho",
    "Pin column": "Fijar columna",
    "Unpin column": "Soltar columna",
    "Hide column": "Ocultar columna",
    "Automatic": "Automático",
    "Localized": "Local",
    "Plain": "Simple",
    "Percent": "Porcentaje",
    "Scientific": "Científico",
    "Accounting": "Contable",
    "Compact": "Compacto",
    "Engineering": "Ingeniería",
    "Dollar": "Dólar",
    "Euro": "Euro",
    "Yen": "Yen",
    "Relative": "Relativo",
    "Calendar": "Calendario",
    "Date": "Fecha",
    "Time": "Hora",
    "Date & time": "Fecha y hora",
    "Date & Time": "Fecha y hora",
    # Barra de herramientas de las tablas
    "Search": "Buscar",
    "Search...": "Buscar...",
    "Download as CSV": "Descargar como CSV",
    "Fullscreen": "Pantalla completa",
    "Close fullscreen": "Salir de pantalla completa",
    "Exit fullscreen": "Salir de pantalla completa",
    "Show/hide columns": "Mostrar u ocultar columnas",
    "Show all": "Mostrar todas",
    "Add row": "Agregar fila",
    "Delete row": "Eliminar fila",
    "Delete rows": "Eliminar filas",
    "Clear selection": "Quitar selección",
    "Copy": "Copiar",
    "Copy to clipboard": "Copiar",
    "Copied": "Copiado",
    "Copied to clipboard": "Copiado",
    "Close": "Cerrar",
    "Download": "Descargar",
    "No results": "Sin resultados",
    "No results found": "Sin resultados",
    "No options to select.": "No hay opciones.",
    "No options to select": "No hay opciones",
    "Choose an option": "Elige una opción",
    "Choose options": "Elige opciones",
    "Select...": "Selecciona...",
    "Select all": "Seleccionar todo",
    "Press Enter to apply": "Presiona Enter para aplicar",
    "Press Enter to submit form": "Presiona Enter para enviar",
    "Increment value": "Aumentar",
    "Decrement value": "Disminuir",
    "Increment": "Aumentar",
    "Decrement": "Disminuir",
    "Show password text": "Mostrar",
    "Open": "Abrir",
    # Ventanas emergentes, avisos y estado de la app
    "Running...": "Procesando...",
    "Running": "Procesando",
    "Stop": "Detener",
    "Rerun": "Volver a cargar",
    "Always rerun": "Recargar siempre",
    "Source file changed.": "El código cambió.",
    "File change.": "El código cambió.",
    "Settings": "Configuración",
    "Print": "Imprimir",
    "Record a screencast": "Grabar pantalla",
    "About": "Acerca de",
    "Developer options": "Opciones de desarrollador",
    "Clear cache": "Borrar caché",
    "Deploy": "Publicar",
    "Main menu": "Menú principal",
    "View fullscreen": "Ver en pantalla completa",
    "Expand": "Expandir",
    "Collapse": "Contraer",
    "Show more": "Ver más",
    "Show less": "Ver menos",
    "Connecting": "Conectando",
    "Please wait...": "Espera un momento...",
    "Connection error": "Error de conexión",
    # Gráficos del historial (menú "...")
    "Show data": "Ver datos",
    "Hide data": "Ocultar datos",
    "Show chart": "Ver gráfico",
    "Download as PNG": "Descargar como PNG",
    "Download as SVG": "Descargar como SVG",
    "Copy Vega-Lite spec": "Copiar especificación del gráfico",
    "Save as SVG": "Guardar como SVG",
    "Save as PNG": "Guardar como PNG",
    "View Source": "Ver código",
    "View Compiled Vega": "Ver Vega compilado",
    "Open in Vega Editor": "Abrir en el editor de Vega",
}

# Textos que cambian (ej. "Limit 200MB per file • XLSX, XLS"): [patrón, reemplazo]
PATRONES = [
    [r"^Limit (\S+) per file • (.*)$", "$2 · máx. $1"],
    [r"^Limit (\S+) per file(.*)$", "Máximo $1 por archivo$2"],
    [r"^(\S+) per file(.*)$", "Máximo $1 por archivo$2"],
    [r"^(\d+) rows?$", "$1 filas"],
    [r"^Remove (.+)$", "Quitar $1"],
]

_SCRIPT = """
<script>
(function () {
  const ventana = window.parent;
  const doc = ventana.document;
  if (ventana.__traduccionSAO) { return; }
  ventana.__traduccionSAO = true;

  const DATOS = {"textos": __TEXTOS__, "patrones": __PATRONES__};

  const codigo = `
  (function () {
    const DATOS = JSON.parse(document.currentScript.dataset.datos);
    const TEXTOS = DATOS.textos;
    const PATRONES = DATOS.patrones.map(p => [new RegExp(p[0]), p[1]]);
    const ATRIBUTOS = ["placeholder", "aria-label", "title"];

    function traducir(texto) {
      if (!texto) return null;
      const limpio = texto.trim();
      if (!limpio) return null;
      if (Object.prototype.hasOwnProperty.call(TEXTOS, limpio)) {
        return texto.replace(limpio, TEXTOS[limpio]);
      }
      for (const [patron, reemplazo] of PATRONES) {
        if (patron.test(limpio)) return texto.replace(limpio, limpio.replace(patron, reemplazo));
      }
      return null;
    }

    function revisarNodo(nodo) {
      if (nodo.nodeType === 3) {
        const nuevo = traducir(nodo.nodeValue);
        if (nuevo !== null && nuevo !== nodo.nodeValue) nodo.nodeValue = nuevo;
        return;
      }
      if (nodo.nodeType !== 1) return;
      const etiqueta = nodo.tagName;
      if (etiqueta === "SCRIPT" || etiqueta === "STYLE" || etiqueta === "TEXTAREA") return;
      for (const atributo of ATRIBUTOS) {
        const valor = nodo.getAttribute && nodo.getAttribute(atributo);
        if (valor) {
          const nuevo = traducir(valor);
          if (nuevo !== null && nuevo !== valor) nodo.setAttribute(atributo, nuevo);
        }
      }
      for (const hijo of nodo.childNodes) revisarNodo(hijo);
    }

    let pendientes = [];
    let programado = false;
    function procesar() {
      programado = false;
      const lista = pendientes;
      pendientes = [];
      for (const nodo of lista) { if (nodo.isConnected) revisarNodo(nodo); }
    }
    function encolar(nodo) {
      pendientes.push(nodo);
      if (!programado) { programado = true; requestAnimationFrame(procesar); }
    }

    revisarNodo(document.body);
    new MutationObserver(cambios => {
      for (const c of cambios) {
        if (c.type === "childList") { c.addedNodes.forEach(encolar); }
        else if (c.type === "characterData") { encolar(c.target); }
        else if (c.type === "attributes") { encolar(c.target); }
      }
    }).observe(document.body, {
      childList: true, subtree: true, characterData: true,
      attributes: true, attributeFilter: ATRIBUTOS,
    });
  })();`;

  const script = doc.createElement("script");
  script.dataset.datos = JSON.stringify(DATOS);
  script.textContent = codigo;
  doc.head.appendChild(script);
})();
</script>
"""


def instalar() -> None:
    """Agrega el traductor a la página (una sola vez; no ocupa espacio)."""
    import streamlit.components.v1 as components
    script = (_SCRIPT.replace("__TEXTOS__", json.dumps(TEXTOS, ensure_ascii=False))
                     .replace("__PATRONES__", json.dumps(PATRONES)))
    components.html(script, height=0)
