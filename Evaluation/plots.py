"""Genere les figures + tableau de synthese a partir de results/*.jsonl -> figures/

Comparaisons : Local_Search vs Local_Search_DP  |  Global_Greedy vs Greedy_Ratio
"""
import json
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
FIG = HERE / "figures"
FIG.mkdir(exist_ok=True)

SURF, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
COL = {"greedy": "#1baf7a", "gratio": "#e87ba4", "ls": "#eb6834", "dp": "#2a78d6"}
NAME = {"greedy": "Global_Greedy", "gratio": "Greedy_Ratio", "ls": "Local_Search", "dp": "Local_Search_DP"}

plt.rcParams.update({
    "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
    "text.color": INK, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.edgecolor": GRID, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "axes.axisbelow": True,
    "font.size": 13, "axes.titlesize": 15, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "legend.frameon": False, "lines.linewidth": 2.2,
})


def load():
    recs = []
    for f in HERE.glob("results/*.jsonl"):
        recs += [json.loads(l) for l in f.read_text(encoding="utf8").splitlines()]
    return recs


def save(fig, name):
    fig.savefig(FIG / name, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("->", name)


def human(n):
    return f"{n/1e6:.1f}M" if n >= 1e6 else f"{n/1e3:.0f}k" if n >= 1e3 else str(n)


def main():
    recs = load()
    main_r = [r for r in recs if r["tag"] == "main"]
    sens = [r for r in recs if r["tag"] == "sens"]
    by = defaultdict(list)
    for r in main_r:
        by[(r["algo"], r["instance"])].append(r)
    insts = sorted({r["instance"] for r in main_r})
    meta = {i: next(r for r in main_r if r["instance"] == i) for i in insts}
    size = {i: meta[i]["V"] * meta[i]["C"] for i in insts}
    insts.sort(key=lambda i: size[i])                       # petit -> grand
    lab = lambda i: i.replace("instance", "#")
    sc = lambda a, i: np.array([r["score"] for r in by[(a, i)]], float)
    has = lambda a, i: len(by[(a, i)]) > 0
    ls_pair = [i for i in insts if has("ls", i) and has("dp", i)]
    gr_pair = [i for i in insts if has("greedy", i) and has("gratio", i)]
    skipped = [lab(i) for i in insts if i not in ls_pair]

    # ---- tableau ----
    rows = ["| Instance | V | E | C | X | Requêtes | Global_Greedy | Greedy_Ratio | Local_Search | Local_Search_DP (moy ± σ) | Δ GR vs GG | Δ DP vs LS |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    fmt = lambda a, i: f"{sc(a, i).mean():,.0f}" if has(a, i) else "n/a"
    for i in insts:
        m = meta[i]
        dgr = f"{100*(sc('gratio', i).mean()/sc('greedy', i).mean()-1):+.1f}%" if i in gr_pair else "n/a"
        ddp = f"{100*(sc('dp', i).mean()/sc('ls', i).mean()-1):+.1f}%" if i in ls_pair else "n/a (X trop grand)"
        dp = f"{sc('dp', i).mean():,.0f} ± {sc('dp', i).std():,.0f}" if has("dp", i) else "n/a"
        rows.append(f"| {lab(i)} | {m['V']} | {m['E']} | {m['C']} | {m['X']} | {m['R']:,} | {fmt('greedy', i)} | {fmt('gratio', i)} | {fmt('ls', i)} | {dp} | {dgr} | {ddp} |")
    (HERE / "summary.md").write_text("\n".join(rows), encoding="utf8")

    # ---- Fig 1 : score final = gain relatif de l'algo avance sur l'algo de base ----
    def gain_panel(ax, pair, base, adv, title):
        y = np.arange(len(pair))
        g = [100 * (sc(adv, i).mean() / sc(base, i).mean() - 1) for i in pair]
        err = None
        if len(by[(adv, pair[0])]) > 1:
            err = [[100 * (sc(adv, i).mean() - sc(adv, i).min()) / sc(base, i).mean() for i in pair],
                   [100 * (sc(adv, i).max() - sc(adv, i).mean()) / sc(base, i).mean() for i in pair]]
        ax.barh(y, g, color=COL[adv], height=0.65, xerr=err, error_kw=dict(ecolor=INK2, lw=1.2, capsize=2))
        top = max(g + [1])
        for yi, gi in zip(y, g):
            ax.text(gi + (0.01 * top if gi >= 0 else -0.01 * top), yi, ("≈ 0" if abs(gi) < 0.05 else f"{gi:+.1f}%"), va="center",
                    ha="left" if gi >= 0 else "right", fontsize=11, color=INK)
        ax.set_yticks(y, [f"{lab(i)}  (V×C={human(size[i])})" for i in pair]); ax.invert_yaxis()
        ax.axvline(0, color=INK2, lw=1)
        lo = min(g + [0]); ax.set_xlim(lo * 1.4 if lo < 0 else 0, top * 1.18)
        ax.set_xlabel(f"Gain de score de {NAME[adv]} sur {NAME[base]} (%)"); ax.set_title(title)

    fig, axs = plt.subplots(1, 2, figsize=(16, 6.2))
    gain_panel(axs[0], ls_pair, "ls", "dp", "Recherche locale : DP vs ratio")
    gain_panel(axs[1], gr_pair, "greedy", "gratio", "Gloutons : Greedy_Ratio vs Global_Greedy")
    if skipped:
        axs[0].text(0.99, 0.02, f"{', '.join(skipped)} : DP infaisable (X = 6·10⁸)", transform=axs[0].transAxes,
                    ha="right", va="bottom", fontsize=10, color=INK2)
    fig.tight_layout(); save(fig, "1_score_final.png")

    # ---- Fig 2a : convergence Local_Search vs Local_Search_DP (axe temps lineaire) ----
    def t_reach(r, frac):
        fin = r["curve"][-1][1]
        return next((t for t, s in r["curve"] if s >= frac * fin), r["curve"][-1][0])
    pick = [i for i in ["instance01", "instance04", "instance09", "instance15", "instance10", "instance11"] if i in ls_pair]
    fig, axs = plt.subplots(2, 3, figsize=(15, 8))
    for ax, i in zip(axs.flat, pick):
        ref = sc("dp", i).mean()
        t_end_ls = by[("ls", i)][0]["curve"][-1][0]
        t_dp = max(t_reach(r, 0.999) for r in by[("dp", i)])
        horizon = float(np.clip(max(t_dp, t_end_ls) * 1.4, 5, 120))
        grid = np.linspace(0, horizon, 600)
        curves = []
        for r in by[("dp", i)]:
            t = np.array([p[0] for p in r["curve"]]); s = np.array([p[1] for p in r["curve"]], float)
            idx = np.searchsorted(t, grid, side="right") - 1
            curves.append(np.where(idx >= 0, s[np.clip(idx, 0, None)], np.nan))
        c = np.array(curves) / ref * 100
        mean = np.nanmedian(c, 0)
        ax.plot(grid, mean, color=COL["dp"], label=NAME["dp"] + " (médiane des seeds)")
        ax.fill_between(grid, np.nanmin(c, 0), np.nanmax(c, 0), color=COL["dp"], alpha=0.2, lw=0)
        r = by[("ls", i)][0]
        t = np.array([p[0] for p in r["curve"]]); s = np.array([p[1] for p in r["curve"]], float) / ref * 100
        ax.step(t, s, where="post", color=COL["ls"], label=NAME["ls"])
        ax.plot([t[-1]], [s[-1]], "o", color=COL["ls"])
        ax.set_xlim(0, horizon)
        ax.set_ylim(max(min(s[-1], 97) - 6, 0), 101)
        ax.set_title(f"{lab(i)}  (V={meta[i]['V']}, C={meta[i]['C']})", fontsize=13); ax.set_xlabel("Temps (s)")
    axs[0, 0].set_ylabel("% du score final de Local_Search_DP"); axs[1, 0].set_ylabel("% du score final de Local_Search_DP")
    h, l = axs[0, 0].get_legend_handles_labels()
    fig.legend(h, l, ncol=2, loc="upper center", bbox_to_anchor=(0.5, 1.0))
    fig.tight_layout(rect=(0, 0, 1, 0.95)); save(fig, "2a_convergence_ls_dp.png")

    # ---- Fig 2b : gloutons = temps d'execution + qualite (algos constructifs, pas de courbe) ----
    fig, axs = plt.subplots(1, 2, figsize=(16, 9.5), sharey=True)
    y = np.arange(len(gr_pair)); h = 0.4
    for k, a in enumerate(["greedy", "gratio"]):
        tt = [by[(a, i)][0]["run_s"] for i in gr_pair]
        axs[0].barh(y + (k - 0.5) * h, tt, h * 0.95, color=COL[a], label=NAME[a])
        for yi, v in zip(y + (k - 0.5) * h, tt):
            axs[0].text(v, yi, f" {v:.1f}s", va="center", fontsize=9, color=INK)
        rel = [100 * sc(a, i).mean() / max(sc("greedy", i).mean(), sc("gratio", i).mean()) for i in gr_pair]
        axs[1].barh(y + (k - 0.5) * h, rel, h * 0.95, color=COL[a])
        for yi, v in zip(y + (k - 0.5) * h, rel):
            axs[1].text(v, yi, f" {v:.1f}%", va="center", fontsize=9, color=INK)
    axs[0].set_yticks(y, [f"{lab(i)}  (V×C={human(size[i])})" for i in gr_pair]); axs[0].invert_yaxis()
    axs[0].set_xlabel("Temps d'exécution (s)"); axs[0].set_title("Coût en temps"); axs[0].legend(loc="lower right")
    axs[1].set_xlim(0, 118); axs[1].set_xlabel("Score (% du meilleur des deux gloutons)"); axs[1].set_title("Qualité")
    fig.tight_layout(); save(fig, "2b_gloutons.png")

    # ---- Fig 3 : scaling (barres etiquetees, triees par taille) ----
    pair = ls_pair
    y = np.arange(len(pair)); h = 0.4
    fig, axs = plt.subplots(1, 2, figsize=(14, 8), sharey=True)
    g = [100 * (sc("dp", i).mean() / sc("ls", i).mean() - 1) for i in pair]
    axs[0].barh(y, g, color=COL["dp"], height=0.65)
    for yi, v in zip(y, g):
        axs[0].text(v, yi, f" {v:+.1f}%", va="center", fontsize=10, color=INK)
    axs[0].set_xlim(0, max(g) * 1.2)

    def t_ref(r, thr):                      # temps pour atteindre thr (score absolu), None si jamais atteint
        return next((t for t, s_ in r["curve"] if s_ >= thr), None)

    for ax, frac in [(axs[1], 0.99)]:
        xmax = 0
        for k, a in enumerate(["dp", "ls"]):
            for yi, i in zip(y, pair):
                thr = frac * sc("dp", i).mean()
                ts = [t_ref(r, thr) for r in by[(a, i)]]
                yy = yi + (k - 0.5) * h
                if any(t is None for t in ts):
                    best = max(r["curve"][-1][1] for r in by[(a, i)]) / sc("dp", i).mean() * 100
                    ax.text(0.2, yy, f"jamais atteint (plafond {best:.1f}%)", va="center", fontsize=9, color=COL[a])
                else:
                    v = float(np.mean(ts)); xmax = max(xmax, v)
                    ax.barh(yy, v, h * 0.95, color=COL[a], label=NAME[a] if yi == y[0] else None)
                    ax.text(v, yy, f" {v:.1f}s", va="center", fontsize=9, color=INK)
        ax.set_xlim(0, xmax * 1.25)
    axs[0].set_yticks(y, [f"{lab(i)}  (V×C={human(size[i])})" for i in pair]); axs[0].invert_yaxis()
    axs[0].set_title("Gain de DP sur Local_Search"); axs[0].set_xlabel("Gain de score (%)")
    axs[1].set_title("Temps pour atteindre 99 % du score final de DP"); axs[1].set_xlabel("Temps (s)")
    handles = [plt.Rectangle((0, 0), 1, 1, color=COL[a]) for a in ("dp", "ls")]
    axs[1].legend(handles, [NAME["dp"], NAME["ls"]], loc="lower right")
    fig.tight_layout(); save(fig, "3_scaling.png")

    # ---- Fig 4 : sensibilite ----
    if sens:
        fig, axs = plt.subplots(1, 2, figsize=(13, 4.8), sharey=True)
        sinst = sorted({r["instance"] for r in sens})
        base = {i: np.mean([r["score"] for r in sens if r["instance"] == i and r["perturb"] == 0.05 and r["max_items"] == 1500] or [np.nan]) for i in sinst}
        specs = [(sorted({r["perturb"] for r in sens if r["max_items"] == 1500}), lambda r, v: r["perturb"] == v and r["max_items"] == 1500),
                 (sorted({r["max_items"] for r in sens if r["perturb"] == 0.05}), lambda r, v: r["max_items"] == v and r["perturb"] == 0.05)]
        for ax, (vals, sel) in zip(axs, specs):
            for k, i in enumerate(sinst):
                m, lo, hi = [], [], []
                for v in vals:
                    s = np.array([r["score"] for r in sens if r["instance"] == i and sel(r, v)], float) / base[i] * 100
                    m.append(s.mean() if len(s) else np.nan); lo.append(s.min() if len(s) else np.nan); hi.append(s.max() if len(s) else np.nan)
                col = ["#2a78d6", "#eb6834", "#1baf7a"][k]
                ax.plot(range(len(vals)), m, "o-", color=col, label=lab(i)); ax.fill_between(range(len(vals)), lo, hi, color=col, alpha=0.18, lw=0)
            ax.set_xticks(range(len(vals)), [str(v) for v in vals])
        axs[0].set_xlabel("perturb_frac (fraction de caches détruits)"); axs[1].set_xlabel("max_items (candidats max. au sac à dos)")
        axs[0].set_ylabel("Score (% du réglage par défaut)"); axs[0].legend(title="Instance")
        axs[0].set_title("Sensibilité aux hyperparamètres (60 s, 2 seeds)")
        fig.tight_layout(); save(fig, "4_sensibilite.png")


if __name__ == "__main__":
    main()
