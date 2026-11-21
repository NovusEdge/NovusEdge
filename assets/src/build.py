"""Generate header.svg, stack.svg and footer.svg into assets/.

GitHub serves README SVGs through <img>, which blocks every external fetch,
so each file carries its own font subset as a data URI. Rerun after changing
any text here: glyphs missing from the subset fall back to the system font.

    uv run --with fonttools python assets/src/build.py
"""

import base64
from html import escape
import io
import urllib.request
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ASSETS = Path(__file__).resolve().parent.parent
CACHE = Path(__file__).resolve().parent / ".fonts"
GF = "https://raw.githubusercontent.com/google/fonts/main/ofl"
SOURCES = {
    "Barlow-Regular": f"{GF}/barlow/Barlow-Regular.ttf",
    "Barlow-Medium": f"{GF}/barlow/Barlow-Medium.ttf",
    "Barlow-SemiBold": f"{GF}/barlow/Barlow-SemiBold.ttf",
    "JetBrainsMono": f"{GF}/jetbrainsmono/JetBrainsMono%5Bwght%5D.ttf",
}

# GitHub's own fg/muted/border tokens, so the graphics sit in either theme.
# The media query follows the OS scheme, which is GitHub's default setting.
PALETTE = """
  :root { --fg:#1f2328; --muted:#59636e; --line:#d1d9e0; --signal:#b4590b; }
  @media (prefers-color-scheme: dark) {
    :root { --fg:#e6edf3; --muted:#9198a1; --line:#3d444d; --signal:#f2a33a; }
  }
"""


def font_face(family: str, source: str, text: str, weight: int) -> str:
    path = CACHE / f"{source}.ttf"
    if not path.exists():
        CACHE.mkdir(exist_ok=True)
        urllib.request.urlretrieve(SOURCES[source], path)
    font = TTFont(path)
    if "fvar" in font:
        font = instancer.instantiateVariableFont(font, {"wght": weight})
    options = subset.Options()
    options.flavor = "woff"
    options.layout_features = ["kern", "liga"]
    subsetter = subset.Subsetter(options)
    subsetter.populate(text=text)
    subsetter.subset(font)
    buf = io.BytesIO()
    font.flavor = "woff"
    font.save(buf)
    data = base64.b64encode(buf.getvalue()).decode()
    return (
        f"@font-face {{ font-family:'{family}'; font-weight:{weight}; "
        f"src:url(data:font/woff;base64,{data}) format('woff'); }}"
    )


def fonts(texts: dict[tuple[str, str, int], str]) -> str:
    return "\n".join(font_face(fam, src, txt, w) for (fam, src, w), txt in texts.items())


def svg(w: int, h: int, label: str, style: str, body: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img" aria-label="{escape(label)}">\n'
        f"<style>{style}</style>\n{body}\n</svg>\n"
    )


# 20x20 line icons, drawn from the box's icon origin.
ICONS = {
    "agent": "M3 5.5L8.5 10L3 14.5M11 15H17",
    "stoat": "M2 3.5H18V14H2ZM6 7H14V10.5H6ZM10 14V17M6.5 17H13.5",
    "midwire": "M10 4.5a5.5 5.5 0 1 0 .01 0M10 9a1 1 0 1 0 .01 0M10 1V3M10 17V19M1 10H3M17 10H19",
    "docket": "M3 4.5H5M8 4.5H17M3 10H5M8 10H17M3 15.5H5M8 15.5H12.5",
}


