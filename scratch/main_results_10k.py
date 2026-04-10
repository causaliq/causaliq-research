"""Main fusion results with 10K-only BNSL.

Produces the primary paper results table:
BNSL-10K solo, LLM solo, Fusion 50/50, Oracle.
Excludes covid. 9 networks.
"""

import sys
from io import StringIO
from pathlib import Path

base = Path(__file__).resolve().parents[1]
for pkg in [
    "causaliq-core",
    "causaliq-workflow",
    "causaliq-analysis",
]:
    p = base.parent / pkg / "src"
    if p.exists():
        sys.path.insert(0, str(p))

from causaliq_analysis.merge import merge_graphs
from causaliq_analysis.metrics import pdag_compare
from causaliq_core.bn.io import read_bn
from causaliq_core.graph import PDG
from causaliq_core.graph.io import graphml
from causaliq_workflow.cache import WorkflowCache

# covid: not really an expert reference graph
# fire: too niche a subject
# corrosion: too good BNSL results
# gasexplosion: very poor LLM results
# polymorphic: poorish LLM results

NETWORKS = [
    "alarm", "asia", "barley", "child",
    "constructionproductivity", "corical", "diarrhoea", "earthquake",
    "estuary", "flood", "hailfinder",
    "hepar2", "insurance", "kosterhavet",
    "macrophytes", "mildew", "nuclearwaste", "permaBN",
    "pneumonia",  "property", "sachs", "seismic", "sports",
    "urinary", "vessel1", "water",
]
THRESHOLD = 0.3
RESULTS_DIR = (
    base / "papers" / "pdg-merge" / "results"
)
NETWORKS_DIR = base / "networks"


def load_pdgs(cache_path):
    """Load PDGs: BNSL filtered to 10K only."""
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
                net, {"bnsl": [], "llm": []},
            )
            if is_bnsl:
                ss = mv.get("sample_size", "")
                if ss == "10K":
                    data[net]["bnsl"].append(pdg)
            else:
                pd = mv.get("prompt_detail", "")
                if pd in {"standard"}:
                    data[net]["llm"].append(pdg)
    return data


def weighted_merge(bp, lp, bw, lw):
    """50/50 or weighted merge of two groups."""
    bm = merge_graphs(bp)
    lm = merge_graphs(lp)
    t = bw + lw
    return merge_graphs(
        [bm, lm], weights=[bw / t, lw / t]
    )


def evaluate(pdg, ref):
    """PDG -> DAG -> F1."""
    r = pdg.to_dag_greedy(threshold=THRESHOLD)
    return pdag_compare(r.dag, ref)


def main():
    """Run main results table."""
    cache_path = str(RESULTS_DIR / "pdgs.db")
    data = load_pdgs(cache_path)

    weights = [
        round(w / 20, 2) for w in range(21)
    ]

    hdr = (
        f"{'Network':<25} | {'Nodes':>5}"
        f" | {'BNSL':>7} | {'LLM':>7}"
        f" | {'Fusion':>7} | {'Orc_w':>5}"
        f" | {'Oracle':>7}"
        f" | {'F>best':>6}"
    )
    sep = "-" * len(hdr)

    print("MAIN RESULTS: 10K-only BNSL + "
          "3-LLM ensemble, 50/50 fusion")
    print(f"  BNSL: FGES + Tabu + PC, "
          f"10K samples, 2 seeds (6 PDGs)")
    print(f"  LLM:  Gemini + Claude + GPT, "
          f"2 prompts, 3 seeds (18 PDGs)")
    print(f"  Fusion: average strategy, "
          f"threshold {THRESHOLD}")
    print()
    print(sep)
    print(hdr)
    print(sep)

    totals = {
        "bnsl": 0.0, "llm": 0.0,
        "fuse": 0.0, "oracle": 0.0,
        "best_solo": 0.0,
    }
    n_wins = 0
    n = 0

    for net in NETWORKS:
        s = data.get(net)
        if not s or not s["bnsl"] or not s["llm"]:
            print(f"{net:<25} | NO DATA")
            continue

        ref_path = str(
            NETWORKS_DIR / net / f"{net}.xdsl"
        )
        ref_bn = read_bn(ref_path)
        ref = ref_bn.dag
        nodes = len(ref_bn.dag.nodes)

        # Solo baselines
        bm = merge_graphs(s["bnsl"])
        bnsl_f1 = evaluate(bm, ref)["f1"]

        lm = merge_graphs(s["llm"])
        llm_f1 = evaluate(lm, ref)["f1"]

        # Fusion 50/50
        g50 = weighted_merge(
            s["bnsl"], s["llm"], 0.50, 0.50
        )
        g50_f1 = evaluate(g50, ref)["f1"]

        # Oracle sweep
        best_f1 = -1.0
        best_w = 0.0
        for bw in weights:
            lw = 1.0 - bw
            if bw == 0.0:
                p = merge_graphs(s["llm"])
            elif bw == 1.0:
                p = merge_graphs(s["bnsl"])
            else:
                p = weighted_merge(
                    s["bnsl"], s["llm"], bw, lw
                )
            f1 = evaluate(p, ref)["f1"]
            if f1 > best_f1:
                best_f1 = f1
                best_w = bw

        best_solo = max(bnsl_f1, llm_f1)
        delta = g50_f1 - best_solo
        win = delta > 0
        if win:
            n_wins += 1

        print(
            f"{net:<25} | {nodes:>5}"
            f" | {bnsl_f1:>7.3f} | {llm_f1:>7.3f}"
            f" | {g50_f1:>7.3f} | {best_w:>5.2f}"
            f" | {best_f1:>7.3f}"
            f" | {delta:>+6.3f}"
            f"{'*' if not win else ''}"
        )

        totals["bnsl"] += bnsl_f1
        totals["llm"] += llm_f1
        totals["fuse"] += g50_f1
        totals["oracle"] += best_f1
        totals["best_solo"] += best_solo
        n += 1

    if n > 0:
        print(sep)
        print(
            f"{'AVERAGE':<25} | {'':>5}"
            f" | {totals['bnsl'] / n:>7.3f}"
            f" | {totals['llm'] / n:>7.3f}"
            f" | {totals['fuse'] / n:>7.3f}"
            f" | {'':>5}"
            f" | {totals['oracle'] / n:>7.3f}"
            f" | "
        )

        avg_b = totals["bnsl"] / n
        avg_l = totals["llm"] / n
        avg_f = totals["fuse"] / n
        avg_o = totals["oracle"] / n
        avg_best_solo = totals["best_solo"] / n

        print()
        print(f"Fusion wins: {n_wins}/{n} "
              f"networks")
        print(
            f"Fusion vs best solo: "
            f"{avg_f - avg_best_solo:+.3f} "
            f"({avg_f:.3f} vs {avg_best_solo:.3f})"
        )
        print(
            f"Fusion vs BNSL:      "
            f"{avg_f - avg_b:+.3f}"
        )
        print(
            f"Fusion vs LLM:       "
            f"{avg_f - avg_l:+.3f}"
        )
        print(
            f"Oracle vs fusion:    "
            f"{avg_o - avg_f:+.3f} "
            f"(upper bound gap)"
        )


if __name__ == "__main__":
    import io
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    main()
    sys.stdout = old_stdout
    text = buf.getvalue()
    out = base / "scratch" / "main_results.txt"
    out.write_text(text)
    print(text, end="")
