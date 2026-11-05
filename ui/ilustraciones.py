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


def _brazo(trazo: str, mano: str, clase: str, origen: str) -> str:
    return f"""
    <g class="{clase}" style="transform-origin:{origen}">
      <path d="{trazo}" fill="none" stroke="{CAMISA}" stroke-width="13" stroke-linecap="round"
            stroke-linejoin="round"/>
      <path d="{trazo}" fill="none" stroke="{CAMISA_SOMBRA}" stroke-width="13" stroke-opacity=".25"
            stroke-linecap="round" stroke-dasharray="0 999"/>
      {mano}
    </g>"""


def _operador(x: float, piel: str, pelo: str, gesto: str, retraso: float) -> str:
    """Operador de pie con el uniforme SAO. gesto: 'pulgar' o 'saludo'."""
    pulgar = (f'<circle cx="36" cy="90" r="6.5" fill="{piel}"/>'
              f'<rect x="33" y="76" width="6" height="12" rx="3" fill="{piel}"/>')
    brazo_der = _brazo("M22 80 L31 110 L36 92", pulgar, "brazo-pulgar", "22px 80px")
    if gesto == "saludo":
        palma = (f'<circle cx="-40" cy="30" r="8" fill="{piel}"/>'
                 + "".join(f'<rect x="{-46 + i * 4}" y="17" width="3.4" height="11" rx="1.7" '
                           f'fill="{piel}"/>' for i in range(4)))
        brazo_izq = _brazo("M-22 80 L-37 58 L-40 38", palma, "brazo-saludo", "-22px 80px")
    else:
        brazo_izq = _brazo("M-22 80 L-27 128", f'<circle cx="-27" cy="133" r="6" fill="{piel}"/>',
                           "", "0 0")
    return f"""
  <g transform="translate({x} 0)">
   <g class="operador" style="animation-delay:{retraso}s">
    <ellipse cx="0" cy="199" rx="30" ry="5" fill="#000" opacity=".12"/>
    <rect x="-17" y="128" width="15" height="68" rx="5" fill="{PANTALON}"/>
    <rect x="2" y="128" width="15" height="68" rx="5" fill="{PANTALON}"/>
    <ellipse cx="-11" cy="197" rx="11" ry="5" fill="#1C1C1C"/>
    <ellipse cx="11" cy="197" rx="11" ry="5" fill="#1C1C1C"/>
    {brazo_izq}
    <rect x="-6" y="60" width="12" height="16" fill="{piel}"/>
    <rect x="-25" y="72" width="50" height="62" rx="13" fill="{CAMISA}"/>
    <path d="M-25 110 Q0 116 25 110 L25 121 Q0 127 -25 121 Z" fill="{CAMISA_SOMBRA}" opacity=".35"/>
    <path d="M-9 72 L0 84 L-3 72 Z M9 72 L0 84 L3 72 Z" fill="{CAMISA_SOMBRA}"/>
    <line x1="0" y1="84" x2="0" y2="128" stroke="{CAMISA_SOMBRA}" stroke-width="1.5"/>
    <rect x="6" y="90" width="12" height="9" rx="2" fill="{CAMISA_SOMBRA}" opacity=".6"/>
    <rect x="8" y="86" width="8" height="5" rx="1" fill="#E53935"/>
    <rect x="-22" y="80" width="7" height="9" rx="1.5" fill="#2E7D32"/>
    <rect x="-22" y="83" width="7" height="2" fill="{AMARILLO}"/>
    <rect x="-25" y="126" width="50" height="7" fill="#262626"/>
    <rect x="-4" y="126" width="8" height="7" rx="1" fill="#B0B0B0"/>
    {brazo_der}
    <circle cx="-17" cy="46" r="4.5" fill="{piel}"/>
    <circle cx="17" cy="46" r="4.5" fill="{piel}"/>
    <circle cx="0" cy="44" r="18" fill="{piel}"/>
    <path d="M-18 42 Q-19 22 0 22 Q19 22 18 42 Q15 30 0 31 Q-14 30 -18 42 Z" fill="{pelo}"/>
    <path d="M-10 38 L-4 37 M4 37 L10 38" stroke="{pelo}" stroke-width="2" stroke-linecap="round"/>
    <circle class="ojo" cx="-7" cy="44" r="2.2" fill="#222"/>
    <circle class="ojo" cx="7" cy="44" r="2.2" fill="#222"/>
    <path d="M-8 52 Q0 59 8 52" fill="#FFFFFF" stroke="#5A2E1E" stroke-width="1.6"
          stroke-linecap="round"/>
    <circle cx="-11" cy="51" r="2.6" fill="#E57373" opacity=".25"/>
    <circle cx="11" cy="51" r="2.6" fill="#E57373" opacity=".25"/>
   </g>
  </g>"""


def operadores() -> str:
    """Tres operadores SAO frente a una buseta, con pulgar arriba y saludo (380 × 210)."""
    ventanas = "".join(f'<rect x="{x}" y="22" width="52" height="42" rx="6" fill="{VIDRIO}"/>'
                       for x in (16, 76, 136, 196))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 380 210">
  <style>
    .operador {{ animation: respirar 3.2s ease-in-out infinite; }}
    .brazo-pulgar {{ animation: pulgar 2.4s ease-in-out infinite; }}
    .brazo-saludo {{ animation: saludo 1.4s ease-in-out infinite; }}
    .ojo {{ animation: parpadeo 4.5s infinite; transform-box: fill-box; transform-origin: center; }}
    @keyframes respirar {{ 0%,100% {{ transform: translateY(0) }} 50% {{ transform: translateY(-2px) }} }}
    @keyframes pulgar {{ 0%,100% {{ transform: rotate(0deg) }} 50% {{ transform: rotate(-7deg) }} }}
    @keyframes saludo {{ 0%,100% {{ transform: rotate(-6deg) }} 50% {{ transform: rotate(10deg) }} }}
    @keyframes parpadeo {{ 0%,92%,100% {{ transform: scaleY(1) }} 95% {{ transform: scaleY(.1) }} }}
    @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}
  </style>
  <g opacity=".95">
    <rect x="0" y="8" width="380" height="182" rx="14" fill="#FFFFFF" stroke="#D5DDD9" stroke-width="2"/>
    {ventanas}
    <rect x="262" y="18" width="40" height="160" rx="5" fill="{VIDRIO}" opacity=".85"/>
    <rect x="266" y="22" width="32" height="70" rx="3" fill="#F4C430" opacity=".25"/>
    <rect x="0" y="98" width="380" height="9" fill="{AMARILLO}"/>
    <rect x="0" y="107" width="380" height="16" fill="{VERDE}"/>
    <rect x="0" y="150" width="380" height="14" fill="{VERDE_CLARO}" opacity=".55"/>
    <rect x="312" y="40" width="68" height="34" rx="4" fill="#ECEFF1"/>
    <text x="346" y="62" font-family="Arial" font-size="13" font-weight="800" fill="{VERDE}"
          text-anchor="middle">SAO</text>
    <circle cx="350" cy="190" r="26" fill="{LLANTA}"/>
    <circle cx="350" cy="190" r="12" fill="#CFD8DC"/>
  </g>
  <rect x="0" y="196" width="380" height="14" fill="#E6ECE8"/>
  {_operador(78, "#C68B5B", "#2B1B12", "pulgar", 0)}
  {_operador(176, "#D9A27A", "#3A2416", "saludo", .4)}
  {_operador(274, "#B97A4E", "#1E1410", "pulgar", .8)}
</svg>"""