def header() -> str:
    W, H = 800, 300
    # Clockwise loop through the four box centres. The track runs under the
    # boxes and is masked out there, so only the edges between them show.
    bw, bh = 200, 64
    cx = {"agent": 268, "stoat": 628, "midwire": 628, "docket": 268}
    cy = {"agent": 82, "stoat": 82, "midwire": 218, "docket": 218}
    roles = {
        "agent": "your coding agent",
        "stoat": "runs it in a VM",
        "midwire": "checks what changed",
        "docket": "records the decision",
    }
    # One (payload, gloss) per edge, in loop order starting at the agent.
    signals = [
        ("acts", "a tool call"),
        ("effect", "what it did"),
        ("verdict", "landed or not"),
        ("context", "what was decided"),
    ]
    inlet = ("flocc", "issue", "from Linear")
    centre = "closed loop"
    top, right = cx["stoat"] - cx["agent"], cy["midwire"] - cy["stoat"]
    perimeter = 2 * (top + right)
    period = 6.4

    # The pulse is dashes sharing one animation; --o starts each one further
    # along so they end at the same point and read as one comet with a fading
    # tail. A pattern must sum to the perimeter or the dash repeats on the
    # loop, and must not open with a zero-length dash: a round cap draws that
    # as a dot at the tail's tip.
    trail = [(96, 0.12, 1.5, ""), (52, 0.35, 2, ""), (22, 1.0, 2.75, ""), (22, 0.55, 7, ' filter="url(#bloom)"')]
    tail = trail[0][0]
    head_len = trail[2][0]
    pulses = "".join(
        f'<path class="pulse" d="LOOP" stroke-opacity="{op}" stroke-width="{sw}"{extra} '
        f'stroke-dasharray="{n} {perimeter - n}" style="--o:{n - tail}px"/>'
        for n, op, sw, extra in trail
    )

    def pct(d: float) -> str:
        return f"{100 * (d % perimeter) / perimeter:.2f}%"

    def lit(name: str, a: float, b: float, off: str, on: str) -> str:
        # On while the comet's head is between track distances a and b.
        a, b = a - tail, b - (tail - head_len)
        if 0 <= a - 1 and b + 8 <= perimeter:
            return f"@keyframes {name} {{ 0%,{pct(a - 1)},{pct(b + 8)},100% {off} {pct(a + 4)},{pct(b)} {on} }}"
        # The span straddles the loop's start, so it wraps past 100%.
        return f"@keyframes {name} {{ {pct(b + 8)},{pct(a - 1)} {off} 0%,{pct(b)},{pct(a + 4)},100% {on} }}"

    hx, hy = bw / 2, bh / 2
    corners = [0, top, top + right, 2 * top + right]
    hidden, shown = "{ opacity:0; }", "{ opacity:1; }"
    keyframes = [
        lit(f"lit-{n}", c - (hx if k % 2 else hy), c + (hy if k % 2 else hx), hidden, shown)
        for k, (n, c) in enumerate(zip(cx, corners))
    ]
    quiet, loud = "{ fill:var(--muted); }", "{ fill:var(--signal); }"
    spans = [(hx, top - hx), (top + hy, top + right - hy)]
    spans += [(a + top + right, b + top + right) for a, b in spans]
    keyframes += [lit(f"say-{k}", a, b, quiet, loud) for k, (a, b) in enumerate(spans)]

    chip_w, chip_h = 76, 30
    chip_x = 34
    in_x1, in_x2 = chip_x + chip_w, cx["agent"] - hx - 8
    in_len = in_x2 - in_x1

    style = (
        fonts({
            ("Barlow", "Barlow-Regular", 400): "".join(roles.values()) + "".join(g for _, g in signals) + inlet[2],
            ("JB", "JetBrainsMono", 500): (
                "".join(cx) + inlet[0] + ("".join(s for s, _ in signals) + inlet[1] + centre).upper() + "01234"
            ),
        })
        + PALETTE
        + f"""
  .cmd {{ font:500 17px JB,monospace; fill:var(--fg); }}
  .role {{ font:400 15px Barlow,sans-serif; fill:var(--muted); }}
  .gloss {{ font:400 13px Barlow,sans-serif; fill:var(--muted); }}
  .edge {{ font:500 11px JB,monospace; fill:var(--muted); letter-spacing:.16em; animation:{period}s linear infinite; }}
  .num {{ font:500 10px JB,monospace; fill:var(--muted); letter-spacing:.08em; }}
  .mark {{ font:500 11px JB,monospace; fill:var(--muted); letter-spacing:.24em; }}
  .dot {{ fill:var(--line); }}
  .box {{ fill:none; stroke:var(--line); stroke-width:1.5; }}
  .yours {{ stroke-dasharray:5 4; }}
  .ico {{ fill:none; stroke:var(--muted); stroke-width:1.5; stroke-linecap:round; stroke-linejoin:round; }}
  .tick {{ fill:none; stroke:var(--muted); stroke-width:1.25; stroke-linecap:square; }}
  .track {{ fill:none; stroke:var(--line); stroke-width:1.5; }}
  .head {{ fill:var(--muted); }}
  .rule {{ stroke:var(--line); stroke-width:1; }}
  .sig {{ stroke:var(--signal); stroke-width:2; }}
  .lit {{ opacity:0; animation:{period}s linear infinite; }}
  .lit .box {{ stroke:var(--signal); fill:var(--signal); fill-opacity:.08; }}
  .lit .halo {{ fill:none; stroke:var(--signal); stroke-width:3; stroke-opacity:.5; }}
  .lit .ico {{ stroke:var(--signal); }}
  .lit .num {{ fill:var(--signal); }}
  .pulse {{ fill:none; stroke:var(--signal); stroke-linecap:round; animation:run {period}s linear infinite; }}
  .feed {{ fill:none; stroke:var(--signal); stroke-width:2.5; stroke-linecap:round;
           stroke-dasharray:14 400; stroke-dashoffset:15; animation:feed {2 * period}s linear infinite; }}
  @keyframes run {{ from {{ stroke-dashoffset:var(--o); }} to {{ stroke-dashoffset:calc(var(--o) - {perimeter}px); }} }}
  @keyframes feed {{ 0%,93% {{ stroke-dashoffset:15; }} 100% {{ stroke-dashoffset:-{in_len}; }} }}
  {' '.join(keyframes)}
  {' '.join(f'#lit-{n} {{ animation-name:lit-{n}; }}' for n in cx)}
  {' '.join(f'#say-{k} {{ animation-name:say-{k}; }}' for k in range(4))}
  @media (prefers-reduced-motion: reduce) {{ .pulse, .feed, .lit {{ display:none; }} .edge {{ animation:none; }} }}
"""
    )

    x0, y0 = cx["agent"], cy["agent"]
    x1, y1 = x0 + top, y0 + right
    loop = f"M{x0} {y0} H{x1} V{y1} H{x0} Z"
    holes = "".join(
        f'<rect x="{cx[n] - hx}" y="{cy[n] - hy}" width="{bw}" height="{bh}" fill="#000"/>' for n in cx
    )

    def ticks(x: float, y: float) -> str:
        # Registration corners just outside the box, as on a drafting sheet.
        g, s = 6, 7
        xa, ya, xb, yb = x - hx - g, y - hy - g, x + hx + g, y + hy + g
        return (
            f'<path class="tick" d="M{xa} {ya + s}V{ya}H{xa + s} M{xb - s} {ya}H{xb}V{ya + s} '
            f'M{xb} {yb - s}V{yb}H{xb - s} M{xa + s} {yb}H{xa}V{yb - s}"/>'
        )

    def box(n: str, k: int) -> str:
        bx, by = cx[n] - hx, cy[n] - hy
        yours = " yours" if n == "agent" else ""
        rect = f'x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="2"'
        icon = f'<path class="ico" d="{ICONS[n]}" transform="translate({bx + 16} {cy[n] - 10})"/>'
        num = f'<text class="num" x="{bx + bw - 10}" y="{by + 16}" text-anchor="end">0{k + 1}</text>'
        # The lit state is a second copy faded in over the first, so one
        # opacity keyframe drives the border, tint, icon and number together.
        return (
            ticks(cx[n], cy[n])
            + f'<rect class="box{yours}" {rect}/>{icon}{num}'
            f'<g class="lit" id="lit-{n}"><rect class="halo" {rect} filter="url(#bloom)"/>'
            f'<rect class="box{yours}" {rect}/>{icon}{num}</g>'
            f'<text class="cmd" x="{bx + 50}" y="{cy[n] - 3}">{n}</text>'
            f'<text class="role" x="{bx + 50}" y="{cy[n] + 19}">{roles[n]}</text>'
        )

    boxes = "".join(box(n, k) for k, n in enumerate(cx))
    head = '<path class="head" d="M0 0 L-8 -4.5 L-8 4.5 Z" transform="translate({} {}) rotate({})"/>'
    arrows = "".join(
        head.format(x, y, r)
        for x, y, r in [
            (x1 - hx - 2, y0, 0),
            (x1, y1 - hy - 2, 90),
            (x0 + hx + 2, y1, 180),
            (x0, y0 + hy + 2, 270),
            (in_x2 + 6, y0, 0),
        ]
    )
    mid_x, mid_y = x0 + top / 2, y0 + right / 2
    places = [
        (mid_x, y0 - 10, "middle", mid_x, y0 + 20, "middle"),
        (x1 + 14, mid_y - 4, "start", x1 + 14, mid_y + 15, "start"),
        (mid_x, y1 + 22, "middle", mid_x, y1 - 11, "middle"),
        (x0 - 14, mid_y - 4, "end", x0 - 14, mid_y + 15, "end"),
    ]
    edges = "".join(
        f'<text class="edge" id="say-{k}" x="{ex}" y="{ey}" text-anchor="{ea}">{name.upper()}</text>'
        f'<text class="gloss" x="{gx}" y="{gy}" text-anchor="{ga}">{gloss}</text>'
        for k, ((name, gloss), (ex, ey, ea, gx, gy, ga)) in enumerate(zip(signals, places))
    )
    chip_cx = chip_x + chip_w / 2
    feed = (
        f'<rect class="box" x="{chip_x}" y="{y0 - chip_h / 2}" width="{chip_w}" height="{chip_h}" rx="15"/>'
        f'<text class="cmd" x="{chip_cx}" y="{y0 + 5}" text-anchor="middle" style="font-size:14px">{inlet[0]}</text>'
        f'<text class="gloss" x="{chip_cx}" y="{y0 + chip_h / 2 + 18}" text-anchor="middle">{inlet[2]}</text>'
        f'<text class="edge" x="{(in_x1 + in_x2) / 2 + 1}" y="{y0 - 10}" text-anchor="middle" '
        f'style="animation:none">{inlet[1].upper()}</text>'
        f'<path class="track" d="M{in_x1} {y0}H{in_x2}"/><path class="feed" d="M{in_x1} {y0}H{in_x2}"/>'
    )
    mark = (
        f'<line class="rule" x1="{mid_x - 44}" y1="{mid_y - 13.5}" x2="{mid_x + 44}" y2="{mid_y - 13.5}"/>'
        f'<line class="sig" x1="{mid_x - 44}" y1="{mid_y - 13}" x2="{mid_x - 26}" y2="{mid_y - 13}"/>'
        f'<text class="mark" x="{mid_x + 1.5}" y="{mid_y + 6}" text-anchor="middle">{centre.upper()}</text>'
    )
    full = f'maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}"'
    body = f"""<defs>
  <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse"><circle class="dot" cx="10" cy="10" r="1"/></pattern>
  <radialGradient id="fade" cx="50%" cy="50%" r="55%"><stop offset="0" stop-color="#fff" stop-opacity=".9"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>
  <filter id="bloom" filterUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}"><feGaussianBlur stdDeviation="4"/></filter>
  <mask id="vignette" {full}><rect width="{W}" height="{H}" fill="url(#fade)"/></mask>
  <mask id="gaps" {full}><rect width="{W}" height="{H}" fill="#fff"/>{holes}</mask>
</defs>
<rect width="{W}" height="{H}" fill="url(#grid)" mask="url(#vignette)"/>
<g mask="url(#gaps)"><path class="track" d="{loop}"/>{pulses.replace("LOOP", loop)}</g>
{feed}{arrows}{edges}{mark}{boxes}"""
    label = (
        "A feedback loop: flocc hands the agent an issue, the agent acts in stoat, midwire checks "
        "what changed, docket records the decision, and the record feeds the agent's next step."
    )
    return svg(W, H, label, style, body)


