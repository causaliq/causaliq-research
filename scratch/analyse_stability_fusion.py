"""Stability-weighted fusion experiment.

Compares equal-weight PDG fusion (current approach) with
stability-weighted fusion where each source (BNSL vs LLM)
is weighted by internal consistency of its PDGs.

Stability metric: average pairwise edge-probability agreement
across PDGs within a source group. A source that produces
consistent PDGs across configurations gets higher weight.
"""

import sys
from io import StringIO
from pathlib import Path
from typing import Dict, List, Tuple

base = Path(__file__).resolve().parents[1]
for pkg in ["causaliq-core", "causaliq-workflow", "causaliq-analysis"]:
    p = base.parent / pkg / "src"
    if p.exists():
        sys.path.insert(0, str(p))

from causaliq_analysis.merge import merge_graphs
from causaliq_analysis.metrics import pdag_compare
from causaliq_core.bn.io import read_bn
from causaliq_core.graph import PDG, EdgeProbabilities
from causaliq_core.graph.io import graphml
from causaliq_workflow.cache import WorkflowCache

NETWORKS = [
    "alarm", "asia", "child", "covid", "diarrhoea",
    "insurance", "property", "sports", "sachs", "water",
]
THRESHOLD = 0.3
RESULTS_DIR = base / "papers" / "pdg-merge" / "results"
NETWORKS_DIR = base / "networks"


SOURCES = (
    "bnsl", "bnsl_1k", "bnsl_10k",
    "fges", "tabu", "pc",
    "gemini", "claude", "gpt", "llm",
)


def load_pdgs_by_source(
    cache_path: str,
) -> Dict[str, Dict[str, List[PDG]]]:
    """Load PDGs grouped by network and source type.

    Returns:
        {network: {"bnsl": [...], "bnsl_1k": [...],
                    "bnsl_10k": [...], "gemini": [...],
                    "claude": [...], "gpt": [...],
                    "llm": [...]}}

    ``llm`` contains all LLM PDGs combined.
    ``bnsl`` contains all BNSL PDGs combined.
    """
    empty = {s: [] for s in SOURCES}
    result: Dict[str, Dict[str, List[PDG]]] = {}
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

            pdg = graphml.read_pdg(StringIO(pdg_obj.content))

            is_bnsl = mv.get("series") is not None
            if is_bnsl:
                source = "bnsl"
                series = mv.get("series", "")
                ss = mv.get("sample_size", "")
                if ss == "1K":
                    sub_ss = "bnsl_1k"
                else:
                    sub_ss = "bnsl_10k"
                if "FGES" in series:
                    sub_alg = "fges"
                elif "PC" in series:
                    sub_alg = "pc"
                else:
                    sub_alg = "tabu"
            else:
                model = mv.get("llm_model", "")
                if "gemini" in model:
                    source = "gemini"
                elif "anthropic" in model or "claude" in model:
                    source = "claude"
                elif "openai" in model or "gpt" in model:
                    source = "gpt"
                else:
                    source = "gpt"  # fallback

            result.setdefault(
                net, {s: list() for s in SOURCES},
            )
            result[net][source].append(pdg)
            if is_bnsl:
                result[net][sub_ss].append(pdg)
                result[net][sub_alg].append(pdg)
            if source in ("gemini", "claude", "gpt"):
                result[net]["llm"].append(pdg)

    return result


