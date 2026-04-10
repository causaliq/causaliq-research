"""Edge-by-edge analysis of sachs FGES PDG, LLM PDG, and fused PDG
vs ground truth.

Prints a table showing for every node pair:
  - Ground truth edge (if any)
  - FGES PDG probabilities
  - LLM PDG probabilities
  - Fused PDG probabilities
  - Classification (TP, FP, FN)
"""
import sys
import xml.etree.ElementTree as ET
from io import StringIO
from pathlib import Path

# Add package paths
for pkg in ["causaliq-core", "causaliq-workflow"]:
    p = Path(__file__).resolve().parents[2] / pkg / "src"
    if p.exists():
        sys.path.insert(0, str(p))

from causaliq_core.graph.io.graphml import read_pdg
from causaliq_workflow.cache import WorkflowCache


def load_ground_truth(xdsl_path):
    """Extract directed edges from XDSL file."""
    tree = ET.parse(xdsl_path)
    root = tree.getroot()
    edges = set()
    for cpt in root.iter("cpt"):
        child = cpt.get("id")
        parents_el = cpt.find("parents")
        if parents_el is not None and parents_el.text:
            for parent in parents_el.text.strip().split():
                edges.add((parent, child))
    return edges


def load_pdg_from_cache(db_path, key_filter):
    """Load a PDG from a WorkflowCache .db file."""
    with WorkflowCache(db_path) as cache:
        for info in cache.list_entries():
            mv = info["matrix_values"]
            if all(mv.get(k) == v for k, v in key_filter.items()):
                entry = cache.get(mv)
                obj = entry.get_object("pdg")
                if obj:
                    return read_pdg(StringIO(obj.content)), mv
    return None, None


def fmt_prob(p):
    if p < 0.005:
        return "  .  "
    return f"{p:.2f}"


