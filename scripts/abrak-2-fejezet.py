#!/usr/bin/env python3
"""A 2. fejezet két architektúraábrája: a kiindulási és a jelenlegi felállás.

Futtatás a repó gyökeréből:

    python3 scripts/abrak-2-fejezet.py

Kimenet: szakdolgozat/abrak/abra-2-N-*.png (300 dpi, a Word-dokumentumba) és
.pdf (vektoros).

A két ábra szándékosan ugyanazzal a jelölésrendszerrel készül (azonos színek,
azonos dobozformák, azonos nyíltípusok), mert a dolgozat a kettőt egymás mellett
hasonlítja össze; ha a jelölés eltérne, a különbség egy része a rajzból jönne,
nem a rendszerből. A tartalom forrásai:

- kiindulási felállás: platform/compose.yaml (kilenc szolgáltatás a laptopon),
  docs/adr/0001…0004, ansible/roles/deploy_app;
- jelenlegi felállás: README.md „Architecture", platform/compose.azure.yaml,
  chart/values.yaml és chart/templates/, terraform/main.tf és cloud-init.yaml,
  docs/adr/0008…0010.

A színek ugyanabból a palettából jönnek, mint a 6. fejezet ábráié
(scripts/abrak-6-fejezet.py).
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "szakdolgozat" / "abrak"

INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
BLUE, ORANGE, AQUA, VIOLET = "#2a78d6", "#eb6834", "#1baf7a", "#4a3aa7"
NEUTRAL = "#c3c2b7"

# Szerep → szín. Ugyanaz a szerep mindkét ábrán ugyanazt a színt kapja.
ROLE = {
    "cicd": BLUE,      # verziókezelő, futtató, konténerregiszter
    "app": ORANGE,     # az alkalmazás saját komponensei
    "data": AQUA,      # állapot (adatbázis, tartós tár)
    "obs": VIOLET,     # megfigyelés
    "ext": NEUTRAL,    # külső szolgáltatás, fejlesztői gép
}

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 7.5,
    "savefig.facecolor": "white",
    "figure.facecolor": "white",
})
WIDTH_IN = 6.3


def tint(hex_color: str, alpha: float) -> tuple[float, float, float]:
    """A szín világosított, átlátszatlan változata (nyomtatásban is tiszta)."""
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return (1 - alpha + alpha * r, 1 - alpha + alpha * g, 1 - alpha + alpha * b)


def frame(ax, x, y, w, h, title, dashed=False):
    """Határoló keret (gép, fürt, Compose-projekt)."""
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0,rounding_size=0.12",
        linewidth=0.9, edgecolor=INK2, facecolor="none",
        linestyle=(0, (4, 2.5)) if dashed else "solid", zorder=1))
    ax.text(x + 0.12, y + h - 0.1, title, ha="left", va="top",
            fontsize=7.5, fontweight="bold", color=INK2, zorder=2)


def box(ax, cx, cy, w, h, text, role):
    """Komponens: kitöltött doboz a szerep színével."""
    c = ROLE[role]
    ax.add_patch(FancyBboxPatch(
        (cx - w / 2, cy - h / 2), w, h,
        boxstyle="round,pad=0,rounding_size=0.08",
        linewidth=1.1, edgecolor=c, facecolor=tint(c, 0.16), zorder=3))
    ax.text(cx, cy, text, ha="center", va="center", fontsize=7.2,
            color=INK, zorder=4, linespacing=1.25)
    return (cx, cy, w, h)


def edge(b, side):
    cx, cy, w, h = b
    return {"l": (cx - w / 2, cy), "r": (cx + w / 2, cy),
            "t": (cx, cy + h / 2), "b": (cx, cy - h / 2)}[side]


def arrow(ax, p, q, label=None, dashed=False, lpos=0.5, loff=(0, 0.13),
          rad=0.0, ha="center"):
    ax.add_patch(FancyArrowPatch(
        p, q, arrowstyle="-|>", mutation_scale=8, linewidth=0.9,
        color=MUTED if dashed else INK2,
        linestyle=(0, (3, 2)) if dashed else "solid",
        connectionstyle=f"arc3,rad={rad}", shrinkA=1.5, shrinkB=1.5,
        zorder=5))
    if label:
        mx = p[0] + (q[0] - p[0]) * lpos + loff[0]
        my = p[1] + (q[1] - p[1]) * lpos + loff[1]
        ax.text(mx, my, label, ha=ha, va="center", fontsize=6.5,
                color=INK2, zorder=6,
                bbox=dict(boxstyle="square,pad=0.08", fc="white", ec="none"))


def legend(ax, y):
    """Jelmagyarázat két sorban, rögzített oszlopokkal."""
    rows = [
        [("cicd", "verziókezelés, futtató, regiszter"),
         ("app", "az alkalmazás komponensei"),
         ("data", "állapot")],
        [("obs", "megfigyelés"),
         ("ext", "külső szolgáltatás, fejlesztői gép")],
    ]
    cols = (0.15, 3.75, 7.15)
    for r, row in enumerate(rows):
        yy = y - r * 0.3
        for (role, text), x in zip(row, cols):
            c = ROLE[role]
            ax.add_patch(FancyBboxPatch(
                (x, yy - 0.07), 0.22, 0.14,
                boxstyle="round,pad=0,rounding_size=0.03",
                linewidth=1.0, edgecolor=c, facecolor=tint(c, 0.16)))
            ax.text(x + 0.3, yy, text, ha="left", va="center",
                    fontsize=6.5, color=INK2)
    yy = y - 0.3
    ax.plot([7.15, 7.45], [yy, yy], color=INK2, lw=0.9)
    ax.text(7.52, yy, "vezérlés, adat", va="center", fontsize=6.5, color=INK2)
    yy = y - 0.6
    ax.plot([0.15, 0.45], [yy, yy], color=MUTED, lw=0.9, linestyle=(0, (3, 2)))
    ax.text(0.52, yy, "megfigyelés (metrika, napló)", va="center",
            fontsize=6.5, color=INK2)


def canvas(height_in, ymax):
    fig, ax = plt.subplots(figsize=(WIDTH_IN, height_in))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, ymax)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.subplots_adjust(left=0.005, right=0.995, top=0.995, bottom=0.005)
    return fig, ax


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{name}.png", dpi=300)
    fig.savefig(OUT / f"{name}.pdf")
    plt.close(fig)


def abra_kiindulasi():
    """A gyakornoki felállás: minden a laptopon, a cél egy Docker-host."""
    fig, ax = canvas(4.0, 6.35)

    gh = box(ax, 1.05, 4.85, 1.7, 0.62, "GitHub\nkódáttekintés", "ext")
    dev = box(ax, 1.05, 2.9, 1.7, 0.62, "fejlesztői\nmunkapéldány (git)", "ext")

    frame(ax, 2.25, 1.1, 7.6, 5.15, "Laptop (Docker Desktop)")
    frame(ax, 2.45, 2.75, 7.2, 3.1,
          "Docker Compose-projekt (platform/compose.yaml)", dashed=True)
    gitea = box(ax, 3.4, 4.85, 1.5, 0.62, "Gitea\n+ Gitea Actions", "cicd")
    runner = box(ax, 5.5, 4.85, 1.6, 0.62, "act_runner\n(Docker-foglalattal)", "cicd")
    reg = box(ax, 8.6, 4.85, 1.7, 0.62, "konténerregiszter\nlocalhost:5001", "cicd")
    obs = box(ax, 7.0, 3.45, 1.8, 0.95,
              "Prometheus · Loki\nAlloy · Grafana\ncAdvisor · node-exp.",
              "obs")

    appc = box(ax, 6.4, 1.75, 3.4, 0.72,
               "alkalmazáskonténer: Flask · Gunicorn\n(egyetlen konténer, állapot nélkül)",
               "app")

    arrow(ax, edge(dev, "t"), edge(gh, "b"), "egyesítési\nkérelem", loff=(0, 0))
    arrow(ax, edge(dev, "r"), (2.65, 4.7), "git push", lpos=0.55,
          loff=(0.12, -0.05), rad=-0.25, ha="left")
    arrow(ax, edge(gitea, "r"), edge(runner, "l"), "feladat", loff=(0, 0.17))
    arrow(ax, edge(runner, "r"), edge(reg, "l"), "push\n(SHA-címke)",
          loff=(0, 0.3))
    arrow(ax, (5.5, 4.54), (5.5, 2.11), "Ansible deploy_app\n(community.docker)",
          lpos=0.55, loff=(-0.1, 0), ha="right")
    arrow(ax, (8.6, 4.54), (7.95, 2.11), "pull", lpos=0.62, loff=(0.12, 0),
          ha="left")
    arrow(ax, edge(obs, "b"), (7.0, 2.11), dashed=True)

    legend(ax, 0.75)
    save(fig, "abra-2-1-kiindulasi-architektura")


def abra_jelenlegi():
    """A szakdolgozati felállás: Terraformmal létrehozott Azure-gép, k3s, Helm."""
    fig, ax = canvas(4.45, 7.05)

    gh = box(ax, 1.05, 5.5, 1.7, 0.62, "GitHub\nkódáttekintés", "ext")
    dev = box(ax, 1.05, 3.5, 1.7, 0.82,
              "laptop:\nmunkapéldány (git),\nk3d fejlesztőfürt", "ext")

    frame(ax, 2.25, 1.1, 7.6, 5.85,
          "Azure-beli virtuális gép (Terraform, cloud-init) · Standard_B2s_v2")
    frame(ax, 2.45, 3.8, 7.2, 2.75,
          "Docker Compose-projekt (compose.yaml + compose.azure.yaml)",
          dashed=True)
    gitea = box(ax, 3.4, 5.5, 1.5, 0.62, "Gitea\n+ Gitea Actions", "cicd")
    runner = box(ax, 5.5, 5.5, 1.6, 0.62, "act_runner\n(Docker-foglalattal)", "cicd")
    reg = box(ax, 8.6, 5.5, 1.7, 0.62, "konténerregiszter\nlocalhost:5001", "cicd")
    obs = box(ax, 7.0, 4.4, 1.8, 0.8,
              "Prometheus · Loki\nAlloy · Grafana\n(observability profil)",
              "obs")

    frame(ax, 2.45, 1.3, 7.2, 2.15,
          "k3s-fürt (egy csomópont) · Helm-kiadás: projecta")
    ing = box(ax, 3.3, 2.4, 1.4, 0.62, "Traefik\n(ingress)", "app")
    fe = box(ax, 5.0, 2.4, 1.5, 0.62, "frontend ×2\nnginx", "app")
    be = box(ax, 7.0, 2.4, 1.7, 0.62, "backend ×2\nFlask · Gunicorn", "app")
    pg = box(ax, 8.95, 1.85, 1.1, 0.62, "PostgreSQL\n(PVC)", "data")

    arrow(ax, edge(dev, "t"), edge(gh, "b"), "egyesítési\nkérelem", loff=(0, 0))
    arrow(ax, (1.9, 3.6), (2.65, 5.35), "git push\nSSH-alagúton", lpos=0.55,
          loff=(0.12, -0.05), rad=-0.25, ha="left")
    arrow(ax, edge(gitea, "r"), edge(runner, "l"), "feladat", loff=(0, 0.17))
    arrow(ax, edge(runner, "r"), edge(reg, "l"), "push\n(SHA-címke)",
          loff=(0, 0.3))
    arrow(ax, (5.5, 5.19), (5.5, 3.45), "helm upgrade --wait\nhelm rollback",
          lpos=0.5, loff=(-0.1, 0), ha="right")
    arrow(ax, (8.95, 5.19), (8.95, 3.45), "pull", lpos=0.5, loff=(0.1, 0),
          ha="left")
    arrow(ax, edge(obs, "b"), (7.0, 3.45), dashed=True, label="felderítés,\npodnaplók",
          lpos=0.5, loff=(0.1, 0), ha="left")
    arrow(ax, edge(ing, "r"), edge(fe, "l"))
    arrow(ax, edge(fe, "r"), edge(be, "l"), "/api/", loff=(0, 0.2))
    arrow(ax, (7.7, 2.09), edge(pg, "l"), rad=0.2)

    legend(ax, 0.75)
    save(fig, "abra-2-2-jelenlegi-architektura")


if __name__ == "__main__":
    abra_kiindulasi()
    abra_jelenlegi()
