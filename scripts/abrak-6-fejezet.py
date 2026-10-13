#!/usr/bin/env python3
"""A 6. fejezet négy ábrája, közvetlenül a mérés bizonyítékfájljaiból.

Futtatás a repó gyökeréből:

    python3 scripts/abrak-6-fejezet.py

Kimenet: szakdolgozat/abrak/abra-6-N-*.png (300 dpi, a Word-dokumentumba) és
.pdf (vektoros, ha a dolgozat LaTeX-ben vagy nyomdai minőségben készül).

Miért script és nem kézzel rajzolt ábra: a dolgozat minden száma a
szakdolgozat/bizonyitek/meres/ fájljaiból jön, és az ábrának is onnan kell
jönnie. Ha egy adat javul (ahogy a 2026-09-30-i javításoknál történt), az ábra
egy paranccsal újra elkészül, és nem térhet el a táblázattól. A script nem
számol semmit, amit a bizonyítékfájlok nem tartalmaznak; ahol két forrás
összegének egyeznie kell, ott ellenőriz (assert), és eltérésnél megáll.

Bontásoknál a "medián futtatás" módszere: a halmozott oszlop annak a
futtatásnak a valódi szakaszait mutatja, amelynek teljes ideje a sorozat
mediánja (egyezésnél a legkisebb sorszámú). A szakaszonkénti mediánok
összege ugyanis nem egyenlő a teljes idő mediánjával, és egy olyan oszlop,
amelynek a hossza nem egyezik a rá írt számmal, a bírálónál az első kérdés.
"""
from __future__ import annotations

import csv
import re
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MERES = ROOT / "szakdolgozat" / "bizonyitek" / "meres"
OUT = ROOT / "szakdolgozat" / "abrak"

# Nyomtatásra: fehér felület, sötét szöveg, halvány rács. A kategóriaszínek a
# validált alappaletta sorrendjében (a sorrend a színtévesztő-biztonság
# feltétele, nem ízlés). A szürke szándékosan semleges: azt jelöli, ami a két
# oldalon azonos (gépi kivárás), hogy a szem a különbségre essen.
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET = (
    "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7",
)
NEUTRAL = "#c3c2b7"
SHADE = "#f0efec"

plt.rcParams.update({
    "font.family": "DejaVu Sans",   # ő, ű biztosan megvan benne
    "font.size": 9,
    "axes.edgecolor": AXIS,
    "axes.labelcolor": INK2,
    "axes.titlesize": 10,
    "axes.titleweight": "bold",
    "axes.titlecolor": INK,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "xtick.labelcolor": INK2,
    "ytick.labelcolor": INK2,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "legend.frameon": False,
    "savefig.facecolor": "white",
    "figure.facecolor": "white",
})
WIDTH_IN = 6.3  # ~16 cm, A4 szövegtükör


def hu(x: float, nd: int = 0) -> str:
    """Magyar tizedesvessző."""
    s = f"{x:.{nd}f}"
    return s.replace(".", ",")


def mp(cell: str) -> float | None:
    m = re.search(r"(\d+(?:,\d+)?)", cell)
    return float(m.group(1).replace(",", ".")) if m else None


def md_table_rows(path: Path, start: str | None = None) -> list[list[str]]:
    """Egy markdown-fájl első táblázatának sorai (a `start` fejléc után)."""
    text = path.read_text(encoding="utf-8").splitlines()
    if start:
        text = text[next(i for i, ln in enumerate(text) if ln.startswith(start)):]
    rows, inside = [], False
    for line in text:
        if line.startswith("|"):
            inside = True
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if not set("".join(cells)) <= set("-: "):
                rows.append(cells)
        elif inside:
            break
    return rows[1:]  # fejléc nélkül


def read_csv(name: str) -> list[dict]:
    with open(MERES / name, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def median_run(values: list[float], candidates: list[int]) -> int:
    """A medián teljes idejű futtatás indexe (egyezésnél a legkisebb)."""
    med = statistics.median(values[i] for i in candidates)
    for i in candidates:
        if values[i] == med:
            return i
    raise SystemExit(f"nincs olyan futtatás, amelynek ideje a medián ({med})")


def finish(ax):
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def save(fig, name: str):
    OUT.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"{name}.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  {name}.png / .pdf")


