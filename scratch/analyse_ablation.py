"""Ablation analysis for PDG fusion.

Tests how each ingredient contributes to fusion
performance by systematically removing components:
- Single LLM vs 3-LLM ensemble
- Single BNSL algo vs 3-algo ensemble
- 1K vs 10K vs both sample sizes
- Single seed vs multi-seed (LLM)
"""

import sys
from io import StringIO
from pathlib import Path
from typing import Dict, List, Tuple

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

NETWORKS = [
    "alarm", "asia", "child", "diarrhoea",
    "insurance", "property", "sports", "sachs",
    "water",
]
THRESHOLD = 0.3
RESULTS_DIR = (
    base / "papers" / "pdg-merge" / "results"
)
NETWORKS_DIR = base / "networks"


def load_pdgs(
    cache_path: str,
) -> Dict[str, Dict[str, List[Tuple[dict, PDG]]]]:
    """Load PDGs with full metadata.

    Returns {network: {"bnsl": [(mv, pdg), ...],
                        "llm": [(mv, pdg), ...]}}.
    """
    result: Dict[
        str, Dict[str, List[Tuple[dict, PDG]]]
    ] = {}
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
            src = "bnsl" if is_bnsl else "llm"
            result.setdefault(
                net,
                {"bnsl": [], "llm": []},
            )
            result[net][src].append((mv, pdg))
    return result


def fuse_and_eval(
    bnsl_pdgs: List[PDG],
    llm_pdgs: List[PDG],
    ref_dag,
) -> float:
    """50/50 fusion of BNSL + LLM, return F1."""
    bm = merge_graphs(bnsl_pdgs)
    lm = merge_graphs(llm_pdgs)
    fused = merge_graphs(
        [bm, lm], weights=[0.5, 0.5]
    )
    r = fused.to_dag_greedy(threshold=THRESHOLD)
    return pdag_compare(r.dag, ref_dag)["f1"]


def solo_eval(
    pdgs: List[PDG], ref_dag,
) -> float:
    """Merge PDGs and evaluate F1."""
    m = merge_graphs(pdgs)
    r = m.to_dag_greedy(threshold=THRESHOLD)
    return pdag_compare(r.dag, ref_dag)["f1"]


# -- Filter helpers --

def llm_model(mv: dict) -> str:
    """Extract short LLM model name."""
    m = mv.get("llm_model", "")
    if "gemini" in m:
        return "gemini"
    if "anthropic" in m or "claude" in m:
        return "claude"
    return "gpt"


def llm_seed(mv: dict) -> str:
    """Extract LLM seed."""
    return str(mv.get("llm_seed", ""))


def bnsl_algo(mv: dict) -> str:
    """Extract BNSL algorithm name."""
    s = mv.get("series", "")
    if "FGES" in s:
        return "fges"
    if "PC" in s:
        return "pc"
    return "tabu"


def bnsl_sample(mv: dict) -> str:
    """Extract BNSL sample size."""
    return mv.get("sample_size", "")


def llm_prompt(mv: dict) -> str:
    """Extract LLM prompt detail level."""
    return mv.get("prompt_detail", "")


def filter_pdgs(
    entries: List[Tuple[dict, PDG]],
    key_fn,
    keep_value: str,
) -> List[PDG]:
    """Filter entries by metadata key value."""
    return [
        pdg for mv, pdg in entries
        if key_fn(mv) == keep_value
    ]


def all_pdgs(
    entries: List[Tuple[dict, PDG]],
) -> List[PDG]:
    """Extract all PDGs from entries."""
    return [pdg for _, pdg in entries]


def print_table(
    title: str,
    description: str,
    col_labels: List[str],
    rows: Dict[str, Dict[str, float]],
    networks: List[str],
) -> None:
    """Print a formatted results table."""
    w = 9
    hdr = f"{'Network':<12}"
    for label in col_labels:
        hdr += f" | {label:>{w}}"
    sep = "-" * len(hdr)

    print()
    print(title)
    print(f"  {description}")
    print()
    print(sep)
    print(hdr)
    print(sep)

    totals: Dict[str, float] = {
        c: 0.0 for c in col_labels
    }
    nn = 0

    for net in networks:
        nr = rows.get(net)
        if not nr:
            continue
        row = f"{net:<12}"
        for c in col_labels:
            val = nr.get(c)
            if val is not None:
                row += f" | {val:>{w}.3f}"
                totals[c] += val
            else:
                row += f" | {'n/a':>{w}}"
        print(row)
        nn += 1

    if nn > 0:
        print(sep)
        row = f"{'AVERAGE':<12}"
        for c in col_labels:
            avg = totals[c] / nn
            row += f" | {avg:>{w}.3f}"
        print(row)

    return totals, nn


