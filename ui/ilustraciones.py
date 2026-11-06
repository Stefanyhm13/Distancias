"""
Ilustraciones en caricatura de los buses SAO (SVG dibujado a mano, sin imágenes externas).

  - bus_alimentador(): buseta blanca con franjas verde y amarilla.
  - bus_electrico():   bus eléctrico blanco con frente verde y diseño verde/naranja.
  - paisaje():         montañas, edificios, viaducto del metro y la vía.
  - operadores():      tres operadores con el uniforme SAO (animados).

Todo se entrega como `data:` URI para usarlo en <img> o en CSS.
"""
import base64

VERDE = "#1B7A3E"
VERDE_CLARO = "#2ECC71"
AMARILLO = "#F4C430"
NARANJA = "#F28C28"
VIDRIO = "#24343D"
LLANTA = "#1E272C"


def uri(svg: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode()


def _rueda(cx: float, cy: float, r: float = 15) -> str:
    return f"""
    <g>
      <circle cx="{cx}" cy="{cy}" r="{r + 3}" fill="#3A464C"/>
      <circle cx="{cx}" cy="{cy}" r="{r}" fill="{LLANTA}"/>
      <circle cx="{cx}" cy="{cy}" r="{r * 0.5}" fill="#CFD8DC"/>
      <circle cx="{cx}" cy="{cy}" r="{r * 0.18}" fill="#78909C"/>
    </g>"""


def _brillo(x: float, y: float, alto: float) -> str:
    return (f'<path d="M{x + 4} {y + alto - 4} L{x + 14} {y + 4}" stroke="#FFFFFF" '
            f'stroke-opacity=".28" stroke-width="5" stroke-linecap="round"/>')


def bus_alimentador() -> str:
    """Buseta alimentadora vista de lado, mirando a la derecha (240 × 130)."""
    ventanas = "".join(
        f'<rect x="{x}" y="32" width="36" height="30" rx="5" fill="{VIDRIO}"/>{_brillo(x, 32, 30)}'
        for x in (22, 62, 102, 142))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 130">
  <ellipse cx="122" cy="120" rx="108" ry="6" fill="#000" opacity=".18"/>
  <rect x="34" y="12" width="120" height="10" rx="4" fill="#E3E8E6"/>
  <path d="M18 20 Q10 20 10 30 L10 98 Q10 106 18 106 L224 106 Q232 106 232 98 L232 56
           Q232 40 220 28 L210 20 Z" fill="#FFFFFF" stroke="#B9C4C0" stroke-width="2"/>
  <clipPath id="cuerpo"><path d="M18 20 Q10 20 10 30 L10 98 Q10 106 18 106 L224 106
           Q232 106 232 98 L232 56 Q232 40 220 28 L210 20 Z"/></clipPath>
  <g clip-path="url(#cuerpo)">
    <rect x="0" y="67" width="240" height="5" fill="{AMARILLO}"/>
    <rect x="0" y="72" width="240" height="9" fill="{VERDE}"/>
    <rect x="0" y="81" width="240" height="3" fill="{AMARILLO}"/>
    <rect x="0" y="94" width="240" height="12" fill="{VERDE}"/>
  </g>
  {ventanas}
  <rect x="182" y="30" width="22" height="66" rx="4" fill="{VIDRIO}" stroke="#B9C4C0" stroke-width="2"/>
  <line x1="193" y1="32" x2="193" y2="94" stroke="#B9C4C0" stroke-width="2"/>
  <path d="M208 28 L219 30 Q229 42 229 56 L229 64 L208 64 Z" fill="{VIDRIO}"/>
  {_brillo(209, 30, 32)}
  <rect x="186" y="22" width="40" height="6" rx="2" fill="#263238"/>
  <text x="206" y="27" font-family="Arial" font-size="5" font-weight="700" fill="{NARANJA}"
        text-anchor="middle">SAO</text>
  <rect x="6" y="100" width="230" height="8" rx="4" fill="#2B3236"/>
  <ellipse cx="228" cy="88" rx="4" ry="5" fill="#FFF3B0" stroke="#E0B800"/>
  <rect x="11" y="84" width="4" height="9" rx="2" fill="#E53935"/>
  <rect x="96" y="48" width="0" height="0"/>
  {_rueda(56, 106)}
  {_rueda(184, 106)}
</svg>"""


def bus_electrico() -> str:
    """Bus 100 % eléctrico visto de lado, mirando a la derecha (300 × 140)."""
    ventanas = "".join(
        f'<rect x="{x}" y="30" width="40" height="34" rx="5" fill="{VIDRIO}"/>{_brillo(x, 30, 34)}'
        for x in (20, 64, 108, 152, 196))
    hojas = "".join(
        f'<ellipse cx="{x}" cy="{y}" rx="7" ry="3" fill="{c}" transform="rotate({a} {x} {y})"/>'
        for x, y, a, c in [(18, 108, -30, "#43A047"), (30, 110, 25, "#66BB6A"),
                           (44, 107, -40, "#2E7D32"), (58, 110, 20, "#7CB342"),
                           (72, 108, -25, "#43A047"), (210, 109, 30, "#66BB6A"),
                           (198, 107, -35, "#2E7D32")])
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 140">
  <ellipse cx="150" cy="130" rx="138" ry="6" fill="#000" opacity=".18"/>
  <rect x="58" y="8" width="150" height="10" rx="4" fill="#DDE3E1"/>
  <rect x="70" y="5" width="40" height="5" rx="2" fill="#C5CCCA"/>
  <path d="M14 18 Q8 18 8 28 L8 108 Q8 116 16 116 L284 116 Q292 116 292 108 L292 54
           Q292 34 278 24 L268 18 Z" fill="#FFFFFF" stroke="#B9C4C0" stroke-width="2"/>
  <clipPath id="cuerpoE"><path d="M14 18 Q8 18 8 28 L8 108 Q8 116 16 116 L284 116
           Q292 116 292 108 L292 54 Q292 34 278 24 L268 18 Z"/></clipPath>
  <g clip-path="url(#cuerpoE)">
    <path d="M250 70 L300 60 L300 120 L238 120 Z" fill="#2E9E4F"/>
    <path d="M262 70 L300 64 L300 74 L262 80 Z" fill="#8BC34A"/>
    <rect x="0" y="66" width="240" height="4" fill="#8BC34A"/>
    <path d="M22 80 H96 V98 H150" fill="none" stroke="{NARANJA}" stroke-width="5"
          stroke-linejoin="round"/>
    <rect x="112" y="74" width="96" height="30" rx="6" fill="#7CB342"/>
    <rect x="150" y="76" width="44" height="14" rx="4" fill="#AED581"/>
    <path d="M118 102 Q130 84 142 102" fill="none" stroke="{NARANJA}" stroke-width="4"/>
    <rect x="212" y="78" width="12" height="12" rx="2" fill="{NARANJA}"/>
    <rect x="212" y="92" width="12" height="12" rx="2" fill="#2E9E4F"/>
    <rect x="100" y="78" width="8" height="8" rx="1" fill="#1E88E5"/>
    <rect x="100" y="88" width="8" height="8" rx="1" fill="#E53935"/>
    <rect x="0" y="110" width="300" height="10" fill="#E8F5E9"/>
  </g>
  {ventanas}
  <text x="160" y="101" font-family="Arial" font-size="9" font-weight="800" fill="#FFFFFF"
        text-anchor="middle">100% ELÉCTRICO</text>
  {hojas}
  <rect x="240" y="28" width="22" height="78" rx="4" fill="{VIDRIO}" stroke="#B9C4C0" stroke-width="2"/>
  <line x1="251" y1="30" x2="251" y2="104" stroke="#B9C4C0" stroke-width="2"/>
  <path d="M266 26 L277 28 Q289 40 289 56 L289 66 L266 66 Z" fill="{VIDRIO}"/>
  {_brillo(267, 28, 34)}
  <rect x="246" y="20" width="40" height="6" rx="2" fill="#263238"/>
  <text x="266" y="25" font-family="Arial" font-size="5" font-weight="700" fill="{NARANJA}"
        text-anchor="middle">SAO</text>
  <rect x="4" y="110" width="292" height="8" rx="4" fill="#2B3236"/>
  <ellipse cx="288" cy="94" rx="4" ry="6" fill="#FFF3B0" stroke="#E0B800"/>
  <rect x="9" y="88" width="4" height="10" rx="2" fill="#E53935"/>
  {_rueda(62, 116, 16)}
  {_rueda(222, 116, 16)}
</svg>"""


def _edificios(opacidad: float) -> str:
    bloques = [(40, 70), (90, 110), (120, 85), (170, 130), (215, 95), (300, 120), (340, 75),
               (380, 140), (430, 90), (520, 115), (560, 80), (600, 150), (650, 100),
               (760, 125), (800, 90), (840, 140), (890, 105), (980, 120), (1020, 85),
               (1060, 145), (1110, 95), (1200, 125), (1240, 80), (1280, 135), (1330, 100),
               (1420, 120), (1460, 90), (1500, 140), (1550, 105)]
    piezas = []
    for x, alto in bloques:
        y = 175 - alto
        piezas.append(f'<rect x="{x}" y="{y}" width="34" height="{alto}" rx="2"/>')
        for fila in range(y + 10, 165, 16):
            piezas.append(f'<rect x="{x + 6}" y="{fila}" width="6" height="7" fill-opacity=".35" '
                          f'fill="#FFFFFF"/><rect x="{x + 21}" y="{fila}" width="6" height="7" '
                          f'fill-opacity=".35" fill="#FFFFFF"/>')
    return f'<g fill="#FFFFFF" fill-opacity="{opacidad}">{"".join(piezas)}</g>'


def _arboles() -> str:
    return "".join(
        f'<g><rect x="{x - 2}" y="168" width="4" height="14" fill="#5D4037"/>'
        f'<circle cx="{x}" cy="162" r="{r}" fill="{c}"/></g>'
        for x, r, c in [(20, 11, "#2E7D32"), (250, 13, "#388E3C"), (470, 10, "#43A047"),
                        (700, 12, "#2E7D32"), (930, 11, "#388E3C"), (1160, 13, "#43A047"),
                        (1390, 10, "#2E7D32"), (1580, 12, "#388E3C")])


def paisaje(opacidad: float = 1.0) -> str:
    """Montañas, ciudad, viaducto del metro y vía (1600 × 240)."""
    pilares = "".join(f'<rect x="{x}" y="128" width="14" height="50" fill="#E8EEEB" '
                      f'fill-opacity=".55"/>' for x in range(60, 1600, 180))
    rayas = "".join(f'<rect x="{x}" y="214" width="46" height="5" rx="2" fill="{AMARILLO}"/>'
                    for x in range(10, 1600, 110))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 240"
     preserveAspectRatio="xMidYMax slice" opacity="{opacidad}">
  <path d="M0 120 Q120 40 260 95 T540 70 T820 100 T1100 55 T1380 90 T1600 60 V240 H0 Z"
        fill="#0B3F20" fill-opacity=".45"/>
  <path d="M0 150 Q160 90 330 135 T700 120 T1050 140 T1400 110 T1600 130 V240 H0 Z"
        fill="#0E5A2C" fill-opacity=".5"/>
  {_edificios(.13)}
  <rect x="0" y="116" width="1600" height="14" fill="#E8EEEB" fill-opacity=".6"/>
  <rect x="0" y="112" width="1600" height="4" fill="#FFFFFF" fill-opacity=".5"/>
  {pilares}
  {_arboles()}
  <rect x="0" y="182" width="1600" height="58" fill="#2C3631"/>
  <rect x="0" y="180" width="1600" height="5" fill="#9EA9A4"/>
  {rayas}
</svg>"""


def fondo_pagina() -> str:
    """Fondo suave para toda la página: montañas y ciudad en tonos claros."""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 260" preserveAspectRatio="xMidYMax slice">
  <g opacity=".10">
    <path d="M0 140 Q160 70 330 120 T700 100 T1050 125 T1400 90 T1600 115 V260 H0 Z" fill="{VERDE}"/>
    <g fill="{VERDE}">
      {''.join(f'<rect x="{x}" y="{200 - h}" width="40" height="{h}" rx="3"/>'
               for x, h in [(60, 90), (120, 130), (180, 70), (420, 120), (480, 80),
                            (900, 110), (960, 150), (1020, 90), (1300, 120), (1360, 75),
                            (1420, 140)])}
    </g>
    <rect x="0" y="200" width="1600" height="60" fill="#33413A"/>
  </g>
</svg>"""


# ── Operadores SAO (caricatura animada) ───────────────────────────────────────

CAMISA = "#C2D89F"
CAMISA_SOMBRA = "#9FBA7B"
PANTALON = "#2F5140"


def _tono(color: str, factor: float) -> str:
    """Aclara (factor > 1) u oscurece (factor < 1) un color #RRGGBB."""
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    if factor >= 1:
        r, g, b = (int(c + (255 - c) * (factor - 1)) for c in (r, g, b))
    else:
        r, g, b = (int(c * factor) for c in (r, g, b))
    return f"#{min(r, 255):02X}{min(g, 255):02X}{min(b, 255):02X}"


def _n(v: float) -> str:
    return f"{v:.2f}".rstrip("0").rstrip(".")


def _defs_operadores(personas: list[dict]) -> str:
    propios = ""
    for i, p in enumerate(personas):
        piel, pelo, iris = p["piel"], p["pelo"], p["iris"]
        propios += f"""
    <radialGradient id="piel{i}" cx=".38" cy=".34" r=".75">
      <stop offset="0" stop-color="{_tono(piel, 1.3)}"/>
      <stop offset=".6" stop-color="{piel}"/>
      <stop offset="1" stop-color="{_tono(piel, .78)}"/>
    </radialGradient>
    <linearGradient id="pielL{i}" x1="0" x2="1">
      <stop offset="0" stop-color="{_tono(piel, 1.22)}"/>
      <stop offset=".55" stop-color="{piel}"/>
      <stop offset="1" stop-color="{_tono(piel, .78)}"/>
    </linearGradient>
    <linearGradient id="pelo{i}" x1=".2" y1="0" x2=".7" y2="1">
      <stop offset="0" stop-color="{_tono(pelo, 1.55)}"/>
      <stop offset=".35" stop-color="{_tono(pelo, 1.12)}"/>
      <stop offset="1" stop-color="{_tono(pelo, .6)}"/>
    </linearGradient>
    <radialGradient id="iris{i}" cx=".5" cy=".38" r=".6">
      <stop offset="0" stop-color="{_tono(iris, 1.5)}"/>
      <stop offset=".7" stop-color="{iris}"/>
      <stop offset="1" stop-color="{_tono(iris, .5)}"/>
    </radialGradient>
    <clipPath id="cara{i}"><path d="{CARA}"/></clipPath>
    <clipPath id="torso{i}"><path d="{_torso(p.get('mujer', False))}"/></clipPath>"""
    return f"""<defs>
    <linearGradient id="camisa" x1="0" x2="1">
      <stop offset="0" stop-color="{_tono(CAMISA, 1.32)}"/>
      <stop offset=".4" stop-color="{CAMISA}"/>
      <stop offset="1" stop-color="{_tono(CAMISA, .76)}"/>
    </linearGradient>
    <linearGradient id="pantalon" x1="0" x2="1">
      <stop offset="0" stop-color="{_tono(PANTALON, 1.45)}"/>
      <stop offset=".5" stop-color="{PANTALON}"/>
      <stop offset="1" stop-color="{_tono(PANTALON, .6)}"/>
    </linearGradient>
    <linearGradient id="zapato" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#5C5C5C"/><stop offset="1" stop-color="#101010"/>
    </linearGradient>
    <radialGradient id="blanco" cx=".45" cy=".35" r=".7">
      <stop offset="0" stop-color="#FFFFFF"/><stop offset="1" stop-color="#D8DFE4"/>
    </radialGradient>
    <linearGradient id="labio" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#E0928A"/><stop offset="1" stop-color="#C46660"/>
    </linearGradient>
    <linearGradient id="carroceria" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#FFFFFF"/><stop offset=".7" stop-color="#F1F4F3"/>
      <stop offset="1" stop-color="#D3DBD8"/>
    </linearGradient>
    <linearGradient id="vidrio" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#3E5560"/><stop offset="1" stop-color="{VIDRIO}"/>
    </linearGradient>
    <linearGradient id="franja" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{_tono(VERDE, 1.3)}"/><stop offset="1" stop-color="{_tono(VERDE, .75)}"/>
    </linearGradient>
    <filter id="sombraOp" x="-30%" y="-10%" width="160%" height="125%">
      <feDropShadow dx="2" dy="4" stdDeviation="3" flood-color="#0B2E1A" flood-opacity=".25"/>
    </filter>
    <filter id="difuso"><feGaussianBlur stdDeviation="2.5"/></filter>
    <filter id="suave" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2.6"/></filter>
    <filter id="suaveMin" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation=".9"/></filter>{propios}
  </defs>"""


# Cabeza ovalada, más angosta en la barbilla (centro x = 0)
CARA = "M-14 34 C-14.5 21 -7.5 17.5 0 17.5 C7.5 17.5 14.5 21 14 34 C13.6 44 8.5 52 0 53.5 C-8.5 52 -13.6 44 -14 34 Z"


def _torso(mujer: bool) -> str:
    """Camisa: hombros redondeados, pecho, cintura y cadera."""
    if mujer:
        return ("M-6 61 C-12 62 -19 63 -21 68 C-22.5 74 -21 84 -18 92 C-16 100 -16.5 106 -18 114 "
                "L18 114 C16.5 106 16 100 18 92 C21 84 22.5 74 21 68 C19 63 12 62 6 61 Z")
    return ("M-6 60 C-13 61 -22 62 -24.5 68 C-26 75 -24 88 -21 98 C-20 104 -20 109 -20.5 114 "
            "L20.5 114 C20 109 20 104 21 98 C24 88 26 75 24.5 68 C22 62 13 61 6 60 Z")


_IDS = [0]


def _nuevo_id(prefijo: str) -> str:
    _IDS[0] += 1
    return f"{prefijo}{_IDS[0]}"


def _curva_cerrada(puntos: list) -> str:
    """Curva suave (Catmull-Rom) que pasa por todos los puntos y se cierra."""
    n = len(puntos)
    d = f"M{_n(puntos[0][0])} {_n(puntos[0][1])} "
    for k in range(n):
        p0, p1, p2, p3 = (puntos[(k + j) % n] for j in (-1, 0, 1, 2))
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += (f"C{_n(c1[0])} {_n(c1[1])} {_n(c2[0])} {_n(c2[1])} "
              f"{_n(p2[0])} {_n(p2[1])} ")
    return d + "Z"


def _tubo(eje: list, anchos: list) -> str:
    """Contorno curvo y continuo alrededor de una línea (brazo, pierna, dedo):
    `anchos` es el medio ancho en cada punto del eje; los extremos quedan redondeados."""
    import math
    n = len(eje)
    normales, direcciones = [], []
    for k in range(n):
        a = eje[max(k - 1, 0)]
        b = eje[min(k + 1, n - 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        largo = math.hypot(dx, dy) or 1
        direcciones.append((dx / largo, dy / largo))
        normales.append((-dy / largo, dx / largo))
    izq = [(p[0] + nx * w, p[1] + ny * w) for p, (nx, ny), w in zip(eje, normales, anchos)]
    der = [(p[0] - nx * w, p[1] - ny * w) for p, (nx, ny), w in zip(eje, normales, anchos)]
    fin = (eje[-1][0] + direcciones[-1][0] * anchos[-1] * .95,
           eje[-1][1] + direcciones[-1][1] * anchos[-1] * .95)
    inicio = (eje[0][0] - direcciones[0][0] * anchos[0] * .95,
              eje[0][1] - direcciones[0][1] * anchos[0] * .95)
    return _curva_cerrada(izq + [fin] + der[::-1] + [inicio])


def _pieza(d: str, relleno: str, borde: str, sombra: str, grosor: float = 4.5) -> str:
    """Forma con volumen: relleno, bordes oscurecidos (se ve redonda) y contorno fino."""
    clip = _nuevo_id("pz")
    return (f'<clipPath id="{clip}"><path d="{d}"/></clipPath>'
            f'<path d="{d}" fill="{relleno}"/>'
            f'<g clip-path="url(#{clip})">'
            f'<path d="{d}" fill="none" stroke="{sombra}" stroke-width="{grosor}" opacity=".55" '
            f'transform="translate(1.3 .4)" filter="url(#suave)"/>'
            f'<path d="{d}" fill="none" stroke="#FFFFFF" stroke-width="{grosor * .6}" opacity=".35" '
            f'transform="translate(-2.4 -.6)" filter="url(#suaveMin)"/></g>'
            f'<path d="{d}" fill="none" stroke="{borde}" stroke-width=".8"/>')


def _brazo_abajo(lado: int, hx: float, i: int, piel: str) -> str:
    """Brazo relajado junto al cuerpo (lado 1 = derecha del dibujo, -1 = izquierda)."""
    s = lado
    piel_d = _tubo([(s * (hx + 1.5), 74), (s * (hx + 4.6), 87), (s * (hx + 5.6), 99),
                    (s * (hx + 5.4), 110), (s * (hx + 5), 118)],
                   [5.2, 4.8, 4.4, 3.8, 3.2])
    mano = _tubo([(s * (hx + 5), 117), (s * (hx + 5.4), 122), (s * (hx + 5.2), 127),
                  (s * (hx + 4.6), 131)], [3.1, 3.7, 3.4, 2.4])
    pulgar = _tubo([(s * (hx + 3), 119), (s * (hx + 1.8), 124.5)], [1.5, 1.1])
    manga = _tubo([(s * (hx - 1), 66.5), (s * (hx + 2.8), 75), (s * (hx + 4.6), 86.5)],
                  [6.8, 6.9, 6.6])
    bp = _tono(piel, .68)
    return (_pieza(piel_d, f"url(#pielL{i})", bp, _tono(piel, .55))
            + _pieza(pulgar, f"url(#piel{i})", bp, _tono(piel, .55), 2)
            + _pieza(mano, f"url(#piel{i})", bp, _tono(piel, .55), 3)
            + f'<path d="M{s * (hx - 1)} {93} Q{s * (hx + 5)} {95.5} {s * (hx + 11)} {92}" '
              f'stroke="#000" stroke-opacity=".12" stroke-width="2" fill="none" filter="url(#suaveMin)"/>'
            + _pieza(manga, "url(#camisa)", _tono(CAMISA_SOMBRA, .7), _tono(CAMISA_SOMBRA, .6), 5))


def _brazo_saludo(hx: float, i: int, piel: str) -> str:
    """Brazo izquierdo levantado, con la mano abierta saludando."""
    hombro, codo, muneca = (-hx + 1, 69), (-hx - 13, 54), (-hx - 16, 33)
    piel_d = _tubo([(-hx - 6, 62), codo, (-hx - 15, 44), muneca], [5.0, 4.6, 4.1, 3.5])
    manga = _tubo([(-hx + 2, 68), (-hx - 3, 63.5), (-hx - 8, 59.5)], [6.8, 6.8, 6.4])
    wx, wy = muneca
    palma = _tubo([(wx, wy + 1), (wx - .2, wy - 4), (wx - .3, wy - 7)], [3.4, 4.4, 4.2])
    bp, sp = _tono(piel, .68), _tono(piel, .55)
    dedos = "".join(_pieza(_tubo([(wx + dx, wy - 8), (wx + dx * 1.25, wy - 8 - h * .55),
                                  (wx + dx * 1.4, wy - 8 - h)], [1.45, 1.35, 1.15]),
                           f"url(#pielL{i})", bp, sp, 1.4)
                    for dx, h in [(-3.1, 6.2), (-1.05, 7.6), (1.05, 7.2), (3.0, 5.8)])
    pulgar = _pieza(_tubo([(wx + 3.2, wy - 2), (wx + 6, wy - 5), (wx + 7.6, wy - 8)],
                          [1.9, 1.6, 1.3]), f"url(#pielL{i})", bp, sp, 1.6)
    return (_pieza(piel_d, f"url(#pielL{i})", bp, sp)
            + dedos + _pieza(palma, f"url(#piel{i})", bp, sp, 3) + pulgar
            + _pieza(manga, "url(#camisa)", _tono(CAMISA_SOMBRA, .7), _tono(CAMISA_SOMBRA, .6), 5))


def _ojo(cx: float, i: int) -> str:
    return f"""
    <g class="ojo">
      <path d="M{cx - 4} 36.2 Q{cx} 32.4 {cx + 4} 36.2 Q{cx} 39.6 {cx - 4} 36.2 Z" fill="url(#blanco)"/>
      <circle cx="{cx + .2}" cy="36" r="2.35" fill="url(#iris{i})"/>
      <circle cx="{cx + .2}" cy="36.1" r="1.1" fill="#16100C"/>
      <circle cx="{cx + 1}" cy="35.1" r=".75" fill="#FFFFFF"/>
      <path d="M{cx - 4.2} 36.1 Q{cx} 32 {cx + 4.2} 36.1" fill="none" stroke="#2A1A12"
            stroke-width="1.1" stroke-linecap="round"/>
      <path d="M{cx - 3} 38.2 Q{cx} 39.3 {cx + 3} 38.2" fill="none" stroke="#000" stroke-opacity=".12"
            stroke-width=".6"/>
    </g>"""


def _cabeza(i: int, p: dict) -> str:
    piel, pelo = p["piel"], p["pelo"]
    borde = _tono(piel, .72)
    return f"""
    <path d="M-13.2 33 Q-17.5 33 -14.6 41 Q-13 45 -11 43" fill="url(#piel{i})" stroke="{borde}" stroke-width=".7"/>
    <path d="M13.2 33 Q17.5 33 14.6 41 Q13 45 11 43" fill="url(#piel{i})" stroke="{borde}" stroke-width=".7"/>
    <path d="{CARA}" fill="url(#piel{i})"/>
    <g clip-path="url(#cara{i})">
      <ellipse cx="11" cy="42" rx="7" ry="15" fill="{_tono(piel, .68)}" opacity=".5" filter="url(#suave)"/>
      <ellipse cx="0" cy="56" rx="14" ry="5" fill="{_tono(piel, .7)}" opacity=".5" filter="url(#suave)"/>
      <ellipse cx="-6" cy="27" rx="6" ry="4" fill="#FFFFFF" opacity=".3" filter="url(#suave)"/>
      <ellipse cx="-9" cy="43" rx="3.6" ry="2.4" fill="#E2726C" opacity=".32" filter="url(#suaveMin)"/>
      <ellipse cx="9" cy="43" rx="3.6" ry="2.4" fill="#E2726C" opacity=".32" filter="url(#suaveMin)"/>
    </g>
    <path d="{CARA}" fill="none" stroke="{borde}" stroke-width=".7" opacity=".7"/>
    {_ojo(-5.6, i)}
    {_ojo(5.6, i)}
    <path d="M-9.8 31.4 Q-6 29.4 -2.2 30.8 M2.2 30.8 Q6 29.4 9.8 31.4" stroke="{_tono(pelo, .85)}"
          stroke-width="{1.1 if p.get('mujer') else 1.5}" fill="none" stroke-linecap="round"/>
    <path d="M-.6 38 Q-1.2 42.5 -2.4 43.4 Q0 44.6 2.2 43.6" stroke="{_tono(piel, .66)}" stroke-width=".9"
          fill="none" stroke-linecap="round" opacity=".8"/>
    <ellipse cx="-.4" cy="41.6" rx=".9" ry="1.8" fill="#FFFFFF" opacity=".3"/>
    <path d="M-4.6 47.4 Q0 50.6 4.6 47.4 Q0 49 -4.6 47.4 Z" fill="url(#labio)"/>
    <path d="M-4.8 47.2 Q0 50.8 4.8 47.2" stroke="#93453F" stroke-width=".9" fill="none" stroke-linecap="round"/>
    <path d="M-1.6 51.6 Q0 52.3 1.6 51.6" stroke="{_tono(piel, .7)}" stroke-width=".6" fill="none" opacity=".6"/>"""


def _pelo_corto(i: int, pelo: str) -> str:
    return f"""
    <path d="M-14.6 36 Q-17.5 19 -5 15.5 Q8 12.5 14.5 22 Q16.4 27 14.6 36 Q13.6 27 9 24.6
             Q2 26.5 -5 23.8 Q-11 25.5 -12.4 30 Q-13.4 32.6 -14.6 36 Z"
          fill="url(#pelo{i})" stroke="{_tono(pelo, .55)}" stroke-width=".7"/>
    <path d="M-10 21 Q-3 16.6 5 17.4 M-6 23.6 Q2 20 10 21.6" stroke="{_tono(pelo, 1.9)}"
          stroke-opacity=".5" stroke-width="1.4" fill="none" stroke-linecap="round" filter="url(#suaveMin)"/>"""


def _pelo_largo_atras(i: int, pelo: str) -> str:
    return f"""
    <path d="M-16 32 Q-19 13 0 12.5 Q19 13 16 32 L19 66 Q21 84 16 94 Q8 98 0 96 Q-8 98 -16 94
             Q-21 84 -19 66 Z" fill="url(#pelo{i})" stroke="{_tono(pelo, .6)}" stroke-width=".7"/>
    <path d="M-15 50 Q-17 72 -13 90 M15 50 Q17 72 13 90 M-9 70 Q-10 82 -8 92 M9 70 Q10 82 8 92"
          stroke="{_tono(pelo, .62)}" stroke-opacity=".45" stroke-width="1.4" fill="none" stroke-linecap="round"/>"""


def _pelo_largo_frente(i: int, pelo: str) -> str:
    claro = _tono(pelo, 1.75)
    return f"""
    <path d="M-15.4 44 Q-18 16 0 14.4 Q18 16 15.4 44 Q15 30 8 23 Q3 20 .6 17.4 Q-2 21 -7.5 24
             Q-14 29 -15.4 44 Z" fill="url(#pelo{i})" stroke="{_tono(pelo, .6)}" stroke-width=".7"/>
    <path d="M-15.2 40 C-15.6 56 -14.6 70 -11.5 83 C-16 83.5 -20.5 79 -22 70 C-23 60 -20.5 49 -18.8 41 Z
             M15.2 40 C15.6 56 14.6 70 11.5 83 C16 83.5 20.5 79 22 70 C23 60 20.5 49 18.8 41 Z"
          fill="url(#pelo{i})" stroke="{_tono(pelo, .6)}" stroke-width=".7"/>
    <path d="M-17.5 48 C-18.5 60 -17.5 72 -14.5 80 M17.5 48 C18.5 60 17.5 72 14.5 80"
          stroke="{claro}" stroke-opacity=".35" stroke-width="1.4" fill="none" stroke-linecap="round"
          filter="url(#suaveMin)"/>
    <path d="M-3 17.6 Q-11 21 -13.4 33 M3.4 17.6 Q11.4 21 13.4 33" stroke="{claro}" stroke-opacity=".6"
          stroke-width="1.6" fill="none" stroke-linecap="round" filter="url(#suaveMin)"/>
"""


def _operador(x: float, i: int, p: dict, retraso: float) -> str:
    """Operador(a) SAO de proporciones naturales, con luz desde arriba a la izquierda."""
    piel, gesto, mujer = p["piel"], p["gesto"], p.get("mujer", False)
    hx = 19 if mujer else 21.5         # ancho de hombros
    cad = 16.5 if mujer else 18        # ancho de cadera
    brazo_der = _brazo_abajo(1, hx, i, piel)
    if gesto == "saludo":
        brazo_izq = (f'<g class="brazo-saludo" style="transform-origin:{-hx}px 67px">'
                     f'{_brazo_saludo(hx, i, piel)}</g>')
    else:
        brazo_izq = _brazo_abajo(-1, hx, i, piel)
    piernas = ""
    for s_ in (-1, 1):
        eje = [(s_ * cad * .52, 114), (s_ * 9.6, 134), (s_ * 8.6, 154), (s_ * 8.2, 170),
               (s_ * 7.6, 187)]
        piernas += _pieza(_tubo(eje, [9.2, 8.4, 7.4, 7.0, 6.4]), "url(#pantalon)",
                          _tono(PANTALON, .5), "#0E1F17", 5)
        piernas += (f'<path d="M{s_ * 4.5} 156 Q{s_ * 8.6} 158.5 {s_ * 12.5} 155.5" stroke="#000" '
                    f'stroke-opacity=".18" stroke-width="1" fill="none"/>')
    piernas += ('<path d="M0 116 Q-.6 124 -1.2 130" stroke="#0E1F17" stroke-opacity=".5" '
                'stroke-width="1" fill="none"/>')
    zapatos = ""
    for sx, d in [(-7.4, -1), (7.4, 1)]:
        zapato = (f"M{sx - 5.2} 186 L{sx + 5.2} 186 C{sx + 6 + d} 189 {sx + 7.6 + d * 1.6} 191.5 "
                  f"{sx + 7.8 + d * 1.6} 194.8 C{sx + 7.8 + d * 1.6} 197.6 {sx + 4.4 + d} 198.6 {sx + d} 198.6 "
                  f"C{sx - 4.4 + d} 198.6 {sx - 7.8 + d * 1.6} 197.6 {sx - 7.8 + d * 1.6} 194.8 "
                  f"C{sx - 7.6 + d * 1.6} 191.5 {sx - 6 + d} 189 {sx - 5.2} 186 Z")
        zapatos += _pieza(zapato, "url(#zapato)", "#000", "#000", 3)
        zapatos += (f'<ellipse cx="{sx + d * 1.6 - 1.6}" cy="192.4" rx="3.8" ry="1.3" fill="#FFFFFF" '
                    f'opacity=".38" filter="url(#suaveMin)"/>')
    torso = _torso(mujer)
    contorno = _tono(CAMISA_SOMBRA, .7)
    pelo_atras = _pelo_largo_atras(i, p["pelo"]) if mujer else ""
    pelo_frente = _pelo_largo_frente(i, p["pelo"]) if mujer else _pelo_corto(i, p["pelo"])
    return f"""
  <g transform="translate({x} 0)">
   <ellipse cx="2" cy="198" rx="28" ry="5" fill="#000" opacity=".25" filter="url(#difuso)"/>
   <g class="operador" style="animation-delay:{retraso}s" filter="url(#sombraOp)">
    {pelo_atras}
    {piernas}
    {zapatos}
    {brazo_izq}
    {brazo_der}
    <path d="M-5.6 46 C-5.6 53 -6 57.5 -9.5 61.5 Q0 66 9.5 61.5 C6 57.5 5.6 53 5.6 46 Z" fill="url(#pielL{i})"/>
    <ellipse cx="0" cy="55" rx="4.6" ry="3.4" fill="{_tono(piel, .58)}" opacity=".45" filter="url(#suaveMin)"/>
    <path d="{torso}" fill="url(#camisa)" stroke="{contorno}" stroke-width="1"/>
    <g clip-path="url(#torso{i})">
      <path d="M{hx - 4} 70 Q{hx + 2} 92 {cad - 2} 114" stroke="#000" stroke-opacity=".18"
            stroke-width="9" fill="none" filter="url(#suave)"/>
      <path d="M{-hx + 5} 70 Q{-hx + 2} 90 {-cad + 4} 112" stroke="#FFFFFF" stroke-opacity=".45"
            stroke-width="5" fill="none" filter="url(#suave)"/>
      <path d="M-14 99 Q-6 102 -1 98 M4 101 Q10 98 15 101" stroke="{CAMISA_SOMBRA}"
            stroke-width="1" fill="none" opacity=".8"/>
      {'<path d="M-13 82 Q-7 88 -2 84 M2 84 Q7 88 13 82" stroke="#000" stroke-opacity=".1" stroke-width="2" fill="none" filter="url(#suaveMin)"/>' if mujer else ''}
    </g>
    <path d="M-7 60 L0 71 L-1.5 60.5 Z M7 60 L0 71 L1.5 60.5 Z" fill="{_tono(CAMISA, 1.15)}"
          stroke="{contorno}" stroke-width=".7"/>
    <line x1="0" y1="71" x2="0" y2="112" stroke="{_tono(CAMISA_SOMBRA, .85)}" stroke-width="1"/>
    <g fill="#FFFFFF" stroke="{CAMISA_SOMBRA}" stroke-width=".4">
      <circle cx="0" cy="79" r="1.1"/><circle cx="0" cy="90" r="1.1"/><circle cx="0" cy="101" r="1.1"/>
    </g>
    <path d="M5 78 H14 V86 Q9.5 88 5 86 Z" fill="{CAMISA_SOMBRA}" opacity=".55"/>
    <rect x="6.5" y="75" width="6" height="3.6" rx=".8" fill="#E53935"/>
    <rect x="-15" y="73" width="6" height="7.5" rx="1.4" fill="#2E7D32"/>
    <rect x="-15" y="75.6" width="6" height="1.8" fill="{AMARILLO}"/>
    <path d="M{-cad - 2.5} 110 Q0 113 {cad + 2.5} 110 L{cad + 2.5} 116 Q0 119 {-cad - 2.5} 116 Z" fill="#232323"/>
    <path d="M{-cad - 2.5} 110.6 Q0 113.6 {cad + 2.5} 110.6" stroke="#FFFFFF" stroke-opacity=".18" fill="none"/>
    <rect x="-3.5" y="110.6" width="7" height="6.6" rx="1" fill="#CFCFCF" stroke="#8A8A8A" stroke-width=".7"/>
    {_cabeza(i, p)}
    {pelo_frente}
   </g>
  </g>"""


def operadores() -> str:
    """Tres operadores SAO frente a una buseta: dos con los brazos abajo y una operadora
    saludando (380 × 214)."""
    _IDS[0] = 0
    ventanas = "".join(
        f'<rect x="{x}" y="22" width="52" height="42" rx="6" fill="url(#vidrio)" '
        f'stroke="#B9C4C0" stroke-width="1.5"/>'
        f'<path d="M{x + 8} 58 L{x + 22} 28" stroke="#FFFFFF" stroke-opacity=".25" '
        f'stroke-width="6" stroke-linecap="round"/>'
        for x in (16, 76, 136, 196))
    personas = [
        {"piel": "#C68B5B", "pelo": "#2B1B12", "iris": "#6B4226", "gesto": "abajo", "x": 78},
        {"piel": "#E8B48E", "pelo": "#15100E", "iris": "#4E3424", "gesto": "saludo", "x": 180,
         "mujer": True},
        {"piel": "#B97A4E", "pelo": "#1E1410", "iris": "#5A3A22", "gesto": "abajo", "x": 282},
    ]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 380 214">
  {_defs_operadores(personas)}
  <style>
    .operador {{ animation: respirar 3.2s ease-in-out infinite; }}
    .brazo-pulgar {{ animation: pulgar 2.4s ease-in-out infinite; }}
    .brazo-saludo {{ animation: saludo 1.4s ease-in-out infinite; }}
    .ojo {{ animation: parpadeo 4.5s infinite; transform-box: fill-box; transform-origin: center; }}
    @keyframes respirar {{ 0%,100% {{ transform: translateY(0) }} 50% {{ transform: translateY(-1.5px) }} }}
    @keyframes pulgar {{ 0%,100% {{ transform: rotate(0deg) }} 50% {{ transform: rotate(-6deg) }} }}
    @keyframes saludo {{ 0%,100% {{ transform: rotate(-5deg) }} 50% {{ transform: rotate(9deg) }} }}
    @keyframes parpadeo {{ 0%,92%,100% {{ transform: scaleY(1) }} 95% {{ transform: scaleY(.1) }} }}
    @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}
  </style>
  <ellipse cx="190" cy="204" rx="186" ry="7" fill="#000" opacity=".16" filter="url(#difuso)"/>
  <g>
    <rect x="0" y="8" width="380" height="182" rx="14" fill="url(#carroceria)"
          stroke="#B9C4C0" stroke-width="2"/>
    <rect x="4" y="11" width="372" height="4" rx="2" fill="#FFFFFF" opacity=".9"/>
    {ventanas}
    <rect x="262" y="18" width="40" height="160" rx="5" fill="url(#vidrio)" opacity=".9"
          stroke="#B9C4C0" stroke-width="2"/>
    <line x1="282" y1="20" x2="282" y2="176" stroke="#B9C4C0" stroke-width="2"/>
    <rect x="266" y="22" width="32" height="70" rx="3" fill="#F4C430" opacity=".2"/>
    <rect x="0" y="98" width="380" height="9" fill="{AMARILLO}"/>
    <rect x="0" y="107" width="380" height="16" fill="url(#franja)"/>
    <rect x="0" y="107" width="380" height="2" fill="#FFFFFF" opacity=".25"/>
    <rect x="0" y="150" width="380" height="14" fill="{VERDE_CLARO}" opacity=".55"/>
    {_rueda(350, 190, 22)}
  </g>
  <rect x="0" y="198" width="380" height="16" rx="3" fill="#DCE4DF"/>
  <rect x="0" y="198" width="380" height="2" fill="#FFFFFF" opacity=".7"/>
  {''.join(_operador(p["x"], i, p, i * .4) for i, p in enumerate(personas))}
</svg>"""
