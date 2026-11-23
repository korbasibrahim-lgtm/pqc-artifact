#!/usr/bin/env python3
"""Compare measured ML-DSA signing latency with the model of Section V-B.

Input: a directory with the per-signature samples written by sig_latency
(<alg>.ns, one time in nanoseconds per line), e.g. the latency/ directory
produced by run_campaign.sh.

For each ML-DSA parameter set the script
  * computes the measured mean, CV and percentiles,
  * fits T = a + b*K, K ~ Geometric(1/r), to the measured mean and CV with
    r taken from FIPS 204 (the same fit as in the paper),
  * cross-checks that fit with a second estimate that does not use the
    moments: the model says that the fraction 1-(1-1/r)^k of signatures
    finishes within k iterations, so the median of each such rank band is
    the latency of level k, and a straight line through the levels gives
    a and b. The two estimates agree on a quiet host; if timing noise
    inflates the standard deviation, the moment fit drifts and a warning
    is printed,
  * prints measured against model quantiles as LaTeX table rows, and
  * writes fig_latency.pdf: the measured histogram with the model's
    probability mass at a + b*k drawn over it.

Usage: python3 plot_latency.py <latency_dir> [output_dir]
"""
import math
import os
import sys

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPS = {"ML-DSA-44": 4.25, "ML-DSA-65": 5.1, "ML-DSA-87": 3.85}  # FIPS 204, Table 1
QS = (0.95, 0.99, 0.999)
BLUE, VERM, INK, GRID = "#0072B2", "#D55E00", "#111111", "#D9D9D9"

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Liberation Serif", "Times New Roman", "STIXGeneral"],
    "mathtext.fontset": "stix", "font.size": 8, "axes.labelsize": 8, "xtick.labelsize": 7,
    "ytick.labelsize": 7, "legend.fontsize": 7, "axes.linewidth": 0.6, "pdf.fonttype": 42,
})


def fit(mean, cv, r):
    b = cv * mean / math.sqrt(r * (r - 1.0))
    return mean - b * r, b


def fit_levels(t_sorted, r, levels=8):
    """Estimate a and b from the latency levels, without using the moments."""
    n, p = len(t_sorted), 1.0 / r
    ks, pos = [], []
    for k in range(1, levels + 1):
        lo, hi = 1.0 - (1.0 - p) ** (k - 1), 1.0 - (1.0 - p) ** k
        band = t_sorted[int(lo * n):int(hi * n)]
        if len(band) < 50:
            break
        ks.append(k)
        pos.append(np.median(band))
    b, a = np.polyfit(ks, pos, 1)
    return a, b


def model_quantile(a, b, r, q):
    return a + b * math.ceil(math.log(1.0 - q) / math.log(1.0 - 1.0 / r))


def main():
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else src
    algs = [a for a in REPS if os.path.exists(os.path.join(src, a + ".ns"))]
    if not algs:
        sys.exit(f"no ML-DSA sample files (<alg>.ns) found in {src}")
    fig, axes = plt.subplots(len(algs), 1, figsize=(3.45, 1.25 * len(algs) + 0.35),
                             layout="constrained", squeeze=False)
    print("% algorithm & mean & CV(%) & " + " & ".join(f"p{q*100:g} meas. & model" for q in QS) + r" \\")
    for ax, alg in zip(axes[:, 0], algs):
        t = np.loadtxt(os.path.join(src, alg + ".ns")) / 1000.0     # microseconds
        r = REPS[alg]
        mean, sd = t.mean(), t.std()
        a, b = fit(mean, sd / mean, r)
        a2, b2 = fit_levels(np.sort(t), r)
        cells = []
        for q in QS:
            cells.append(f"{np.percentile(t, 100*q, method='inverted_cdf'):.0f} & {model_quantile(a, b, r, q):.0f}")
        print(f"{alg} & {mean:.1f} & {100*sd/mean:.1f} & " + " & ".join(cells) + r" \\"
              + f"   % moment fit a={a:.1f}, b={b:.1f} us; level fit a={a2:.1f}, b={b2:.1f} us; n={len(t)}")
        if abs(b - b2) > 0.15 * b2:
            print(f"% WARNING {alg}: moment fit and level fit differ by more than 15%: timing noise is"
                  " inflating the standard deviation. Pin the process, use the performance governor,"
                  " or quote the level fit. The figure is drawn with the level fit.")
            a, b = a2, b2
        hi = model_quantile(a, b, r, 0.999) * 1.05
        bins = np.linspace(0, hi, 240)
        ax.hist(t[t <= hi], bins=bins, density=True, color=BLUE, alpha=0.55, lw=0, label="measured")
        ks = np.arange(1, int((hi - a) / b) + 1)
        pk = (1.0 / r) * (1.0 - 1.0 / r) ** (ks - 1)
        # scale probability mass to the histogram's density units
        ax.vlines(a + b * ks, 0, pk / (bins[1] - bins[0]) * 0.35, color=VERM, lw=0.8)
        for q, ls in zip((0.95, 0.99), ((0, (4, 2)), (0, (1, 1.5)))):
            ax.axvline(model_quantile(a, b, r, q), color=INK, lw=0.6, ls=ls)
        ax.set_xlim(0, hi)
        ax.set_yticks([])
        ax.set_ylabel(alg, fontsize=7)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    axes[0, 0].legend(handles=[Patch(fc=BLUE, alpha=0.55, lw=0, label="measured"),
                               Line2D([], [], color=VERM, lw=0.8, label=r"model mass at $a+bk$ (scaled)")],
                      frameon=False, loc="upper right")
    axes[-1, 0].set_xlabel(r"Signing time ($\mu$s); dashed and dotted lines: model $t_{0.95}$, $t_{0.99}$")
    path = os.path.join(out, "fig_latency.pdf")
    fig.savefig(path)
    print("wrote", path)


if __name__ == "__main__":
    main()
