"""BIC-sweep adaptive fusion weighting.

Sweeps BNSL weight 0.00-1.00 in 0.05 steps.
At each weight: merge sources -> extract DAG ->
score BIC against 100k observational data.
Picks weight with best BIC per network.
"""

import sys
from io import StringIO
from pathlib import Path

base = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(base.parent / "discovery"))
for pkg in ["causaliq-core", "causaliq-workflow",
            "causaliq-analysis"]:
    p = base.parent / pkg / "src"
    if p.exists():
        sys.path.insert(0, str(p))

from causaliq_analysis.merge import merge_graphs
from causaliq_analysis.metrics import pdag_compare
from causaliq_core.bn.io import read_bn
from causaliq_core.graph.io import graphml
from causaliq_workflow.cache import WorkflowCache
from data.pandas import Pandas
from data.score import dag_score

NETWORKS = [
    "alarm", "asia", "child", "covid", "diarrhoea",
    "insurance", "property", "sports", "sachs",
    "water",
]
THRESHOLD = 0.3
RESULTS_DIR = base / "papers" / "pdg-merge" / "results"
NETWORKS_DIR = base / "networks"
SCORE_PARAMS = {"base": "e"}


def load_pdgs(cache_path):
    """Load PDGs grouped by network and source."""
    sources = ("bnsl", "llm")
    data = {}
    with WorkflowCache(cache_path) as cache:
        for info in cache.list_entries():
            mv = info["matrix_values"]
            net = mv.get("network")
            if net not in NETWORKS:
                continue
            entry = cache.get(mv)
            pdg_obj = entry.get_object("pdg")
            if pdg_obj is None:
                continue
            pdg = graphml.read_pdg(
                StringIO(pdg_obj.content)
            )
            is_bnsl = mv.get("series") is not None
            data.setdefault(
                net, {s: [] for s in sources}
            )
            if is_bnsl:
                data[net]["bnsl"].append(pdg)
            else:
                data[net]["llm"].append(pdg)
    return data


def weighted_merge(bp, lp, bw, lw):
    """Merge BNSL and LLM PDGs with given weights."""
    bm = merge_graphs(bp)
    lm = merge_graphs(lp)
    t = bw + lw
    return merge_graphs(
        [bm, lm], weights=[bw / t, lw / t]
    )


def evaluate(pdg, ref):
    """Convert PDG to DAG and evaluate."""
    r = pdg.to_dag_greedy(threshold=THRESHOLD)
    return pdag_compare(r.dag, ref)