# --- adatok ---------------------------------------------------------------
kezi = read_csv("kezi-sorozat.csv")
K_TOTAL = [float(r["eltelt_mp"]) for r in kezi]
BEALLT = list(range(3, 10))  # a 4–10. futtatás, 0-tól számozva

# lepesidok.md: a 13 lépés futtatásonként
STEP = {}
for cells in md_table_rows(MERES / "lepesidok.md"):
    key = cells[0]
    if key.isdigit() or key == "—":
        STEP[key] = (cells[1].strip("*"), [mp(c) for c in cells[2:12]])
for i in BEALLT:  # a bontás zárt: a lépések összege a CSV teljes ideje
    s = sum(v[i] for v in (STEP[k][1] for k in STEP))
    assert s == K_TOTAL[i], (i + 1, s, K_TOTAL[i])

auto = read_csv("auto-sorozat.csv")
A_TOTAL = [float(r["teljes_mp"]) for r in auto]
A_DEPLOY = [float(r["telepitesi_szakasz_mp"]) for r in auto]

AUTO = {}
for cells in md_table_rows(MERES / "auto-lepesidok.md", "## A telepítési sorozat"):
    code = cells[0].split()[0].strip("*")
    if re.fullmatch(r"F|J|B\d|D\d", code):
        AUTO[code] = [mp(c) for c in cells[1:11]]
assert len(AUTO) == 15, sorted(AUTO)

hiba = read_csv("hiba-sorozat.csv")
H_TOTAL = [float(r["teljes_mp"]) for r in hiba]
HSTEP = {}
for cells in md_table_rows(MERES / "hiba-lepesidok.md"):
    if cells[0] in {"12", "13", "V2", "V3", "V4", "V5", "V6"}:
        HSTEP[cells[0]] = [mp(c) for c in cells[2:5]]

ahiba = read_csv("auto-hiba-sorozat.csv")
AH_TOTAL = [float(r["teljes_mp"]) for r in ahiba]


# --- 6.1 ------------------------------------------------------------------
def abra_6_1():
    fig, ax = plt.subplots(figsize=(WIDTH_IN, 2.9))
    x = list(range(1, 11))
    ax.axvspan(3.5, 10.5, color=SHADE, zorder=0)
    med = statistics.median(K_TOTAL[i] for i in BEALLT)
    ax.axhline(med, color=MUTED, linewidth=1, linestyle=(0, (4, 3)), zorder=1)
    ax.plot(x, K_TOTAL, color=BLUE, linewidth=2, zorder=2)
    ax.scatter(x, K_TOTAL, s=28, color=BLUE, edgecolor="white", linewidth=1.5, zorder=3)
    for xi, y in zip(x, K_TOTAL):
        lo = y == min(K_TOTAL[i] for i in BEALLT)
        if xi in (1, 2, 3) or lo or y == max(K_TOTAL[i] for i in BEALLT):
            ax.annotate(f"{hu(y)}", (xi, y), xytext=(0, -13 if lo else 7),
                        textcoords="offset points", ha="center", color=INK2, fontsize=8)
    ax.text(0.65, med - 5, f"beállt medián: {hu(med)} mp", ha="left", va="top",
            color=INK2, fontsize=8)
    ax.text(7, 168, "beállt szakasz (4–10.)", ha="center", color=INK2, fontsize=8)
    ax.text(2, 168, "bemelegedés", ha="center", color=INK2, fontsize=8)
    ax.set_xlim(0.5, 10.5)
    ax.set_ylim(0, 178)
    ax.set_yticks(range(0, 176, 25))
    ax.set_xticks(x)
    ax.set_xlabel("futtatás sorszáma")
    ax.set_ylabel("teljes idő (mp)")
    ax.set_title("Kézi telepítés: teljes idő futtatásonként", loc="left")
    finish(ax)
    save(fig, "abra-6-1-kezi-tanulasi-gorbe")


# --- 6.2 ------------------------------------------------------------------
GEPI = {"5", "6", "7", "8", "9", "10", "11"}