def main():
    """Run all ablation analyses."""
    cache_path = str(RESULTS_DIR / "pdgs.db")
    data = load_pdgs(cache_path)

    # ------------------------------------------------
    # Table 1: LLM ablation
    # Full BNSL ensemble fused with each LLM subset
    # ------------------------------------------------
    llm_cols = [
        "BNSL", "Gemini", "Claude", "GPT",
        "B+Gem", "B+Cla", "B+GPT", "B+All",
    ]
    llm_rows: Dict[str, Dict[str, float]] = {}

    for net in NETWORKS:
        d = data.get(net)
        if not d:
            continue
        bnsl_all = all_pdgs(d["bnsl"])
        llm_all = all_pdgs(d["llm"])
        if not bnsl_all or not llm_all:
            continue

        ref = read_bn(
            str(NETWORKS_DIR / net / f"{net}.xdsl")
        ).dag

        gem = filter_pdgs(
            d["llm"], llm_model, "gemini"
        )
        cla = filter_pdgs(
            d["llm"], llm_model, "claude"
        )
        gpt = filter_pdgs(
            d["llm"], llm_model, "gpt"
        )

        nr: Dict[str, float] = {}
        nr["BNSL"] = solo_eval(bnsl_all, ref)

        # Solo LLMs
        for label, pdgs in [
            ("Gemini", gem),
            ("Claude", cla),
            ("GPT", gpt),
        ]:
            if pdgs:
                nr[label] = solo_eval(pdgs, ref)

        # Each LLM fused with full BNSL
        for label, pdgs in [
            ("B+Gem", gem),
            ("B+Cla", cla),
            ("B+GPT", gpt),
        ]:
            if pdgs:
                nr[label] = fuse_and_eval(
                    bnsl_all, pdgs, ref,
                )

        # All 3 LLMs fused with BNSL
        nr["B+All"] = fuse_and_eval(
            bnsl_all, llm_all, ref,
        )
        llm_rows[net] = nr

    totals, nn = print_table(
        "LLM ABLATION",
        "Full BNSL ensemble fused with "
        "each LLM (50/50)",
        llm_cols,
        llm_rows,
        NETWORKS,
    )

    if nn > 0:
        avg_singles = []
        for k in ["B+Gem", "B+Cla", "B+GPT"]:
            avg_singles.append(totals[k] / nn)
        avg_single = sum(avg_singles) / 3
        avg_all = totals["B+All"] / nn
        print()
        print("Interpretation:")
        print(
            f"  Avg single-LLM fusion = "
            f"{avg_single:.3f}"
        )
        print(
            f"  Avg 3-LLM fusion      = "
            f"{avg_all:.3f}"
        )
        print(
            f"  Multi-LLM diversity   = "
            f"{avg_all - avg_single:+.3f}"
        )

    # ------------------------------------------------
    # Table 2: BNSL algorithm ablation
    # Full LLM ensemble fused with each BNSL algo
    # ------------------------------------------------
    bnsl_algo_cols = [
        "LLM", "FGES", "Tabu", "PC",
        "F+LLM", "T+LLM", "P+LLM", "All+LLM",
    ]
    bnsl_algo_rows: Dict[str, Dict[str, float]] = {}

    for net in NETWORKS:
        d = data.get(net)
        if not d:
            continue
        bnsl_all = all_pdgs(d["bnsl"])
        llm_all = all_pdgs(d["llm"])
        if not bnsl_all or not llm_all:
            continue

        ref = read_bn(
            str(NETWORKS_DIR / net / f"{net}.xdsl")
        ).dag

        fges = filter_pdgs(
            d["bnsl"], bnsl_algo, "fges"
        )
        tabu = filter_pdgs(
            d["bnsl"], bnsl_algo, "tabu"
        )
        pc = filter_pdgs(
            d["bnsl"], bnsl_algo, "pc"
        )

        nr = {}
        nr["LLM"] = solo_eval(llm_all, ref)

        for label, pdgs in [
            ("FGES", fges),
            ("Tabu", tabu),
            ("PC", pc),
        ]:
            if pdgs:
                nr[label] = solo_eval(pdgs, ref)

        for label, pdgs in [
            ("F+LLM", fges),
            ("T+LLM", tabu),
            ("P+LLM", pc),
        ]:
            if pdgs:
                nr[label] = fuse_and_eval(
                    pdgs, llm_all, ref,
                )

        nr["All+LLM"] = fuse_and_eval(
            bnsl_all, llm_all, ref,
        )
        bnsl_algo_rows[net] = nr

    totals, nn = print_table(
        "BNSL ALGORITHM ABLATION",
        "Full LLM ensemble fused with "
        "each BNSL algo (50/50)",
        bnsl_algo_cols,
        bnsl_algo_rows,
        NETWORKS,
    )

    if nn > 0:
        avg_singles = []
        for k in ["F+LLM", "T+LLM", "P+LLM"]:
            avg_singles.append(totals[k] / nn)
        avg_single = sum(avg_singles) / 3
        avg_all = totals["All+LLM"] / nn
        print()
        print("Interpretation:")
        print(
            f"  Avg single-algo fusion = "
            f"{avg_single:.3f}"
        )
        print(
            f"  Avg 3-algo fusion      = "
            f"{avg_all:.3f}"
        )
        print(
            f"  Multi-algo diversity   = "
            f"{avg_all - avg_single:+.3f}"
        )

    # ------------------------------------------------
    # Table 3: BNSL sample size ablation
    # Full LLM ensemble fused with each sample size
    # ------------------------------------------------
    ss_cols = [
        "1K only", "10K only", "Both",
        "1K+LLM", "10K+LLM", "Both+LLM",
    ]
    ss_rows: Dict[str, Dict[str, float]] = {}

    for net in NETWORKS:
        d = data.get(net)
        if not d:
            continue
        bnsl_all = all_pdgs(d["bnsl"])
        llm_all = all_pdgs(d["llm"])
        if not bnsl_all or not llm_all:
            continue

        ref = read_bn(
            str(NETWORKS_DIR / net / f"{net}.xdsl")
        ).dag

        b1k = filter_pdgs(
            d["bnsl"], bnsl_sample, "1K"
        )
        b10k = filter_pdgs(
            d["bnsl"], bnsl_sample, "10K"
        )

        nr = {}
        if b1k:
            nr["1K only"] = solo_eval(b1k, ref)
        if b10k:
            nr["10K only"] = solo_eval(b10k, ref)
        nr["Both"] = solo_eval(bnsl_all, ref)

        if b1k:
            nr["1K+LLM"] = fuse_and_eval(
                b1k, llm_all, ref,
            )
        if b10k:
            nr["10K+LLM"] = fuse_and_eval(
                b10k, llm_all, ref,
            )
        nr["Both+LLM"] = fuse_and_eval(
            bnsl_all, llm_all, ref,
        )
        ss_rows[net] = nr

    totals, nn = print_table(
        "BNSL SAMPLE SIZE ABLATION",
        "Full LLM ensemble fused with "
        "each BNSL sample size (50/50)",
        ss_cols,
        ss_rows,
        NETWORKS,
    )

    if nn > 0:
        avg_1k = totals["1K+LLM"] / nn
        avg_10k = totals["10K+LLM"] / nn
        avg_both = totals["Both+LLM"] / nn
        best_single = max(avg_1k, avg_10k)
        print()
        print("Interpretation:")
        print(
            f"  1K+LLM   = {avg_1k:.3f}"
        )
        print(
            f"  10K+LLM  = {avg_10k:.3f}"
        )
        print(
            f"  Both+LLM = {avg_both:.3f}"
        )
        print(
            f"  Sample diversity = "
            f"{avg_both - best_single:+.3f}"
        )

    # ------------------------------------------------
    # Table 4: LLM seed ablation
    # Full BNSL + single LLM seed vs multi-seed
    # ------------------------------------------------
    seed_cols = [
        "Seed 0", "Seed 1", "Seed 2",
        "S0+BNSL", "S1+BNSL", "S2+BNSL",
        "All+BNSL",
    ]
    seed_rows: Dict[str, Dict[str, float]] = {}

    for net in NETWORKS:
        d = data.get(net)
        if not d:
            continue
        bnsl_all = all_pdgs(d["bnsl"])
        llm_all = all_pdgs(d["llm"])
        if not bnsl_all or not llm_all:
            continue

        ref = read_bn(
            str(NETWORKS_DIR / net / f"{net}.xdsl")
        ).dag

        nr = {}
        for seed_val in ["0", "1", "2"]:
            sp = filter_pdgs(
                d["llm"], llm_seed, seed_val,
            )
            if sp:
                slabel = f"Seed {seed_val}"
                nr[slabel] = solo_eval(sp, ref)
                flabel = f"S{seed_val}+BNSL"
                nr[flabel] = fuse_and_eval(
                    bnsl_all, sp, ref,
                )

        nr["All+BNSL"] = fuse_and_eval(
            bnsl_all, llm_all, ref,
        )
        seed_rows[net] = nr

    totals, nn = print_table(
        "LLM SEED ABLATION",
        "Full BNSL ensemble fused with "
        "LLM PDGs from each seed (50/50)",
        seed_cols,
        seed_rows,
        NETWORKS,
    )

    if nn > 0:
        avg_singles = []
        for k in [
            "S0+BNSL", "S1+BNSL", "S2+BNSL",
        ]:
            avg_singles.append(totals[k] / nn)
        avg_single = sum(avg_singles) / 3
        avg_all = totals["All+BNSL"] / nn
        print()
        print("Interpretation:")
        print(
            f"  Avg single-seed fusion = "
            f"{avg_single:.3f}"
        )
        print(
            f"  Avg 3-seed fusion      = "
            f"{avg_all:.3f}"
        )
        print(
            f"  Multi-seed diversity   = "
            f"{avg_all - avg_single:+.3f}"
        )

    # ------------------------------------------------
    # Table 5: LLM prompt detail ablation
    # Full BNSL + minimal/standard/both prompts
    # ------------------------------------------------
    prompt_cols = [
        "Minimal", "Standard", "Both",
        "Min+BNSL", "Std+BNSL", "Both+BNSL",
    ]
    prompt_rows: Dict[str, Dict[str, float]] = {}

    for net in NETWORKS:
        d = data.get(net)
        if not d:
            continue
        bnsl_all = all_pdgs(d["bnsl"])
        llm_all = all_pdgs(d["llm"])
        if not bnsl_all or not llm_all:
            continue

        ref = read_bn(
            str(NETWORKS_DIR / net / f"{net}.xdsl")
        ).dag

        nr = {}
        for pval, slabel, flabel in [
            ("minimal", "Minimal", "Min+BNSL"),
            ("standard", "Standard", "Std+BNSL"),
        ]:
            pp = filter_pdgs(
                d["llm"], llm_prompt, pval,
            )
            if pp:
                nr[slabel] = solo_eval(pp, ref)
                nr[flabel] = fuse_and_eval(
                    bnsl_all, pp, ref,
                )

        nr["Both"] = solo_eval(llm_all, ref)
        nr["Both+BNSL"] = fuse_and_eval(
            bnsl_all, llm_all, ref,
        )
        prompt_rows[net] = nr

    totals, nn = print_table(
        "LLM PROMPT DETAIL ABLATION",
        "Full BNSL ensemble fused with "
        "minimal/standard/both prompts (50/50)",
        prompt_cols,
        prompt_rows,
        NETWORKS,
    )

    if nn > 0:
        avg_min = totals["Min+BNSL"] / nn
        avg_std = totals["Std+BNSL"] / nn
        avg_both = totals["Both+BNSL"] / nn
        best_single = max(avg_min, avg_std)
        print()
        print("Interpretation:")
        print(
            f"  Min+BNSL  = {avg_min:.3f}"
        )
        print(
            f"  Std+BNSL  = {avg_std:.3f}"
        )
        print(
            f"  Both+BNSL = {avg_both:.3f}"
        )
        print(
            f"  Prompt diversity = "
            f"{avg_both - best_single:+.3f}"
        )


if __name__ == "__main__":
    import io
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    main()
    sys.stdout = old_stdout
    text = buf.getvalue()
    out = base / "scratch" / "ablation_output.txt"
    out.write_text(text)
    print(text, end="")
