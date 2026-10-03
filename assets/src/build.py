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


def header() -> str:
    W, H = 800, 280
    # Clockwise loop through the four box centres. The track runs under the
    # boxes and is masked out there, so only the edges between them show.
    bw, bh = 188, 64
    cx = {"agent": 210, "stoat": 590, "midwire": 590, "docket": 210}
    cy = {"agent": 74, "stoat": 74, "midwire": 206, "docket": 206}
    roles = {
        "agent": "your coding agent",
        "stoat": "runs it in a VM",
        "midwire": "checks what changed",
        "docket": "records the decision",
    }
    signals = ["acts", "effect", "verdict", "context"]
    top, right = cx["stoat"] - cx["agent"], cy["midwire"] - cy["stoat"]
    perimeter = 2 * (top + right)
    period = 6.4

    # The pulse is three dashes sharing one animation; leading gaps offset each
    # so they end at the same point and read as one comet with a fading tail.
    # A pattern must sum to the perimeter or the dash repeats on the loop.
    trail = [(96, 0.12, 1.5), (52, 0.35, 2), (22, 1.0, 2.75)]
    tail = trail[0][0]
    pulses = "".join(
        f'<path class="pulse" d="LOOP" stroke-opacity="{op}" stroke-width="{sw}" '
        f'stroke-dasharray="0 {tail - n} {n} {perimeter - tail}"/>'
        for n, op, sw in trail
    )

    # Distance along the track where the bright head enters and leaves each box,
    # as keyframe percentages, so a box lights while the head is inside it.
    hx, hy = bw / 2, bh / 2
    head_len = trail[-1][0]
    spans = {
        "stoat": (top - hx - tail, top + hy - (tail - head_len)),
        "midwire": (top + right - hy - tail, top + right + hx - (tail - head_len)),
        "docket": (2 * top + right - hx - tail, 2 * top + right + hy - (tail - head_len)),
    }

    def pct(d: float) -> str:
        return f"{100 * (d % perimeter) / perimeter:.2f}%"

    off = "{ stroke:var(--line); fill-opacity:0; }"
    on = "{ stroke:var(--signal); fill-opacity:.09; }"
    keyframes = [
        f"@keyframes lit-{n} {{ 0%,{pct(a - 1)},{pct(b + 8)},100% {off} {pct(a + 4)},{pct(b)} {on} }}"
        for n, (a, b) in spans.items()
    ]
    # The agent box straddles the loop's start, so its lit span wraps past 100%.
    a_in, a_out = perimeter - hy - tail, hx - (tail - head_len)
    keyframes.append(
        f"@keyframes lit-agent {{ {pct(a_out + 8)},{pct(a_in - 1)} {off}"
        f" 0%,{pct(a_out)},{pct(a_in + 4)},100% {on} }}"
    )

    style = (
        fonts({
            ("Barlow", "Barlow-Regular", 400): "".join(roles.values()),
            ("JB", "JetBrainsMono", 500): "".join(cx) + "".join(signals).upper(),
        })
        + PALETTE
        + f"""
  .cmd {{ font:500 17px JB,monospace; fill:var(--fg); }}
  .role {{ font:400 15px Barlow,sans-serif; fill:var(--muted); }}
  .edge {{ font:500 11px JB,monospace; fill:var(--muted); letter-spacing:.16em; }}
  .dot {{ fill:var(--line); }}
  .box {{ fill:var(--signal); fill-opacity:0; stroke:var(--line); stroke-width:1.5;
          animation:{period}s linear infinite; }}
  .yours {{ stroke-dasharray:5 4; }}
  .tick {{ fill:none; stroke:var(--muted); stroke-width:1.25; stroke-linecap:square; }}
  .track {{ fill:none; stroke:var(--line); stroke-width:1.5; }}
  .head {{ fill:var(--muted); }}
  .pulse {{ fill:none; stroke:var(--signal); stroke-linecap:round; animation:run {period}s linear infinite; }}
  @keyframes run {{ to {{ stroke-dashoffset:-{perimeter}; }} }}
  {' '.join(keyframes)}
  {' '.join(f'#box-{n} {{ animation-name:lit-{n}; }}' for n in cx)}
  @media (prefers-reduced-motion: reduce) {{ .pulse, .box {{ animation:none; }} .pulse {{ display:none; }} }}
"""
    )

    x0, y0 = cx["agent"], cy["agent"]
    loop = f"M{x0} {y0} H{x0 + top} V{y0 + right} H{x0} Z"
    pulses = pulses.replace("LOOP", loop)
    holes = "".join(
        f'<rect x="{cx[n] - hx}" y="{cy[n] - hy}" width="{bw}" height="{bh}" fill="#000"/>' for n in cx
    )

    def ticks(x: float, y: float) -> str:
        # Registration corners just outside the box, as on a drafting sheet.
        g, s = 6, 7
        x1, y1, x2, y2 = x - hx - g, y - hy - g, x + hx + g, y + hy + g
        return (
            f'<path class="tick" d="M{x1} {y1 + s}V{y1}H{x1 + s} M{x2 - s} {y1}H{x2}V{y1 + s} '
            f'M{x2} {y2 - s}V{y2}H{x2 - s} M{x1 + s} {y2}H{x1}V{y2 - s}"/>'
        )

    boxes = "".join(
        ticks(cx[n], cy[n])
        + f'<rect id="box-{n}" class="box{" yours" if n == "agent" else ""}" x="{cx[n] - hx}" '
        f'y="{cy[n] - hy}" width="{bw}" height="{bh}" rx="2"/>'
        f'<text class="cmd" x="{cx[n] - hx + 16}" y="{cy[n] - 3}">{n}</text>'
        f'<text class="role" x="{cx[n] - hx + 16}" y="{cy[n] + 19}">{roles[n]}</text>'
        for n in cx
    )
    heads = [
        (cx["stoat"] - hx - 2, y0, 0),
        (cx["stoat"], cy["midwire"] - hy - 2, 90),
        (cx["docket"] + hx + 2, cy["docket"], 180),
        (x0, y0 + hy + 2, 270),
    ]
    arrows = "".join(
        f'<path class="head" d="M0 0 L-8 -4.5 L-8 4.5 Z" transform="translate({x} {y}) rotate({r})"/>'
        for x, y, r in heads
    )
    mid_x, mid_y = x0 + top / 2, y0 + right / 2
    edges = (
        f'<text class="edge" x="{mid_x}" y="{y0 - 10}" text-anchor="middle">{signals[0].upper()}</text>'
        f'<text class="edge" x="{cx["stoat"] + 14}" y="{mid_y + 4}">{signals[1].upper()}</text>'
        f'<text class="edge" x="{mid_x}" y="{cy["docket"] + 22}" text-anchor="middle">{signals[2].upper()}</text>'
        f'<text class="edge" x="{x0 - 14}" y="{mid_y + 4}" text-anchor="end">{signals[3].upper()}</text>'
    )
    body = f"""<defs>
  <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse"><circle class="dot" cx="10" cy="10" r="1"/></pattern>
  <radialGradient id="fade" cx="50%" cy="50%" r="55%"><stop offset="0" stop-color="#fff" stop-opacity=".9"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>
  <mask id="vignette" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}"><rect width="{W}" height="{H}" fill="url(#fade)"/></mask>
  <mask id="gaps" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}"><rect width="{W}" height="{H}" fill="#fff"/>{holes}</mask>
</defs>
<rect width="{W}" height="{H}" fill="url(#grid)" mask="url(#vignette)"/>
<g mask="url(#gaps)"><path class="track" d="{loop}"/>{pulses}</g>
{arrows}{edges}{boxes}"""
    label = (
        "A feedback loop: the agent acts in stoat, midwire checks what changed, "
        "docket records the decision, and the record feeds the agent's next step."
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