def compute_stability(pdgs: List[PDG]) -> float:
    """Compute stability of a group of PDGs.

    Stability = 1 - mean(pairwise edge-probability distance).
    Distance per edge pair = sum of absolute differences in the
    4-probability vector, divided by 2 (max possible distance).

    Returns value in [0, 1] where 1 = all PDGs identical.
    """
    if len(pdgs) <= 1:
        return 1.0

    nodes = pdgs[0].nodes
    n_pairs = len(nodes) * (len(nodes) - 1) // 2

    total_distance = 0.0
    n_comparisons = 0

    for i in range(len(pdgs)):
        for j in range(i + 1, len(pdgs)):
            pair_dist = 0.0
            for ni, na in enumerate(nodes):
                for nb in nodes[ni + 1:]:
                    pa = pdgs[i].get_probabilities(na, nb)
                    pb = pdgs[j].get_probabilities(na, nb)
                    # L1 distance of probability vectors, normalised
                    d = (
                        abs(pa.forward - pb.forward)
                        + abs(pa.backward - pb.backward)
                        + abs(pa.undirected - pb.undirected)
                        + abs(pa.none - pb.none)
                    ) / 2.0  # max L1 distance is 2.0
                    pair_dist += d
            total_distance += pair_dist / n_pairs
            n_comparisons += 1

    mean_distance = total_distance / n_comparisons
    return 1.0 - mean_distance


def pdg_to_dag_and_evaluate(
    pdg: PDG,
    reference_dag,
    threshold: float,
) -> Dict[str, float]:
    """Convert PDG to DAG and evaluate against reference."""
    result = pdg.to_dag_greedy(threshold=threshold)
    metrics = pdag_compare(result.dag, reference_dag)
    return metrics


def weighted_merge(
    bnsl_pdgs: List[PDG],
    llm_pdgs: List[PDG],
    bnsl_weight: float,
    llm_weight: float,
) -> PDG:
    """Merge BNSL and LLM PDGs with specified source weights.

    First merges within each source (equal weight), then merges
    the two source-level PDGs with the given weights.
    """
    # Merge within each source
    bnsl_merged = merge_graphs(bnsl_pdgs)
    llm_merged = merge_graphs(llm_pdgs)

    # Merge across sources with specified weights
    total = bnsl_weight + llm_weight
    w_bnsl = bnsl_weight / total
    w_llm = llm_weight / total

    return merge_graphs(
        [bnsl_merged, llm_merged],
        weights=[w_bnsl, w_llm],
    )


def _print_disentanglement(
    results: Dict[str, Dict[str, float]],
) -> None:
    """Print disentanglement table: source balancing vs diversity."""
    cols = [
        ("Equal", "equal"),
        ("Bal(B+LLM)", "stab"),
        ("Bal(B+Gem)", "bnsl_gem"),
        ("Bal(B+Cla)", "bnsl_cla"),
        ("Bal(B+GPT)", "bnsl_gpt"),
        ("4-Source", "four_src"),
        ("BNSL only", "bnsl_only"),
        ("Gem only", "gem_only"),
        ("Cla only", "cla_only"),
        ("GPT only", "gpt_only"),
    ]
    w = 10
    hdr = f"{'Network':<12}"
    for label, _ in cols:
        hdr += f" | {label:>{w}}"
    sep = "-" * len(hdr)

    print()
    print(
        "DISENTANGLEMENT: source balancing vs "
        "cross-model diversity"
    )
    print(
        "  Equal      = all PDGs equal weight "
        "(current baseline)"
    )
    print(
        "  Bal(B+LLM) = 50/50 BNSL vs LLM "
        "(all models pooled)"
    )
    print(
        "  Bal(B+Gem) = 50/50 BNSL vs Gemini only"
    )
    print(
        "  Bal(B+Cla) = 50/50 BNSL vs Claude only"
    )
    print(
        "  Bal(B+GPT) = 50/50 BNSL vs GPT only"
    )
    print(
        "  4-Source   = 1/4 BNSL + 1/4 per LLM"
    )
    print()
    print(sep)
    print(hdr)
    print(sep)

    totals: Dict[str, float] = {k: 0.0 for _, k in cols}
    nn = 0

    for net in NETWORKS:
        nr = results.get(net)
        if not nr:
            continue
        row = f"{net:<12}"
        for _, key in cols:
            val = nr.get(key)
            if val is not None:
                row += f" | {val:>{w}.3f}"
                totals[key] += val
            else:
                row += f" | {'n/a':>{w}}"
        print(row)
        nn += 1

    if nn > 0:
        print(sep)
        row = f"{'AVERAGE':<12}"
        for _, key in cols:
            avg = totals[key] / nn
            row += f" | {avg:>{w}.3f}"
        print(row)

    # Summary interpretation.
    if nn > 0:
        avg_bal_llm = totals["stab"] / nn
        avg_bal_gem = totals.get("bnsl_gem", 0) / nn
        avg_bal_cla = totals.get("bnsl_cla", 0) / nn
        avg_bal_gpt = totals.get("bnsl_gpt", 0) / nn
        singles = [avg_bal_gem, avg_bal_cla, avg_bal_gpt]
        avg_single = sum(singles) / len(singles)
        avg_four = totals.get("four_src", 0) / nn
        diversity_effect = avg_bal_llm - avg_single
        print()
        print("Interpretation:")
        print(
            f"  Avg single-LLM balanced = "
            f"{avg_single:.3f}  "
            f"(Gem={avg_bal_gem:.3f} "
            f"Cla={avg_bal_cla:.3f} "
            f"GPT={avg_bal_gpt:.3f})"
        )
        print(
            f"  Avg all-LLM balanced    = "
            f"{avg_bal_llm:.3f}"
        )
        print(
            f"  4-source (per-model)    = "
            f"{avg_four:.3f}"
        )
        print(
            f"  Cross-model diversity   = "
            f"{diversity_effect:+.3f}"
        )
        if abs(diversity_effect) < 0.01:
            print(
                "  -> Diversity effect is NEGLIGIBLE; "
                "source balancing is the driver."
            )
        elif diversity_effect > 0:
            print(
                "  -> Cross-model diversity HELPS; "
                "adding more LLMs likely beneficial."
            )
        else:
            print(
                "  -> Cross-model diversity HURTS; "
                "one model may be dragging down."
            )