def abra_6_2():
    keys = [str(n) for n in range(1, 14)]
    keys.insert(2, "—")  # a műszer a 2. lépés után jön, a jegyzőkönyv sorrendjében
    labels, vals, colors = [], [], []
    for k in keys:
        name, v = STEP[k]
        m = statistics.median(v[i] for i in BEALLT)
        labels.append(f"{k}. {name}" if k != "—" else "prompt beállítása (műszer)")
        vals.append(m)
        colors.append(NEUTRAL if k == "—" else BLUE if k in GEPI else ORANGE)
    fig, ax = plt.subplots(figsize=(WIDTH_IN, 3.9))
    y = list(range(len(keys)))[::-1]
    ax.barh(y, vals, color=colors, height=0.62, edgecolor="white", linewidth=1)
    for yi, v in zip(y, vals):
        ax.text(v + 0.3, yi, f"{hu(v)} mp", va="center", color=INK2, fontsize=8)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel("medián a beállt szakaszban, 4–10. futtatás (mp)")
    ax.set_xlim(0, max(vals) + 3)
    ax.set_xticks(range(0, int(max(vals)) + 3, 5))
    ax.set_title("Kézi telepítés: a 13 lépés ideje", loc="left")
    ax.legend(handles=[Patch(color=BLUE, label="gépi (build, push, helm, gördülő csere)"),
                       Patch(color=ORANGE, label="begépelt és elolvasott"),
                       Patch(color=NEUTRAL, label="mérőeszköz")],
              loc="lower right", fontsize=8)
    ax.grid(axis="x", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    save(fig, "abra-6-2-kezi-lepesbontas")


# --- 6.3 ------------------------------------------------------------------
GROUPS = [
    ("futtató és előkészítés (F, B1, B2, B9, J, D1, D2)", BLUE, ["F", "B1", "B2", "B9", "J", "D1", "D2"]),
    ("ansible-lint és függőségei (B5)", ORANGE, ["B5"]),
    ("többi minőségi kapu (B3, B4, B7)", AQUA, ["B3", "B4", "B7"]),
    ("két image-build és push (B6, B8)", YELLOW, ["B6", "B8"]),
    ("helm upgrade --wait (D3)", MAGENTA, ["D3"]),
    ("verify (D4)", GREEN, ["D4"]),
]


def abra_6_3():
    fig, ax = plt.subplots(figsize=(WIDTH_IN, 3.6))
    x = list(range(1, 11))
    bottom = [0.0] * 10
    for label, color, codes in GROUPS:
        h = [sum(AUTO[c][i] for c in codes) for i in range(10)]
        ax.bar(x, h, bottom=bottom, color=color, width=0.62, label=label,
               edgecolor="white", linewidth=1)
        if codes == ["B5"]:
            for xi, b, hi in zip(x, bottom, h):
                ax.text(xi, b + hi / 2, hu(hi, 1), ha="center", va="center",
                        color="white", fontsize=7, fontweight="bold")
        bottom = [b + hi for b, hi in zip(bottom, h)]
    for i, (xi, top) in enumerate(zip(x, bottom)):
        assert abs(top - A_TOTAL[i]) <= 1.0, (i + 1, top, A_TOTAL[i])  # a bontás zárt
        ax.text(xi, top + 2, hu(A_TOTAL[i]), ha="center", color=INK2, fontsize=8)
    ax.set_xticks(x)
    ax.set_xlabel("futtatás sorszáma")
    ax.set_ylabel("push → elfogadás (mp)")
    ax.set_ylim(0, 165)
    ax.set_title("Automatizált telepítés: a pipeline szakaszai futtatásonként", loc="left")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=2, fontsize=7.5)
    finish(ax)
    save(fig, "abra-6-3-auto-szakaszok")


# --- 6.4 ------------------------------------------------------------------
SEG = [  # (címke, szín)
    ("észlelés", VIOLET),
    ("kézi parancs (helm upgrade / helm rollback)", ORANGE),
    ("gépi kivárás (gördülő csere)", NEUTRAL),
    ("ellenőrzés (/version + füstteszt)", BLUE),
]