STACK = {
    "Languages": ["Rust", "Go", "C", "Python", "TypeScript", "Elixir"],
    "Data": ["Postgres", "Qdrant", "ClickHouse", "TypeDB", "Redis", "SQLite"],
    "Orchestration": ["Claude", "MCP", "Temporal", "Dagster", "LiteLLM", "Pydantic AI"],
    "Infra & policy": ["QEMU", "Nix", "Docker", "Pulumi", "Terraform", "Cedar"],
}


def stack() -> str:
    heads = "".join(STACK)
    items = "".join(i for v in STACK.values() for i in v)
    style = (
        fonts({
            ("Barlow", "Barlow-Medium", 500): heads,
            ("Barlow", "Barlow-Regular", 400): items,
        })
        + PALETTE
        + """
  .h { font:500 15px Barlow,sans-serif; fill:var(--muted); }
  .i { font:400 18px Barlow,sans-serif; fill:var(--fg); }
  .rule { stroke:var(--line); stroke-width:1; }
  .tick { stroke:var(--signal); stroke-width:2; }
"""
    )
    col = 200
    parts = []
    for n, (head, entries) in enumerate(STACK.items()):
        x = n * col
        parts.append(f'<line class="rule" x1="{x}" y1="0.5" x2="{x + col - 24}" y2="0.5"/>')
        parts.append(f'<line class="tick" x1="{x}" y1="1" x2="{x + 18}" y2="1"/>')
        parts.append(f'<text class="h" x="{x}" y="28">{escape(head)}</text>')
        for k, item in enumerate(entries):
            parts.append(f'<text class="i" x="{x}" y="{60 + 28 * k}">{item}</text>')
    label = "Stack. " + ". ".join(f"{h}: {', '.join(v)}" for h, v in STACK.items())
    return svg(800, 212, label, style, "\n".join(parts))


def footer() -> str:
    # The header's pulse, run once across the page width, then a long rest.
    style = PALETTE + """
  .track { stroke:var(--line); stroke-width:1; }
  .pulse { stroke:var(--signal); stroke-width:2.5; stroke-linecap:round;
           stroke-dasharray:26 1600; stroke-dashoffset:26; animation:run 9s cubic-bezier(.5,0,.3,1) infinite; }
  @keyframes run { 0% { stroke-dashoffset:26; } 45%,100% { stroke-dashoffset:-800; } }
  @media (prefers-reduced-motion: reduce) { .pulse { display:none; } }
"""
    body = (
        '<line class="track" x1="0" y1="12" x2="800" y2="12"/>'
        '<line class="pulse" x1="0" y1="12" x2="800" y2="12"/>'
    )
    return svg(800, 24, "", style, body).replace(' role="img" aria-label=""', ' aria-hidden="true"')


if __name__ == "__main__":
    for name, fn in [("header", header), ("stack", stack), ("footer", footer)]:
        (ASSETS / f"{name}.svg").write_text(fn())
        print(f"{name}.svg {(ASSETS / f'{name}.svg').stat().st_size // 1024} KB")
