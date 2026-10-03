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
    name = "Aliasgar Khimani"
    lines = ["Tools for coding agents that act,", "check the result, and remember why."]

    # Clockwise loop through the four box centres. The track runs under the
    # boxes and is masked out there, so only the edges between them show.
    bw, bh = 152, 58
    cx = {"agent": 488, "stoat": 708, "midwire": 708, "docket": 488}
    cy = {"agent": 70, "stoat": 70, "midwire": 196, "docket": 196}
    roles = {
        "agent": "your coding agent",
        "stoat": "runs it in a VM",
        "midwire": "checks what changed",
        "docket": "records the decision",
    }
    top, right = cx["stoat"] - cx["agent"], cy["midwire"] - cy["stoat"]
    perimeter = 2 * (top + right)
    dash = 26
    period = 5.2

    # Distance along the track where the pulse enters and leaves each box,
    # converted to keyframe percentages so a box lights while the pulse is in it.
    hx, hy = bw / 2, bh / 2
    spans = {
        "stoat": (top - hx - dash, top + hy),
        "midwire": (top + right - hy - dash, top + right + hx),
        "docket": (2 * top + right - hx - dash, 2 * top + right + hy),
    }

    def pct(d: float) -> str:
        return f"{100 * d / perimeter:.2f}%"

    keyframes = []
    for node, (a, b) in spans.items():
        keyframes.append(
            f"@keyframes lit-{node} {{ 0%,{pct(a - 1)},{pct(b + 6)},100% {{ stroke:var(--line); }}"
            f" {pct(a + 4)},{pct(b)} {{ stroke:var(--signal); }} }}"
        )
    a_in, a_out = perimeter - hy - dash, hx
    keyframes.append(
        f"@keyframes lit-agent {{ {pct(a_out + 6)},{pct(a_in - 1)} {{ stroke:var(--line); }}"
        f" 0%,{pct(a_out)},{pct(a_in + 4)},100% {{ stroke:var(--signal); }} }}"
    )

    mono = "".join(cx) + "".join(roles)
    style = (
        fonts({
            ("Barlow", "Barlow-SemiBold", 600): name,
            ("Barlow", "Barlow-Regular", 400): "".join(lines) + "".join(roles.values())
            + "actseffectverdictcontext",
            ("JB", "JetBrainsMono", 500): mono,
        })
        + PALETTE
        + f"""
  .name {{ font:600 36px Barlow,sans-serif; fill:var(--fg); letter-spacing:-0.01em; }}
  .lede {{ font:400 18px Barlow,sans-serif; fill:var(--muted); }}
  .cmd {{ font:500 16px JB,monospace; fill:var(--fg); }}
  .role {{ font:400 14px Barlow,sans-serif; fill:var(--muted); }}
  .edge {{ font:400 14px Barlow,sans-serif; fill:var(--muted); }}
  .box {{ fill:none; stroke:var(--line); stroke-width:1.5; animation:{period}s linear infinite; }}
  .yours {{ stroke-dasharray:4 4; }}
  .track {{ fill:none; stroke:var(--line); stroke-width:1.5; }}
  .head {{ fill:var(--muted); }}
  .pulse {{ fill:none; stroke:var(--signal); stroke-width:2.5; stroke-linecap:round;
           stroke-dasharray:{dash} {perimeter - dash}; animation:run {period}s linear infinite; }}
  @keyframes run {{ to {{ stroke-dashoffset:-{perimeter}; }} }}
  {' '.join(keyframes)}
  {' '.join(f'#box-{n} {{ animation-name:lit-{n}; }}' for n in cx)}
  @media (prefers-reduced-motion: reduce) {{ .pulse, .box {{ animation:none; }} .pulse {{ display:none; }} }}
"""
    )

    x0, y0 = cx["agent"], cy["agent"]
    loop = f"M{x0} {y0} H{x0 + top} V{y0 + right} H{x0} Z"
    holes = "".join(
        f'<rect x="{cx[n] - hx}" y="{cy[n] - hy}" width="{bw}" height="{bh}" fill="#000"/>' for n in cx
    )
    boxes = "".join(
        f'<rect id="box-{n}" class="box{" yours" if n == "agent" else ""}" x="{cx[n] - hx}" '
        f'y="{cy[n] - hy}" width="{bw}" height="{bh}" rx="3"/>'
        f'<text class="cmd" x="{cx[n] - hx + 14}" y="{cy[n] - 4}">{n}</text>'
        f'<text class="role" x="{cx[n] - hx + 14}" y="{cy[n] + 17}">{roles[n]}</text>'
        for n in cx
    )
    # Arrowheads at the end of each edge, pointing along the loop.
    heads = [
        (cx["stoat"] - hx, y0, 0),
        (cx["stoat"], cy["midwire"] - hy, 90),
        (cx["docket"] + hx, cy["docket"], 180),
        (x0, y0 + hy, 270),
    ]
    arrows = "".join(
        f'<path class="head" d="M0 0 L-8 -4.5 L-8 4.5 Z" transform="translate({x} {y}) rotate({r})"/>'
        for x, y, r in heads
    )
    mid_x, mid_y = x0 + top / 2, y0 + right / 2
    edges = (
        f'<text class="edge" x="{mid_x}" y="{y0 - 8}" text-anchor="middle">acts</text>'
        f'<text class="edge" x="{cx["stoat"] + 10}" y="{mid_y + 5}">effect</text>'
        f'<text class="edge" x="{mid_x}" y="{cy["docket"] + 20}" text-anchor="middle">verdict</text>'
        f'<text class="edge" x="{x0 - 10}" y="{mid_y + 5}" text-anchor="end">context</text>'
    )
    body = f"""<mask id="gaps" maskUnits="userSpaceOnUse" x="0" y="0" width="800" height="266">
  <rect width="800" height="266" fill="#fff"/>{holes}</mask>
<text class="name" x="0" y="110">{name}</text>
<text class="lede" x="0" y="146">{lines[0]}</text>
<text class="lede" x="0" y="170">{lines[1]}</text>
<g mask="url(#gaps)"><path class="track" d="{loop}"/><path class="pulse" d="{loop}"/></g>
{arrows}{edges}{boxes}"""
    label = (
        f"{name}. {lines[0]} {lines[1]} A feedback loop: the agent acts in stoat, "
        "midwire checks what changed, docket records the decision, and the record "
        "feeds the agent's next step."
    )
    return svg(800, 266, label, style, body)


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