def abra_6_4():
    # Telepítési szakasz, kézi: a beállt szakasz medián futtatása (9–13. lépés).
    kd = [sum(STEP[str(s)][1][i] for s in range(9, 14)) for i in range(10)]
    ki = median_run(kd, BEALLT)
    k_dep = [0, STEP["9"][1][ki], STEP["10"][1][ki] + STEP["11"][1][ki],
             STEP["12"][1][ki] + STEP["13"][1][ki]]
    assert sum(k_dep) == kd[ki]
    # Telepítési szakasz, automatizált: a medián futtatás D2–D4 szakaszai.
    ai = median_run(A_DEPLOY, list(range(10)))
    # A D2 (0,1 mp) a deploy-start jelölő kiírása, nem kézi parancs: a kivárásba számít.
    a_dep = [0, 0, AUTO["D2"][ai] + AUTO["D3"][ai], AUTO["D4"][ai]]
    # Kiesés, kézi: a medián futtatás (hibás verzió él → helyreállt).
    hi = median_run(H_TOTAL, [0, 1, 2])
    k_out = [float(hiba[hi]["eszlelesi_mp"]), HSTEP["V2"][hi],
             HSTEP["V3"][hi] + HSTEP["V4"][hi], HSTEP["V5"][hi] + HSTEP["V6"][hi]]
    assert sum(k_out) == H_TOTAL[hi], (k_out, H_TOTAL[hi])
    # Kiesés, automatizált: észlelés + rollback --wait + a visszaállított verzió ellenőrzése.
    ahi = median_run(AH_TOTAL, [0, 1, 2])
    wait = float(re.search(r"rollback --wait [\d:]+ -> [\d:]+ \((\d+) mp\)",
                           ahiba[ahi]["megjegyzes"]).group(1))
    rest = float(ahiba[ahi]["helyreallitasi_mp"]) - wait
    a_out = [float(ahiba[ahi]["eszlelesi_mp"]), 0, wait, rest]
    assert sum(a_out) == AH_TOTAL[ahi]

    bars = [
        ("Telepítési szakasz\nkézi", k_dep, kd[ki]),
        ("Telepítési szakasz\nautomatizált", a_dep, A_DEPLOY[ai]),
        ("Kiesés hibás telepítés után\nkézi", k_out, H_TOTAL[hi]),
        ("Kiesés hibás telepítés után\nautomatizált", a_out, AH_TOTAL[ahi]),
    ]
    fig, ax = plt.subplots(figsize=(WIDTH_IN, 3.1))
    ypos = [3.6, 2.8, 1.0, 0.2]
    for yp, (_, segs, total) in zip(ypos, bars):
        left = 0.0
        for (lab, col), v in zip(SEG, segs):
            if v <= 0:
                continue
            ax.barh(yp, v, left=left, color=col, height=0.6, edgecolor="white", linewidth=1)
            txt = hu(v, 0 if v == int(v) else 1)
            if v >= 1.5:
                tc = INK if col == NEUTRAL else "white"
                ax.text(left + v / 2, yp, txt, ha="center",
                        va="center", color=tc, fontsize=7.5, fontweight="bold")
            left += v
        ax.text(left + 0.8, yp, f"{hu(total)} mp", va="center", color=INK, fontsize=8.5,
                fontweight="bold")
    ax.set_yticks(ypos)
    ax.set_yticklabels([b[0] for b in bars], fontsize=8)
    ax.set_xlim(0, 64)
    ax.set_xlabel("idő (mp) — a sorozat medián futtatásának bontása")
    ax.set_title("Kézi és automatizált út: hol tűnik el az idő", loc="left")
    ax.legend(handles=[Patch(color=c, label=lbl) for lbl, c in SEG], loc="upper center",
              bbox_to_anchor=(0.5, -0.2), ncol=2, fontsize=7.5)
    ax.grid(axis="x", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    save(fig, "abra-6-4-osszevetes")
    return ki + 1, ai + 1, hi + 1, ahi + 1


if __name__ == "__main__":
    print(f"kimenet: {OUT.relative_to(ROOT)}/")
    abra_6_1()
    abra_6_2()
    abra_6_3()
    runs = abra_6_4()
    print("6.4 medián futtatásai — kézi telepítés: %d., automatizált telepítés: %d., "
          "kézi kiesés: H%d, automatizált kiesés: A%d" % runs)