def main():
    base = Path(__file__).resolve().parents[1]
    results = base / "papers" / "pdg-merge" / "results"

    # Ground truth
    gt_edges = load_ground_truth(
        base / "networks" / "sachs" / "sachs.xdsl"
    )
    print(f"Ground truth: {len(gt_edges)} directed edges")
    for s, t in sorted(gt_edges):
        print(f"  {s} -> {t}")
    print()

    # Load PDGs
    llm_pdg, llm_key = load_pdg_from_cache(
        str(results / "llm-pdgs.db"),
        {"network": "sachs", "llm_model": "anthropic/claude-haiku-4-5-20251001",
         "prompt_detail": "minimal"},
    )
    # Also load Gemini for comparison
    llm2_pdg, llm2_key = load_pdg_from_cache(
        str(results / "llm-pdgs.db"),
        {"network": "sachs", "llm_model": "gemini/gemini-2.0-flash",
         "prompt_detail": "minimal"},
    )
    fges_pdg, fges_key = load_pdg_from_cache(
        str(results / "bnsl-pdgs.db"),
        {"network": "sachs", "series": "TETRAD/FGES_BASE4",
         "sample_size": "1K", "pdg_seed": 1},
    )
    fuse_pdg, fuse_key = load_pdg_from_cache(
        str(results / "fuse.db"),
        {"network": "sachs", "llm_model": "anthropic/claude-haiku-4-5-20251001",
         "prompt_detail": "minimal", "series": "TETRAD/FGES_BASE4",
         "sample_size": "1K", "pdg_seed": 1},
    )

    print(f"LLM key:  {llm_key}")
    print(f"LLM2 key: {llm2_key}")
    print(f"FGES key: {fges_key}")
    print(f"Fuse key: {fuse_key}")
    print()

    if not all([llm_pdg, llm2_pdg, fges_pdg, fuse_pdg]):
        print("ERROR: Could not load all PDGs")
        if not llm_pdg:
            print("  Missing: LLM PDG (Claude)")
        if not llm2_pdg:
            print("  Missing: LLM2 PDG (Gemini)")
        if not fges_pdg:
            print("  Missing: FGES PDG")
        if not fuse_pdg:
            print("  Missing: Fused PDG")
        return

    nodes = sorted(llm_pdg.nodes)
    print(f"Nodes: {nodes}")
    print()

    # Header
    hdr = (
        f"{'Pair':<16} {'GT':>5}  "
        f"{'FGES_fwd':>8} {'FGES_bwd':>8} {'FGES_none':>9}  "
        f"{'Cld_fwd':>8} {'Cld_bwd':>8} {'Cld_none':>9}  "
        f"{'Gem_fwd':>8} {'Gem_bwd':>8} {'Gem_none':>9}  "
        f"{'Agree?'}"
    )
    print(hdr)
    print("-" * len(hdr))

    tp = fp = fn = 0
    fges_tp = fges_fp = fges_fn = 0
    llm_tp = llm_fp = llm_fn = 0
    llm2_tp = llm2_fp = llm2_fn = 0
    agree_tp = agree_fp = 0

    for i, a in enumerate(nodes):
        for b in nodes[i + 1:]:
            gt_fwd = (a, b) in gt_edges
            gt_bwd = (b, a) in gt_edges
            has_gt = gt_fwd or gt_bwd
            gt_str = f"{a[0]}->{b[0]}" if gt_fwd else (
                f"{b[0]}->{a[0]}" if gt_bwd else "  -  "
            )

            fges_p = fges_pdg.get_probabilities(a, b)
            llm_p = llm_pdg.get_probabilities(a, b)
            llm2_p = llm2_pdg.get_probabilities(a, b)
            fuse_p = fuse_pdg.get_probabilities(a, b)

            # Determine classification at threshold 0.3
            fges_exists = fges_p.p_exist > 0.3
            llm_exists = llm_p.p_exist > 0.3
            llm2_exists = llm2_p.p_exist > 0.3
            fuse_exists = fuse_p.p_exist > 0.3

            # Agreement between Claude and Gemini
            both_say_edge = llm_exists and llm2_exists
            neither_say_edge = not llm_exists and not llm2_exists
            agree = both_say_edge or neither_say_edge
            agree_str = "YES" if agree else "NO "

            if has_gt and fuse_exists:
                cls = "TP"
                tp += 1
            elif has_gt and not fuse_exists:
                cls = "FN"
                fn += 1
            elif not has_gt and fuse_exists:
                cls = "FP"
                fp += 1
            else:
                cls = "  "

            # FGES standalone
            if has_gt and fges_exists:
                fges_tp += 1
            elif has_gt and not fges_exists:
                fges_fn += 1
            elif not has_gt and fges_exists:
                fges_fp += 1

            # Claude standalone
            if has_gt and llm_exists:
                llm_tp += 1
            elif has_gt and not llm_exists:
                llm_fn += 1
            elif not has_gt and llm_exists:
                llm_fp += 1

            # Gemini standalone
            if has_gt and llm2_exists:
                llm2_tp += 1
            elif has_gt and not llm2_exists:
                llm2_fn += 1
            elif not has_gt and llm2_exists:
                llm2_fp += 1

            # Track agreement on edges
            if both_say_edge and has_gt:
                agree_tp += 1
            elif both_say_edge and not has_gt:
                agree_fp += 1

            # Only print interesting rows
            any_exist = (
                fges_p.p_exist > 0.01
                or llm_p.p_exist > 0.01
                or llm2_p.p_exist > 0.01
                or has_gt
            )
            if not any_exist:
                continue

            row = (
                f"{a+'-'+b:<16} {gt_str:>5}  "
                f"{fmt_prob(fges_p.forward):>8} "
                f"{fmt_prob(fges_p.backward):>8} "
                f"{fmt_prob(fges_p.none):>9}  "
                f"{fmt_prob(llm_p.forward):>8} "
                f"{fmt_prob(llm_p.backward):>8} "
                f"{fmt_prob(llm_p.none):>9}  "
                f"{fmt_prob(llm2_p.forward):>8} "
                f"{fmt_prob(llm2_p.backward):>8} "
                f"{fmt_prob(llm2_p.none):>9}  "
                f"{agree_str}"
            )
            print(row)

    print()
    f1 = lambda tp, fp, fn: (
        2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) > 0 else 0
    )
    print(f"FGES:    TP={fges_tp} FP={fges_fp} FN={fges_fn}"
          f"  F1={f1(fges_tp, fges_fp, fges_fn):.3f}")
    print(f"Claude:  TP={llm_tp} FP={llm_fp} FN={llm_fn}"
          f"  F1={f1(llm_tp, llm_fp, llm_fn):.3f}")
    print(f"Gemini:  TP={llm2_tp} FP={llm2_fp} FN={llm2_fn}"
          f"  F1={f1(llm2_tp, llm2_fp, llm2_fn):.3f}")
    print(f"FUSED:   TP={tp} FP={fp} FN={fn}"
          f"  F1={f1(tp, fp, fn):.3f}")
    print()
    print(f"Both LLMs agree edge exists: {agree_tp} TP, {agree_fp} FP")


if __name__ == "__main__":
    main()