def _print_bnsl_diversity(
    pdgs_by_source: Dict[str, Dict[str, List[PDG]]],
) -> None:
    """Analyse BNSL-side diversity by sample size and algorithm."""
    cols = [
        ("BNSL all", "bnsl_all"),
        ("BNSL 1K", "bnsl_1k"),
        ("BNSL 10K", "bnsl_10k"),
        ("FGES", "fges"),
        ("Tabu", "tabu"),
        ("PC", "pc"),
        ("B+LLM all", "llm_b_all"),
        ("B+LLM 1K", "llm_b_1k"),
        ("B+LLM 10K", "llm_b_10k"),
        ("FGES+LLM", "llm_fges"),
        ("Tabu+LLM", "llm_tabu"),
        ("PC+LLM", "llm_pc"),
    ]
    w = 9
    hdr = f"{'Network':<12}"
    for label, _ in cols:
        hdr += f" | {label:>{w}}"
    sep = "-" * len(hdr)

    print()
    print(
        "BNSL DIVERSITY: sample size and algorithm"
    )
    print(
        "  BNSL all  = merge all 12 BNSL PDGs"
    )
    print(
        "  FGES/Tabu/PC = merge 4 PDGs per algorithm"
    )
    print(
        "  B+LLM x   = 50/50 fusion with all LLMs"
    )
    print()
    print(sep)
    print(hdr)
    print(sep)

    totals: Dict[str, float] = {
        k: 0.0 for _, k in cols
    }
    nn = 0

    for net in NETWORKS:
        sources = pdgs_by_source.get(net)
        if not sources:
            continue

        bnsl_all = sources.get("bnsl", [])
        bnsl_1k = sources.get("bnsl_1k", [])
        bnsl_10k = sources.get("bnsl_10k", [])
        fges_pdgs = sources.get("fges", [])
        tabu_pdgs = sources.get("tabu", [])
        pc_pdgs = sources.get("pc", [])
        llm_pdgs = sources.get("llm", [])

        if not bnsl_all or not llm_pdgs:
            continue

        ref_path = str(
            NETWORKS_DIR / net / f"{net}.xdsl"
        )
        ref_dag = read_bn(ref_path).dag

        nr: Dict[str, float] = {}

        # BNSL-only baselines.
        for key, pdgs in [
            ("bnsl_all", bnsl_all),
            ("bnsl_1k", bnsl_1k),
            ("bnsl_10k", bnsl_10k),
            ("fges", fges_pdgs),
            ("tabu", tabu_pdgs),
            ("pc", pc_pdgs),
        ]:
            if pdgs:
                m = merge_graphs(pdgs)
                met = pdg_to_dag_and_evaluate(
                    m, ref_dag, THRESHOLD,
                )
                nr[key] = met["f1"]

        # Fused with LLM (50/50).
        for key, pdgs in [
            ("llm_b_all", bnsl_all),
            ("llm_b_1k", bnsl_1k),
            ("llm_b_10k", bnsl_10k),
            ("llm_fges", fges_pdgs),
            ("llm_tabu", tabu_pdgs),
            ("llm_pc", pc_pdgs),
        ]:
            if pdgs:
                fused = weighted_merge(
                    pdgs, llm_pdgs, 0.5, 0.5,
                )
                met = pdg_to_dag_and_evaluate(
                    fused, ref_dag, THRESHOLD,
                )
                nr[key] = met["f1"]

        row = f"{net:<12}"
        for _, key in cols:
            val = nr.get(key)
            if val is not None:
                row += f" | {val:>{w}.3f}"
                totals[key] += val
            else:
                row += f" | {'n/a':>{w}}"
        print(row)
        nn += 1

    if nn > 0:
        print(sep)
        row = f"{'AVERAGE':<12}"
        for _, key in cols:
            avg = totals[key] / nn
            row += f" | {avg:>{w}.3f}"
        print(row)

        # Interpretation.
        a_all = totals["bnsl_all"] / nn
        a_1k = totals["bnsl_1k"] / nn
        a_10k = totals["bnsl_10k"] / nn
        a_fges = totals["fges"] / nn
        a_tabu = totals["tabu"] / nn
        a_pc = totals["pc"] / nn
        best_ss = max(a_1k, a_10k)
        best_alg = max(a_fges, a_tabu, a_pc)
        ss_div = a_all - best_ss
        alg_div = a_all - best_alg

        f_all = totals["llm_b_all"] / nn
        f_1k = totals["llm_b_1k"] / nn
        f_10k = totals["llm_b_10k"] / nn
        f_fges = totals["llm_fges"] / nn
        f_tabu = totals["llm_tabu"] / nn
        f_pc = totals["llm_pc"] / nn
        best_f_ss = max(f_1k, f_10k)
        best_f_alg = max(f_fges, f_tabu, f_pc)
        f_ss_div = f_all - best_f_ss
        f_alg_div = f_all - best_f_alg

        print()
        print("Interpretation (BNSL-only):")
        print(
            f"  Sample-size: pooled={a_all:.3f} "
            f"best={best_ss:.3f} "
            f"(1K={a_1k:.3f} 10K={a_10k:.3f}) "
            f"div={ss_div:+.3f}"
        )
        print(
            f"  Algorithm:   pooled={a_all:.3f} "
            f"best={best_alg:.3f} "
            f"(FGES={a_fges:.3f} "
            f"Tabu={a_tabu:.3f} "
            f"PC={a_pc:.3f}) "
            f"div={alg_div:+.3f}"
        )
        print()
        print("Interpretation (fused with LLM):")
        print(
            f"  Sample-size: pooled={f_all:.3f} "
            f"best={best_f_ss:.3f} "
            f"(1K={f_1k:.3f} 10K={f_10k:.3f}) "
            f"div={f_ss_div:+.3f}"
        )
        print(
            f"  Algorithm:   pooled={f_all:.3f} "
            f"best={best_f_alg:.3f} "
            f"(FGES={f_fges:.3f} "
            f"Tabu={f_tabu:.3f} "
            f"PC={f_pc:.3f}) "
            f"div={f_alg_div:+.3f}"
        )
        if abs(f_alg_div) < 0.01:
            print(
                "  -> BNSL algorithm diversity "
                "is NEGLIGIBLE for fusion."
            )
        elif f_alg_div > 0:
            print(
                "  -> BNSL algorithm diversity "
                "HELPS fusion."
            )
        else:
            print(
                "  -> BNSL algorithm diversity "
                "does NOT help fusion; "
                "best single algorithm wins."
            )


