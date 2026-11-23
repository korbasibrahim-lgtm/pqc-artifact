#!/usr/bin/env python3
"""Regenerate the data figures of the paper as vector PDFs.

All plotted values are read from derive_numbers.py, i.e. from the measured
tables of the paper. Update the tables there after a re-run and execute

    python3 make_figures.py <output_dir>

Figures are sized for one IEEE column (3.45 in) with 8 pt text.
"""
import sys
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

import derive_numbers as D

OUT = sys.argv[1] if len(sys.argv) > 1 else "."

# Okabe-Ito hues (validated for colour-vision deficiency); shape carries the
# same information so that the figures also read in greyscale.
BLUE, VERM, GREEN = "#0072B2", "#D55E00", "#009E73"
INK, MUTED, GRID = "#111111", "#555555", "#D9D9D9"
FAM = {  # family -> (colour, marker)
    "ML-DSA": (BLUE, "o"), "Falcon": (VERM, "s"), "SLH-DSA": (GREEN, "^"),
    "RSA": ("#4D4D4D", "D"), "ECDSA": (INK, "x"),
}

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Liberation Serif", "Times New Roman", "STIXGeneral"],  # TrueType, embeds cleanly
    "mathtext.fontset": "stix",
    "font.size": 8, "axes.labelsize": 8, "xtick.labelsize": 7, "ytick.labelsize": 7,
    "legend.fontsize": 7, "axes.linewidth": 0.6, "xtick.major.width": 0.6,
    "ytick.major.width": 0.6, "xtick.minor.width": 0.4, "ytick.minor.width": 0.4,
    "xtick.major.size": 2.5, "ytick.major.size": 2.5, "xtick.minor.size": 1.5,
    "ytick.minor.size": 1.5, "pdf.fonttype": 42, "ps.fonttype": 42,
    "axes.edgecolor": INK, "text.color": INK, "axes.labelcolor": INK,
    "xtick.color": INK, "ytick.color": INK, "savefig.pad_inches": 0.02,
})
W = 3.45


def family(name):
    for f in FAM:
        if name.startswith(f):
            return f
    raise KeyError(name)


def fig_size_speed():
    fig, ax = plt.subplots(figsize=(W, 2.3), layout="constrained")
    pts = [(n, v[2], v[4]) for n, v in D.SIG.items()]
    pts += [(n, v[2], v[0]) for n, v in D.CLS.items()]
    short = {"ML-DSA-44": "44", "ML-DSA-65": "65", "ML-DSA-87": "87", "Falcon-512": "512",
             "Falcon-1024": "1024", "SLH-DSA-128f": "128f", "SLH-DSA-192f": "192f",
             "SLH-DSA-256f": "256f", "RSA-2048": "2048", "RSA-3072": "3072", "RSA-4096": "4096",
             "ECDSA P-256": "P-256", "ECDSA P-384": "P-384"}
    off = {"ML-DSA-44": (0, -9), "ML-DSA-65": (4, -9), "ML-DSA-87": (0, 5),
           "Falcon-512": (0, -9), "Falcon-1024": (-7, 5), "SLH-DSA-128f": (0, -9),
           "SLH-DSA-192f": (10, -7), "SLH-DSA-256f": (-12, -2), "RSA-2048": (9, -3), "RSA-3072": (9, -3),
           "RSA-4096": (9, -3), "ECDSA P-256": (11, -3), "ECDSA P-384": (11, -3)}
    for n, x, y in pts:
        c, m = FAM[family(n)]
        ax.scatter(x, y, s=26 if m != "x" else 24, marker=m, color=c, linewidths=1.2 if m == "x" else 0.6,
                   edgecolors="white" if m != "x" else None, zorder=3)
        dx, dy = off[n]
        ax.annotate(short[n], (x, y), xytext=(dx, dy), textcoords="offset points", ha="center",
                    fontsize=6.5, color=INK, zorder=4)
    # family regions (log-space rounded boxes) with direct family labels
    # one region per post-quantum family; the regions are disjoint in the data
    for f, (x0, x1, y0, y1, lx, ly, ha) in {
        "ML-DSA":  (1980, 6400, 22, 400, 3560, 15, "center"),
        "Falcon":  (560, 1830, 60, 1000, 1010, 41, "center"),
        "SLH-DSA": (10500, 85000, 6800, 140000, 9300, 42000, "right"),
    }.items():
        c = FAM[f][0]
        ax.fill([x0, x1, x1, x0], [y0, y0, y1, y1], color=c, alpha=0.08, lw=0, zorder=1)
        ax.plot([x0, x1, x1, x0, x0], [y0, y0, y1, y1, y0], color=c, lw=0.7, ls=(0, (3, 2)), zorder=2)
        ax.text(lx, ly, f, color=INK, fontsize=7, ha=ha, va="center", style="italic")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlim(40, 1.1e5); ax.set_ylim(7, 1.8e5)
    ax.set_xlabel("Signature size (bytes)"); ax.set_ylabel(r"Mean signing time ($\mu$s)")
    ax.grid(True, which="major", color=GRID, lw=0.5, zorder=0); ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    h = [Line2D([], [], marker=m, color=c, ls="", ms=4.5, mew=1.1 if m == "x" else 0.5,
                mec=c if m == "x" else "white", label=f) for f, (c, m) in FAM.items()]
    ax.legend(handles=h, ncol=5, loc="lower center", bbox_to_anchor=(0.46, 1.0), frameon=False,
              handletextpad=0.1, columnspacing=0.9, borderaxespad=0.2)
    fig.savefig(f"{OUT}/fig_size_speed.pdf"); plt.close(fig)


