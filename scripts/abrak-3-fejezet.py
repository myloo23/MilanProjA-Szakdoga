#!/usr/bin/env python3
"""A 3. fejezet ábrája: a Helm-kiadás objektumai a k3s-fürtben.

Futtatás a repó gyökeréből:

    python3 scripts/abrak-3-fejezet.py

Kimenet: szakdolgozat/abrak/abra-3-1-helm-kiadas-objektumai.png (300 dpi) és
.pdf (vektoros).

A jelölésrendszer (színek, dobozok, nyilak) a 2. fejezet ábráiéval azonos: a
segédfüggvények a scripts/abrak-2-fejezet.py-ból jönnek, nem másolatként, hogy
a két fejezet ábrái ne térhessenek el egymástól. A tartalom forrásai:
chart/values.yaml, chart/templates/*.yaml, frontend/nginx.conf.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

from matplotlib.patches import FancyBboxPatch

_spec = importlib.util.spec_from_file_location(
    "abrak2", Path(__file__).resolve().parent / "abrak-2-fejezet.py")
a2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(a2)

box, frame, arrow, edge, canvas, save = (
    a2.box, a2.frame, a2.arrow, a2.edge, a2.canvas, a2.save)
ROLE, INK2, MUTED, tint = a2.ROLE, a2.INK2, a2.MUTED, a2.tint


def legend(ax, y):
    items = [("app", "az alkalmazás objektumai"),
             ("data", "állapot és séma"),
             ("cicd", "konténerregiszter"),
             ("ext", "nem a chart része (kézzel létrehozva)")]
    cols = (0.15, 3.0, 5.55, 0.15)
    rows = (0, 0, 0, 1)
    for (role, text), x, r in zip(items, cols, rows):
        yy = y - r * 0.3
        c = ROLE[role]
        ax.add_patch(FancyBboxPatch(
            (x, yy - 0.07), 0.22, 0.14,
            boxstyle="round,pad=0,rounding_size=0.03",
            linewidth=1.0, edgecolor=c, facecolor=tint(c, 0.16)))
        ax.text(x + 0.3, yy, text, ha="left", va="center",
                fontsize=6.5, color=INK2)
    yy = y - 0.3
    ax.plot([5.55, 5.85], [yy, yy], color=INK2, lw=0.9)
    ax.text(5.92, yy, "kérés, adat", va="center", fontsize=6.5, color=INK2)
    ax.plot([7.45, 7.75], [yy, yy], color=MUTED, lw=0.9, linestyle=(0, (3, 2)))
    ax.text(7.82, yy, "hivatkozás, letöltés", va="center", fontsize=6.5,
            color=INK2)


def abra_kiadas():
    fig, ax = canvas(4.75, 7.55)

    c1, c2, c3, c4 = 3.0, 4.8, 6.9, 9.05
    r1, r2, r3, r4 = 5.45, 4.05, 2.75, 1.5
    w3, w4 = 2.4, 1.6

    browser = box(ax, 0.95, r1, 1.5, 0.62, "böngésző", "ext")
    reg = box(ax, c3, 7.05, 2.9, 0.55,
              "konténerregiszter · localhost:5001", "cicd")

    frame(ax, 1.95, 0.95, 7.95, 5.75,
          "k3s-fürt (egy csomópont) · Helm-kiadás: projecta")

    ing = box(ax, c1, r1, 1.45, 0.62, "Ingress\n(Traefik)", "app")
    sfe = box(ax, c2, r1, 1.45, 0.62, "Service\nfrontend :80", "app")
    dfe = box(ax, c3, r1, w3, 0.8,
              "Deployment frontend ×2\nnginx :8080\nélő/kész: /healthz", "app")

    sbe = box(ax, c2, r2, 1.45, 0.62, "Service\nbackend :80", "app")
    dbe = box(ax, c3, r2, w3, 0.8,
              "Deployment backend ×2\nGunicorn :8000\nélő: /health · kész: /ready",
              "app")
    mig = box(ax, c3, r3, w3, 0.62,
              "init container: migrate\n(minden backend-pod előtt)", "app")
    cm = box(ax, c4, r3, w4, 0.62, "ConfigMap\ndb-schema", "data")
    box(ax, c1 - 0.05, r3, 1.75, 1.0,
        "Secret\ndb-credentials\n(backend, migrate,\npostgres)", "ext")

    spg = box(ax, c2, r4, 1.45, 0.62, "Service\npostgres :5432", "data")
    dpg = box(ax, c3, r4, w3, 0.62,
              "Deployment postgres ×1\nstratégia: Recreate", "data")
    pvc = box(ax, c4, r4, w4, 0.8,
              "PVC postgres-data\n2Gi · keep\n(local-path)", "data")

    arrow(ax, edge(browser, "r"), edge(ing, "l"), "HTTP :80", loff=(0, 0.17))
    arrow(ax, edge(ing, "r"), edge(sfe, "l"))
    arrow(ax, edge(sfe, "r"), edge(dfe, "l"))
    arrow(ax, (c3 - 0.7, r1 - 0.4), (c2 + 0.45, r2 + 0.31),
          "/api/ (előtag\nlevágva)", lpos=0.4, loff=(0.5, 0.08), ha="left")
    arrow(ax, edge(sbe, "r"), edge(dbe, "l"))
    arrow(ax, edge(dbe, "b"), edge(mig, "t"), "előtte lefut",
          loff=(0.1, 0), ha="left", dashed=True)
    arrow(ax, edge(cm, "l"), edge(mig, "r"), dashed=True)
    arrow(ax, (c3 - w3 / 2, r2 - 0.25), (c2 - 0.15, r4 + 0.31),
          "psycopg", lpos=0.5, loff=(-0.1, 0),
          ha="right", rad=0.22)
    arrow(ax, (c3 - 0.75, r3 - 0.31), (c2 + 0.45, r4 + 0.31), "psql",
          lpos=0.45, loff=(0.22, 0.05), ha="left")
    arrow(ax, edge(spg, "r"), edge(dpg, "l"))
    arrow(ax, edge(dpg, "r"), edge(pvc, "l"))

    # A regiszterből a két saját kép jön, közös címkével.
    arrow(ax, (c3 + 0.65, 7.05 - 0.28), (c3 + 0.65, r1 + 0.4), dashed=True,
          label="pull (IfNotPresent),\nközös image.tag", lpos=0.45,
          loff=(0.12, 0), ha="left")
    arrow(ax, (c3 + 1.3, 7.05 - 0.2), (c3 + w3 / 2, r2 + 0.1), dashed=True,
          rad=-0.3)

    legend(ax, 0.62)
    save(fig, "abra-3-1-helm-kiadas-objektumai")


if __name__ == "__main__":
    abra_kiadas()