def _run_weight_sweep() -> None:
    """Sweep BNSL weight from 0.0 to 1.0."""
    cache_path = str(RESULTS_DIR / "pdgs.db")
    pdgs_by_source = load_pdgs_by_source(cache_path)

    weights = [
        round(w / 20, 2) for w in range(21)
    ]  # 0.00, 0.05, ..., 1.00

    print()
    print("=" * 80)
    print("BNSL WEIGHT SWEEP (source-balanced fusion)")
    print(
        "  BNSL_w = weight given to BNSL composite; "
        "LLM_w = 1 - BNSL_w"
    )

    # Build per-network data.
    net_data: List[
        Tuple[str, List[PDG], List[PDG], object]
    ] = []
    for net in NETWORKS:
        sources = pdgs_by_source.get(net)
        if not sources:
            continue
        bnsl_pdgs = sources["bnsl"]
        llm_pdgs = sources["llm"]
        if not bnsl_pdgs or not llm_pdgs:
            continue
        ref_path = str(
            NETWORKS_DIR / net / f"{net}.xdsl"
        )
        ref_dag = read_bn(ref_path).dag
        net_data.append(
            (net, bnsl_pdgs, llm_pdgs, ref_dag)
        )

    # Header.
    w_col = 7
    hdr = f"{'BNSL_w':>{w_col}}"
    for net, _, _, _ in net_data:
        hdr += f" | {net:>9}"
    hdr += f" | {'AVERAGE':>9}"
    sep = "-" * len(hdr)

    print()
    print(sep)
    print(hdr)
    print(sep)

    best_avg = -1.0
    best_w = 0.0

    for bw in weights:
        lw = 1.0 - bw
        row = f"{bw:>{w_col}.2f}"
        total = 0.0
        for net, bnsl_pdgs, llm_pdgs, ref_dag in net_data:
            if bw == 0.0:
                pdg = merge_graphs(llm_pdgs)
            elif bw == 1.0:
                pdg = merge_graphs(bnsl_pdgs)
            else:
                pdg = weighted_merge(
                    bnsl_pdgs, llm_pdgs, bw, lw,
                )
            met = pdg_to_dag_and_evaluate(
                pdg, ref_dag, THRESHOLD,
            )
            row += f" | {met['f1']:>9.3f}"
            total += met["f1"]
        avg = total / len(net_data)
        row += f" | {avg:>9.3f}"
        if avg > best_avg:
            best_avg = avg
            best_w = bw
        # Mark the best so far.
        if bw == best_w:
            row += " <--"
        print(row)

    print(sep)
    print(
        f"\nOptimal BNSL weight: {best_w:.2f} "
        f"(avg F1 = {best_avg:.3f})"
    )

    # Also show equal-weight baseline.
    eq_total = 0.0
    for net, bnsl_pdgs, llm_pdgs, ref_dag in net_data:
        all_p = bnsl_pdgs + llm_pdgs
        eq_pdg = merge_graphs(all_p)
        eq_met = pdg_to_dag_and_evaluate(
            eq_pdg, ref_dag, THRESHOLD,
        )
        eq_total += eq_met["f1"]
    eq_avg = eq_total / len(net_data)
    print(
        f"Equal-weight (no balancing): "
        f"avg F1 = {eq_avg:.3f}"
    )
    print(
        f"Improvement of optimal over equal: "
        f"{best_avg - eq_avg:+.3f}"
    )