def main():
    """Run BIC-sweep fusion experiment.

    For each network, sweep BNSL weights 0.0-1.0,
    at each weight: merge -> extract DAG -> score
    BIC against data -> pick weight with best BIC.
    """
    cache_path = str(RESULTS_DIR / "pdgs.db")
    pdgs = load_pdgs(cache_path)

    weights_grid = [
        round(w / 20, 2) for w in range(21)
    ]

    # Header
    hdr = (
        f"{'Network':<12} | "
        f"{'BNSL F1':>7} | {'LLM F1':>7} | "
        f"{'Glb .50':>7} | "
        f"{'BIC_w':>5} | {'BIC F1':>7} | "
        f"{'Orc_w':>5} | {'Oracle':>7}"
    )
    sep = "-" * len(hdr)

    print("BIC-SWEEP ADAPTIVE FUSION")
    print(
        "  Sweep BNSL weight 0.00-1.00, "
        "at each weight:"
    )
    print(
        "  merge -> extract DAG -> score BIC "
        "-> pick weight with best BIC"
    )
    print()
    print(sep)
    print(hdr)
    print(sep)

    totals = {
        k: 0.0 for k in [
            "bnsl", "llm", "global", "bic",
            "oracle",
        ]
    }
    n = 0

    for net in NETWORKS:
        s = pdgs.get(net)
        if not s or not s["bnsl"] or not s["llm"]:
            print(f"{net:<12} | NO DATA")
            continue

        # Reference DAG
        ref_path = str(
            NETWORKS_DIR / net / f"{net}.xdsl"
        )
        ref = read_bn(ref_path).dag

        # Data file
        data_path = (
            NETWORKS_DIR / net / "datasets"
            / f"{net}_100k.csv.gz"
        )
        if not data_path.exists():
            print(f"{net:<12} | NO DATA FILE")
            continue

        # Load data once for scoring
        data = Pandas.read(
            str(data_path), dstype="categorical"
        )

        # Baselines
        bnsl_merged = merge_graphs(s["bnsl"])
        llm_merged = merge_graphs(s["llm"])
        bnsl_f1 = evaluate(bnsl_merged, ref)["f1"]
        llm_f1 = evaluate(llm_merged, ref)["f1"]

        g50 = weighted_merge(
            s["bnsl"], s["llm"], 0.50, 0.50
        )
        g50_f1 = evaluate(g50, ref)["f1"]

        # Sweep: find best weight by BIC and by F1
        best_bic = float("-inf")
        best_bic_w = 0.50
        best_f1 = -1.0
        best_f1_w = 0.0

        for bw in weights_grid:
            lw = 1.0 - bw
            if bw == 0.0:
                pdg = merge_graphs(s["llm"])
            elif bw == 1.0:
                pdg = merge_graphs(s["bnsl"])
            else:
                pdg = weighted_merge(
                    s["bnsl"], s["llm"], bw, lw
                )

            dag = pdg.to_dag_greedy(
                threshold=THRESHOLD
            ).dag

            # BIC score (no ground truth)
            scores = dag_score(
                dag, data, types=["bic"],
                params=SCORE_PARAMS,
            )
            bic = scores["bic"].sum()
            if bic > best_bic:
                best_bic = bic
                best_bic_w = bw

            # Oracle F1 (uses ground truth)
            f1 = pdag_compare(dag, ref)["f1"]
            if f1 > best_f1:
                best_f1 = f1
                best_f1_w = bw

        # Evaluate BIC-chosen weight by F1
        if best_bic_w == 0.0:
            bic_pdg = merge_graphs(s["llm"])
        elif best_bic_w == 1.0:
            bic_pdg = merge_graphs(s["bnsl"])
        else:
            bic_pdg = weighted_merge(
                s["bnsl"], s["llm"],
                best_bic_w, 1.0 - best_bic_w,
            )
        bic_f1 = evaluate(bic_pdg, ref)["f1"]

        print(
            f"{net:<12} | "
            f"{bnsl_f1:>7.3f} | {llm_f1:>7.3f}"
            f" | {g50_f1:>7.3f}"
            f" | {best_bic_w:>5.2f}"
            f" | {bic_f1:>7.3f}"
            f" | {best_f1_w:>5.2f}"
            f" | {best_f1:>7.3f}"
        )

        totals["bnsl"] += bnsl_f1
        totals["llm"] += llm_f1
        totals["global"] += g50_f1
        totals["bic"] += bic_f1
        totals["oracle"] += best_f1
        n += 1

    if n > 0:
        print(sep)
        print(
            f"{'AVERAGE':<12} | "
            f"{totals['bnsl'] / n:>7.3f}"
            f" | {totals['llm'] / n:>7.3f}"
            f" | {totals['global'] / n:>7.3f}"
            f" | {'':>5}"
            f" | {totals['bic'] / n:>7.3f}"
            f" | {'':>5}"
            f" | {totals['oracle'] / n:>7.3f}"
        )
        print()
        avg_g = totals["global"] / n
        avg_b = totals["bic"] / n
        avg_o = totals["oracle"] / n
        print(
            f"BIC-sweep vs global .50: "
            f"{avg_b - avg_g:+.3f}"
        )
        print(
            f"BIC-sweep vs oracle:     "
            f"{avg_b - avg_o:+.3f}"
        )
        if avg_o > avg_g:
            pct = (
                (avg_b - avg_g)
                / (avg_o - avg_g)
                * 100
            )
            print(
                f"Gap closed (global->oracle): "
                f"{pct:.1f}% "
                f"(oracle gap = "
                f"{avg_o - avg_g:+.3f})"
            )


if __name__ == "__main__":
    import io
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    main()
    sys.stdout = old_stdout
    text = buf.getvalue()
    out = base / "scratch" / "score_output.txt"
    out.write_text(text)
    print(text, end="")
