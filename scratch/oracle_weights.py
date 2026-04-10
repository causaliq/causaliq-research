"""Per-network oracle weight analysis.

Computes the optimal BNSL weight for each network
individually, showing the upper bound of fusion
performance if we could predict the right weight.
"""

import sys
from io import StringIO
from pathlib import Path

base = Path(__file__).resolve().parents[1]
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

NETWORKS = [
    "alarm", "asia", "child", "covid", "diarrhoea",
    "insurance", "property", "sports", "sachs",
    "water",
]
THRESHOLD = 0.3
RESULTS_DIR = base / "papers" / "pdg-merge" / "results"
NETWORKS_DIR = base / "networks"

SOURCES = ("bnsl", "llm", "gemini", "claude", "gpt")


def load_pdgs(cache_path):
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
                net, {s: [] for s in SOURCES}
            )
            if is_bnsl:
                data[net]["bnsl"].append(pdg)
            else:
                model = mv.get("llm_model", "")
                if "gemini" in model:
                    src = "gemini"
                elif "claude" in model or "anthrop" in model:
                    src = "claude"
                else:
                    src = "gpt"
                data[net][src].append(pdg)
                data[net]["llm"].append(pdg)
    return data


def weighted_merge(bp, lp, bw, lw):
    bm = merge_graphs(bp)
    lm = merge_graphs(lp)
    t = bw + lw
    return merge_graphs([bm, lm], weights=[bw / t, lw / t])


def evaluate(pdg, ref):
    r = pdg.to_dag_greedy(threshold=THRESHOLD)
    return pdag_compare(r.dag, ref)


def main():
    cache_path = str(RESULTS_DIR / "pdgs.db")
    data = load_pdgs(cache_path)

    weights = [round(w / 20, 2) for w in range(21)]

    hdr = (
        f"{'Network':<12} | {'BNSL-only':>9} | "
        f"{'LLM-only':>9} | {'Global.50':>9} | "
        f"{'Oracle F1':>9} | {'Oracle_w':>8} | "
        f"Fusion > both?"
    )
    sep = "-" * len(hdr)
    print(hdr)
    print(sep)

    total_bnsl = 0.0
    total_llm = 0.0
    total_global = 0.0
    total_oracle = 0.0
    n = 0
    all_beat = True

    for net in NETWORKS:
        s = data.get(net)
        if not s or not s["bnsl"] or not s["llm"]:
            continue
        ref_path = str(
            NETWORKS_DIR / net / f"{net}.xdsl"
        )
        ref = read_bn(ref_path).dag

        # BNSL only
        bm = merge_graphs(s["bnsl"])
        bnsl_f1 = evaluate(bm, ref)["f1"]

        # LLM only
        lm = merge_graphs(s["llm"])
        llm_f1 = evaluate(lm, ref)["f1"]

        # Global 0.50
        g50 = weighted_merge(
            s["bnsl"], s["llm"], 0.50, 0.50
        )
        g50_f1 = evaluate(g50, ref)["f1"]

        # Oracle: best weight per network
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

        beats = (
            best_f1 > bnsl_f1 and best_f1 > llm_f1
        )
        if not beats:
            all_beat = False
            if bnsl_f1 >= llm_f1:
                tag = "NO  (=BNSL)"
            else:
                tag = "NO  (=LLM)"
        else:
            tag = "YES"

        print(
            f"{net:<12} | {bnsl_f1:>9.3f} | "
            f"{llm_f1:>9.3f} | {g50_f1:>9.3f} | "
            f"{best_f1:>9.3f} | {best_w:>8.2f} | "
            f"{tag}"
        )
        total_bnsl += bnsl_f1
        total_llm += llm_f1
        total_global += g50_f1
        total_oracle += best_f1
        n += 1

    print(sep)
    label = "ALL" if all_beat else "NOT ALL"
    print(
        f"{'AVERAGE':<12} | {total_bnsl / n:>9.3f}"
        f" | {total_llm / n:>9.3f}"
        f" | {total_global / n:>9.3f}"
        f" | {total_oracle / n:>9.3f}"
        f" | {'':>8} | {label}"
    )
    print()
    d_bnsl = (total_oracle - total_bnsl) / n
    d_llm = (total_oracle - total_llm) / n
    d_global = (total_oracle - total_global) / n
    print(
        f"Oracle improvement over BNSL-only: "
        f"{d_bnsl:+.3f}"
    )
    print(
        f"Oracle improvement over LLM-only:  "
        f"{d_llm:+.3f}"
    )
    print(
        f"Oracle improvement over global .50: "
        f"{d_global:+.3f}"
    )


if __name__ == "__main__":
    main()