def fig_level_match():
    tiers = [
        ("Tier 1", ["RSA-2048", "RSA-3072", "ECDSA P-256", "ML-DSA-44", "Falcon-512", "SLH-DSA-128f"]),
        ("Tier 3", ["ECDSA P-384", "ML-DSA-65", "SLH-DSA-192f"]),
        ("Tier 5", ["RSA-4096", "ML-DSA-87", "Falcon-1024", "SLH-DSA-256f"]),
    ]
    rows, y, seps, mids = [], 0.0, [], []
    for tname, algs in tiers:
        start = y
        for a in algs:
            sv = (D.SIG[a][4], D.SIG[a][5]) if a in D.SIG else D.CLS[a][:2]
            rows.append((y, a, sv)); y += 1.0
        mids.append((tname, (start + y - 1) / 2)); seps.append(y - 0.25); y += 0.5
    fig, ax = plt.subplots(figsize=(W, 2.5), layout="constrained")
    for yy, a, (s, v) in rows:
        ax.plot([s, v], [yy, yy], color="#9A9A9A", lw=0.8, zorder=2, solid_capstyle="round")
        ax.scatter(s, yy, s=22, marker="o", color=BLUE, edgecolors="white", linewidths=0.5, zorder=3)
        ax.scatter(v, yy, s=20, marker="s", facecolors="white", edgecolors=VERM, linewidths=1.0, zorder=3)
    ax.set_yticks([r[0] for r in rows]); ax.set_yticklabels([r[1] for r in rows])
    ax.set_ylim(rows[-1][0] + 0.7, -0.7)
    ax.set_xscale("log"); ax.set_xlim(8, 1.5e5)
    ax.set_xlabel(r"Mean time per operation ($\mu$s)")
    ax.grid(True, axis="x", which="major", color=GRID, lw=0.5); ax.set_axisbelow(True)
    for sy in seps[:-1]:
        ax.axhline(sy, color="#9A9A9A", lw=0.5, ls=(0, (2, 2)))
    for tname, my in mids:
        ax.text(1.2e5, my, tname, rotation=270, ha="center", va="center", fontsize=7, color=MUTED)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0)
    h = [Line2D([], [], marker="o", color=BLUE, ls="", ms=4.5, mec="white", mew=0.5, label="Sign"),
         Line2D([], [], marker="s", color=VERM, ls="", ms=4.2, mfc="white", mew=1.0, label="Verify")]
    ax.legend(handles=h, ncol=2, loc="lower center", bbox_to_anchor=(0.5, 1.0), frameon=False,
              handletextpad=0.2, columnspacing=1.4, borderaxespad=0.2)
    fig.savefig(f"{OUT}/fig_level_match.pdf"); plt.close(fig)


def fig_handshake():
    rows = [(n, (2 * pk + 3 * sg + ct) / 1000.0) for n, pk, sg, ct in D.FLIGHTS]
    rows.sort(key=lambda r: r[1])
    fam = lambda n: "ECDSA" if n.startswith("ECDSA") else family(n)
    fig, ax = plt.subplots(figsize=(W, 1.85), layout="constrained")
    budgets = [(3.6, "QUIC limit 3.6 kB", "right", -3), (14.6, "TCP window 14.6 kB", "left", 3)]
    for x, lab, ha, dx in budgets:
        ax.axvline(x, color=INK, lw=0.7, ls=(0, (4, 2)), zorder=1)
        ax.annotate(lab, (x, -0.62), xytext=(dx, 0), textcoords="offset points", ha=ha, va="center",
                    fontsize=6.5, color=INK)
    for i, (n, kb) in enumerate(rows):
        c, m = FAM[fam(n)]
        ax.plot([0.2, 60], [i, i], color=GRID, lw=0.5, zorder=0)
        ax.scatter(kb, i, s=26, marker=m, color=c, linewidths=1.2 if m == "x" else 0.6,
                   edgecolors="white" if m != "x" else None, zorder=3)
        ax.text(1.13, i, f"{kb:.1f}" if kb >= 1 else f"{kb:.2f}", ha="right", va="center", fontsize=7,
                color=INK, transform=ax.get_yaxis_transform())
    ax.set_yticks(range(len(rows))); ax.set_yticklabels([r[0] for r in rows])
    ax.set_ylim(len(rows) - 0.4, -1.05)
    ax.set_xscale("log"); ax.set_xlim(0.2, 60)
    ax.set_xticks([0.3, 1, 3, 10, 30]); ax.set_xticklabels(["0.3", "1", "3", "10", "30"])
    ax.minorticks_off()
    ax.set_xlabel("Server-flight payload (kB)")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0)
    fig.savefig(f"{OUT}/fig_handshake.pdf"); plt.close(fig)


if __name__ == "__main__":
    fig_size_speed(); fig_level_match(); fig_handshake()
    print("wrote fig_size_speed.pdf, fig_level_match.pdf, fig_handshake.pdf to", OUT)
