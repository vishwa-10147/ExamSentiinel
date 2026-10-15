"""Add missing Tailwind dark-mode variants next to light-only colour classes.

    python scripts/add-dark-variants.py            # dry run: report what would change
    python scripts/add-dark-variants.py --write    # apply
    python scripts/add-dark-variants.py --check    # CI: exit 1 if any light-only class lacks a dark variant

For every string literal in app/ and components/ that contains Tailwind classes, a light colour
class such as ``bg-white`` gets its dark counterpart (``dark:bg-slate-800``) inserted right
after it, in the same string - so conditional branches keep their own colours. Nothing is
added when the string (or, inside a className attribute, any part of that attribute) already
sets a dark variant for the same property.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# light class -> dark class
MAP = {
    "bg-white": "dark:bg-slate-800",
    "bg-slate-50": "dark:bg-slate-900", "bg-gray-50": "dark:bg-slate-900",
    "bg-slate-100": "dark:bg-slate-800", "bg-gray-100": "dark:bg-slate-800",
    "bg-slate-200": "dark:bg-slate-700", "bg-gray-200": "dark:bg-slate-700",
    "text-slate-900": "dark:text-white", "text-gray-900": "dark:text-white", "text-black": "dark:text-white",
    "text-slate-800": "dark:text-slate-100", "text-gray-800": "dark:text-slate-100",
    "text-slate-700": "dark:text-slate-200", "text-gray-700": "dark:text-slate-200",
    "text-slate-600": "dark:text-slate-300", "text-gray-600": "dark:text-slate-300",
    "text-slate-500": "dark:text-slate-400", "text-gray-500": "dark:text-slate-400",
    "border-slate-100": "dark:border-slate-700", "border-gray-100": "dark:border-slate-700",
    "border-slate-200": "dark:border-slate-700", "border-gray-200": "dark:border-slate-700",
    "border-slate-300": "dark:border-slate-600", "border-gray-300": "dark:border-slate-600",
    "divide-slate-100": "dark:divide-slate-700", "divide-gray-100": "dark:divide-slate-700",
    "divide-slate-200": "dark:divide-slate-700", "divide-gray-200": "dark:divide-slate-700",
    "hover:bg-slate-50": "dark:hover:bg-slate-700/50", "hover:bg-gray-50": "dark:hover:bg-slate-700/50",
    "hover:bg-slate-100": "dark:hover:bg-slate-700", "hover:bg-gray-100": "dark:hover:bg-slate-700",
    "hover:text-slate-900": "dark:hover:text-white", "hover:text-gray-900": "dark:hover:text-white",
}
# Which existing dark: prefix counts as "already handled" for each light class.
def prop(cls: str) -> str:
    if cls.startswith("hover:bg-"):
        return "dark:hover:bg-"
    if cls.startswith("hover:text-"):
        return "dark:hover:text-"
    return "dark:" + cls.split("-")[0] + "-"

TEXT_COLOR = re.compile(r"^text-(?:slate|gray|black)")
# A light tinted background (badges, alerts): mapping its text to white would hurt contrast.
TINTED_BG = re.compile(r"(?<![\w:-])bg-(?!slate|gray|white|zinc|neutral|stone)[a-z]+-(?:50|100|200)(?![\w/-])")
LITERAL = re.compile(r'"([^"\\\n]*)"|`([^`]*)`')
CLASSNAME = re.compile(r"className=")
SKIP_FILES = {"globals.css"}


def attribute_spans(src: str) -> list[tuple[int, int]]:
    """Spans of className={...} / className="..." attribute values."""
    spans = []
    for m in CLASSNAME.finditer(src):
        i = m.end()
        if i < len(src) and src[i] == '"':
            j = src.index('"', i + 1)
            spans.append((i, j + 1))
        elif i < len(src) and src[i] == "{":
            depth, j = 0, i
            while j < len(src):
                if src[j] == "{":
                    depth += 1
                elif src[j] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            spans.append((i, j + 1))
    return spans


def tokens(text: str) -> list[str]:
    # Split on whitespace and JS punctuation so classes inside ${cond ? "a" : "b"} are seen too.
    return [t for t in re.split(r"[\s\"'`{}()?,$]+", text) if t]


# Coloured (non-neutral) classes: tinted badge/alert backgrounds become translucent in dark mode,
# and dark coloured text is lifted to a lighter shade so it stays readable.
COLORS = "red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose"


def color_dark(cls: str) -> str | None:
    m = re.fullmatch(rf"(hover:)?(bg|border|text|from|via|to)-({COLORS})-(\d+)", cls)
    if not m:
        return None
    hover, kind, color, shade = m.group(1) or "", m.group(2), m.group(3), int(m.group(4))
    if kind == "bg" and shade in (50, 100):
        return f"dark:{hover}bg-{color}-500/{10 if shade == 50 else 20}"
    if kind == "border" and shade in (100, 200, 300) and not hover:
        return f"dark:border-{color}-500/30"
    if kind == "text" and shade >= 600 and not hover:
        return f"dark:text-{color}-{400 if shade <= 700 else 300}"
    if kind in ("from", "via", "to") and shade in (50, 100) and not hover:
        return f"dark:{kind}-{color}-950/40"
    return None


def color_prop(cls: str) -> str:
    base = cls.split(":")[-1]
    kind = base.split("-")[0]
    return ("dark:hover:" if cls.startswith("hover:") else "dark:") + kind + "-"


def transform(text: str, context_tokens: list[str]) -> tuple[str, int]:
    have = set(context_tokens) | set(tokens(text))
    tinted = bool(TINTED_BG.search(" ".join(t for t in context_tokens if not t.startswith("dark:"))))
    # A tinted background that already has (or is about to get) a dark variant is not "light" in dark mode.
    if tinted and any(t.startswith("dark:bg-") for t in have):
        tinted = False
    added = 0

    def repl(m: re.Match) -> str:
        nonlocal added
        cls, alpha = m.group(1), m.group(2) or ""
        if cls in MAP:
            dark, key = MAP[cls] + alpha, prop(cls)
            if tinted and TEXT_COLOR.match(cls):
                return m.group(0)
        else:
            dark = color_dark(cls)
            if dark is None:
                return m.group(0)
            key = color_prop(cls)
        if any(t.startswith(key) for t in have):
            return m.group(0)
        added += 1
        return f"{m.group(0)} {dark}"

    # An optional opacity suffix (bg-white/80) is carried over to the dark class.
    static = "|".join(re.escape(k) for k in sorted(MAP, key=len, reverse=True))
    colored = rf"(?:hover:)?(?:bg|border|text|from|via|to)-(?:{COLORS})-\d+"
    pattern = rf"(?<![\w:/\[-])({static}|{colored})(/\d+)?(?![\w/\[-])"
    return re.sub(pattern, repl, text), added


def process(path: Path, write: bool) -> int:
    src = path.read_text(encoding="utf-8")
    spans = attribute_spans(src)
    out, last, total = [], 0, 0
    for m in LITERAL.finditer(src):
        body = m.group(1) if m.group(1) is not None else m.group(2)
        span = next(((a, b) for a, b in spans if a <= m.start() < b), None)
        # Outside a className attribute, require 2+ tokens so ordinary strings are left alone.
        if not body or (span is None and len(tokens(body)) < 2):
            continue
        context = tokens(src[span[0]:span[1]]) if span else tokens(body)
        new_body, added = transform(body, context)
        if not added:
            continue
        quote = '"' if m.group(1) is not None else "`"
        out.append(src[last:m.start()])
        out.append(quote + new_body + quote)
        last = m.end()
        total += added
    if total and write:
        out.append(src[last:])
        path.write_text("".join(out), encoding="utf-8", newline="\n")
    return total


def main() -> None:
    write = "--write" in sys.argv
    grand = 0
    for path in sorted(list((ROOT / "app").rglob("*.tsx")) + list((ROOT / "components").rglob("*.tsx"))):
        n = process(path, write)
        if n:
            grand += n
            print(f"{n:4d}  {path.relative_to(ROOT)}")
    print(f"{'applied' if write else 'would add'} {grand} dark variants")
    if "--check" in sys.argv and grand:
        print("Light-only colour classes found: run `python scripts/add-dark-variants.py --write` and review the diff.")
        sys.exit(1)


if __name__ == "__main__":
    main()
