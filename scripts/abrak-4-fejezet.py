#!/usr/bin/env python3
"""A 4. fejezet ábrája: a telepítési lánc két feladata (job) és lépései.

Futtatás a repó gyökeréből:

    python3 scripts/abrak-4-fejezet.py

Kimenet: szakdolgozat/abrak/abra-4-1-telepitesi-lanc.png (300 dpi) és .pdf.

Forrás: .gitea/workflows/ci.yml. A szaggatott keretű lépések a mérés után
kerültek be (naplo 3.2), a mért lánc (e4da1d9) nem tartalmazta őket; az ábra
ezt jelöli, hogy a 4. és az 5. fejezet ugyanarról a láncról beszéljen.
A jelölésrendszer a 2–3. fejezet ábráiéval azonos (scripts/abrak-2-fejezet.py).
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

from matplotlib.patches import FancyBboxPatch

_spec = importlib.util.spec_from_file_location(
    "abrak2", Path(__file__).resolve().parent / "abrak-2-fejezet.py")
a2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(a2)

frame, arrow, canvas, save = a2.frame, a2.arrow, a2.canvas, a2.save
INK, INK2, MUTED, tint = a2.INK, a2.INK2, a2.MUTED, a2.tint
KIND = {"step": a2.BLUE, "gate": a2.ORANGE, "back": a2.VIOLET, "ok": a2.AQUA}


def step(ax, cx, cy, w, h, text, kind, later=False):
    c = KIND[kind]
    ax.add_patch(FancyBboxPatch(
        (cx - w / 2, cy - h / 2), w, h,
        boxstyle="round,pad=0,rounding_size=0.07",
        linewidth=1.1, edgecolor=c,
        facecolor="white" if later else tint(c, 0.16),
        linestyle=(0, (3, 2)) if later else "solid", zorder=3))
    ax.text(cx, cy, text, ha="center", va="center", fontsize=6.9,
            color=INK, zorder=4, linespacing=1.2)
    return (cx, cy, w, h)


def legend(ax, y):
    items = [("step", "előállítás, telepítés", False),
             ("gate", "minőségi kapu (bukása megállítja a láncot)", False),
             ("back", "visszaállítás", False),
             ("ok", "eredmény", False)]
    xs = (0.15, 2.75, 7.05, 8.75)
    for (kind, text, _), x in zip(items, xs):
        c = KIND[kind]
        ax.add_patch(FancyBboxPatch(
            (x, y - 0.07), 0.22, 0.14,
            boxstyle="round,pad=0,rounding_size=0.03",
            linewidth=1.0, edgecolor=c, facecolor=tint(c, 0.16)))
        ax.text(x + 0.3, y, text, ha="left", va="center", fontsize=6.5,
                color=INK2)
    yy = y - 0.3
    ax.add_patch(FancyBboxPatch(
        (0.15, yy - 0.07), 0.22, 0.14,
        boxstyle="round,pad=0,rounding_size=0.03", linewidth=1.0,
        edgecolor=INK2, facecolor="white", linestyle=(0, (3, 2))))
    ax.text(0.45, yy, "a mérés után került be, a mért lánc (e4da1d9) nem "
            "tartalmazta", ha="left", va="center", fontsize=6.5, color=INK2)


def abra_lanc():
    fig, ax = canvas(6.1, 9.7)

    # Bal oldal: build-test-push
    lx, lw, h, dy = 2.55, 4.5, 0.46, 0.62
    frame(ax, 0.15, 1.2, 4.85, 8.0,
          "1. feladat: build-test-push (minden push)")
    y = 8.5
    L = []
    L.append(step(ax, lx, y, lw, h,
                  "ref-kapu: kiadható-e az ág? (main, release/*)\n"
                  "képcímke = a commit rövid azonosítója", "step"))
    rows = [
        ("Ruff (kódstílus)", "gate", False),
        ("titokkeresés a kódfán (Trivy fs)", "gate", False),
        ("hadolint: backend Dockerfile", "gate", False),
        ("hadolint: frontend Dockerfile", "gate", True),
        ("pytest, ≥ 80 % lefedettség", "gate", False),
        ("ansible-lint", "gate", False),
        ("két kép összeállítása (GIT_SHA → APP_VERSION)", "step", False),
        ("konténerpróba: HEALTHCHECK, elérés hálózaton", "gate", False),
        ("Trivy: backend kép (HIGH, CRITICAL)", "gate", False),
        ("Trivy: frontend kép (HIGH, CRITICAL)", "gate", True),
    ]
    for text, kind, later in rows:
        y -= dy
        L.append(step(ax, lx, y, lw, h, text, kind, later))
    for a, b in zip(L, L[1:]):
        arrow(ax, (a[0], a[1] - a[3] / 2), (b[0], b[1] + b[3] / 2))
    y -= dy
    push = step(ax, lx, y, lw, h,
                "push a regiszterbe: két kép, közös címke\n(csak kiadható ágon)",
                "step")
    arrow(ax, (L[-1][0], L[-1][1] - h / 2), (push[0], push[1] + h / 2))

    # Jobb oldal: deploy
    rx, rw = 7.5, 4.3
    frame(ax, 5.3, 1.2, 4.55, 8.0,
          "2. feladat: deploy (needs, csak kiadható ágon)")
    r1 = step(ax, rx, 8.5, rw, h,
              "a futó kiadás címkéjének rögzítése\n(PREV_TAG, helm get values)",
              "step")
    r2 = step(ax, rx, 7.35, rw, 0.62,
              "helm upgrade --install --wait\n--set image.tag=<commit>\n"
              "(nem --atomic)", "step")
    r3 = step(ax, rx, 6.05, rw, 0.82,
              "telepítés utáni ellenőrzés a bejáraton át\n"
              "(verify.yml: /health, /ready, /version = commit,\n"
              "/echo négy esete)", "gate")
    ok = step(ax, 6.35, 4.55, 1.8, 0.55, "elfogadva\n(zöld futás)", "ok")
    rb = step(ax, 8.55, 4.4, 2.3, 0.85,
              "helm rollback --wait\nújraellenőrzés a PREV_TAG\nellen", "back")
    red = step(ax, 8.55, 3.05, 2.3, 0.55,
               "a futás piros marad:\nvisszaállt, nem szállított", "ok")

    arrow(ax, (rx, r1[1] - h / 2), (rx, r2[1] + 0.31))
    arrow(ax, (rx, r2[1] - 0.31), (rx, r3[1] + 0.41))
    arrow(ax, (6.35, r3[1] - 0.41), (6.35, ok[1] + 0.275), "siker",
          lpos=0.5, loff=(-0.1, 0), ha="right")
    arrow(ax, (8.55, r3[1] - 0.41), (8.55, rb[1] + 0.425), "bukás",
          lpos=0.5, loff=(0.1, 0), ha="left")
    arrow(ax, (8.55, rb[1] - 0.425), (8.55, red[1] + 0.275))

    # A két feladat kapcsolata: ugyanaz a kép, nem épül újra.
    arrow(ax, (push[0] + lw / 2, push[1]), (5.55, push[1]), dashed=True)
    ax.text(5.6, push[1] + 0.1, "needs: a deploy csak a push után indul,\n"
            "és ugyanazt a képet telepíti a regiszterből", ha="left",
            va="center", fontsize=6.5, color=INK2)

    legend(ax, 0.62)
    save(fig, "abra-4-1-telepitesi-lanc")


if __name__ == "__main__":
    abra_lanc()