def main() -> None:
    """Run the stability-weighted fusion experiment."""
    cache_path = str(RESULTS_DIR / "pdgs.db")
    pdgs_by_source = load_pdgs_by_source(cache_path)

    # ---- Table 1: Original comparison ----
    print("=" * 95)
    print(
        f"{'Network':<12} | {'BNSL stab':>9} | "
        f"{'LLM stab':>9} | {'Equal F1':>9} | "
        f"{'Stab F1':>9} | {'BNSL-only':>9} | "
        f"{'LLM-only':>9} | {'Delta':>7}"
    )
    print("-" * 95)

    total_equal = 0.0
    total_stab = 0.0
    n = 0

    # Store per-network results for table 2.
    net_results: Dict[str, Dict[str, float]] = {}

    for net in NETWORKS:
        sources = pdgs_by_source.get(net)
        if not sources:
            print(f"{net:<12} | {'NO DATA':>9}")
            continue

        bnsl_pdgs = sources["bnsl"]
        llm_pdgs = sources["llm"]
        gemini_pdgs = sources["gemini"]
        claude_pdgs = sources["claude"]
        gpt_pdgs = sources["gpt"]

        if not bnsl_pdgs or not llm_pdgs:
            print(
                f"{net:<12} | BNSL={len(bnsl_pdgs)} "
                f"LLM={len(llm_pdgs)} - skipped"
            )
            continue

        # Load reference graph
        ref_path = str(NETWORKS_DIR / net / f"{net}.xdsl")
        ref_dag = read_bn(ref_path).dag

        # Compute stability for each source
        bnsl_stab = compute_stability(bnsl_pdgs)
        llm_stab = compute_stability(llm_pdgs)

        # Equal-weight fusion (current approach)
        all_pdgs = bnsl_pdgs + llm_pdgs
        equal_pdg = merge_graphs(all_pdgs)
        equal_metrics = pdg_to_dag_and_evaluate(
            equal_pdg, ref_dag, THRESHOLD,
        )
        equal_f1 = equal_metrics["f1"]

        # Stability-weighted fusion
        stab_pdg = weighted_merge(
            bnsl_pdgs, llm_pdgs, bnsl_stab, llm_stab,
        )
        stab_metrics = pdg_to_dag_and_evaluate(
            stab_pdg, ref_dag, THRESHOLD,
        )
        stab_f1 = stab_metrics["f1"]

        # Source-only baselines
        bnsl_only = merge_graphs(bnsl_pdgs)
        bnsl_metrics = pdg_to_dag_and_evaluate(
            bnsl_only, ref_dag, THRESHOLD,
        )
        bnsl_f1 = bnsl_metrics["f1"]

        llm_only = merge_graphs(llm_pdgs)
        llm_metrics = pdg_to_dag_and_evaluate(
            llm_only, ref_dag, THRESHOLD,
        )
        llm_f1 = llm_metrics["f1"]

        delta = stab_f1 - equal_f1
        sign = "+" if delta > 0 else ""

        print(
            f"{net:<12} | {bnsl_stab:>9.3f} | "
            f"{llm_stab:>9.3f} | {equal_f1:>9.3f} | "
            f"{stab_f1:>9.3f} | {bnsl_f1:>9.3f} | "
            f"{llm_f1:>9.3f} | {sign}{delta:>6.3f}"
        )

        total_equal += equal_f1
        total_stab += stab_f1
        n += 1

        # Disentanglement: per-model fusions.
        nr: Dict[str, float] = {
            "equal": equal_f1,
            "stab": stab_f1,
            "bnsl_only": bnsl_f1,
            "llm_only": llm_f1,
        }

        # Gemini-only + BNSL (50/50 source-balanced)
        if gemini_pdgs:
            gem_fused = weighted_merge(
                bnsl_pdgs, gemini_pdgs, 0.5, 0.5,
            )
            gem_m = pdg_to_dag_and_evaluate(
                gem_fused, ref_dag, THRESHOLD,
            )
            nr["bnsl_gem"] = gem_m["f1"]

            gem_only = merge_graphs(gemini_pdgs)
            gem_solo = pdg_to_dag_and_evaluate(
                gem_only, ref_dag, THRESHOLD,
            )
            nr["gem_only"] = gem_solo["f1"]

        # Claude-only + BNSL (50/50 source-balanced)
        if claude_pdgs:
            cla_fused = weighted_merge(
                bnsl_pdgs, claude_pdgs, 0.5, 0.5,
            )
            cla_m = pdg_to_dag_and_evaluate(
                cla_fused, ref_dag, THRESHOLD,
            )
            nr["bnsl_cla"] = cla_m["f1"]

            cla_only = merge_graphs(claude_pdgs)
            cla_solo = pdg_to_dag_and_evaluate(
                cla_only, ref_dag, THRESHOLD,
            )
            nr["cla_only"] = cla_solo["f1"]

        # GPT-only + BNSL (50/50 source-balanced)
        if gpt_pdgs:
            gpt_fused = weighted_merge(
                bnsl_pdgs, gpt_pdgs, 0.5, 0.5,
            )
            gpt_m = pdg_to_dag_and_evaluate(
                gpt_fused, ref_dag, THRESHOLD,
            )
            nr["bnsl_gpt"] = gpt_m["f1"]

            gpt_only = merge_graphs(gpt_pdgs)
            gpt_solo = pdg_to_dag_and_evaluate(
                gpt_only, ref_dag, THRESHOLD,
            )
            nr["gpt_only"] = gpt_solo["f1"]

        # 4-source: BNSL + Gemini + Claude + GPT
        src_pdgs = []
        src_labels = []
        if bnsl_pdgs:
            src_pdgs.append(merge_graphs(bnsl_pdgs))
            src_labels.append("bnsl")
        if gemini_pdgs:
            src_pdgs.append(merge_graphs(gemini_pdgs))
            src_labels.append("gemini")
        if claude_pdgs:
            src_pdgs.append(merge_graphs(claude_pdgs))
            src_labels.append("claude")
        if gpt_pdgs:
            src_pdgs.append(merge_graphs(gpt_pdgs))
            src_labels.append("gpt")
        if len(src_pdgs) >= 3:
            w = [1.0 / len(src_pdgs)] * len(src_pdgs)
            multi_pdg = merge_graphs(src_pdgs, weights=w)
            multi_metrics = pdg_to_dag_and_evaluate(
                multi_pdg, ref_dag, THRESHOLD,
            )
            nr["four_src"] = multi_metrics["f1"]

        net_results[net] = nr

    if n > 0:
        print("-" * 95)
        avg_equal = total_equal / n
        avg_stab = total_stab / n
        delta = avg_stab - avg_equal
        sign = "+" if delta > 0 else ""
        print(
            f"{'AVERAGE':<12} | {'':>9} | "
            f"{'':>9} | {avg_equal:>9.3f} | "
            f"{avg_stab:>9.3f} | {'':>9} | "
            f"{'':>9} | {sign}{delta:>6.3f}"
        )

    # ---- Table 2: Disentanglement ----
    _print_disentanglement(net_results)

    # ---- Table 3: BNSL diversity ----
    _print_bnsl_diversity(pdgs_by_source)

    # Detailed stability breakdown
    print()
    print("Stability breakdown per source:")
    print("-" * 60)
    for net in NETWORKS:
        sources = pdgs_by_source.get(net, {})
        bnsl_pdgs = sources.get("bnsl", [])
        llm_pdgs = sources.get("llm", [])
        bnsl_stab = compute_stability(bnsl_pdgs) if bnsl_pdgs else 0
        llm_stab = compute_stability(llm_pdgs) if llm_pdgs else 0
        ratio = bnsl_stab / llm_stab if llm_stab > 0 else float("inf")
        bnsl_w = bnsl_stab / (bnsl_stab + llm_stab) if (bnsl_stab + llm_stab) > 0 else 0.5
        print(
            f"  {net:<12} BNSL: {len(bnsl_pdgs):>2} PDGs "
            f"stab={bnsl_stab:.3f}  "
            f"LLM: {len(llm_pdgs):>2} PDGs "
            f"stab={llm_stab:.3f}  "
            f"ratio={ratio:.2f}  "
            f"BNSL_weight={bnsl_w:.3f}"
        )


if __name__ == "__main__":
    main()
    _run_weight_sweep()
