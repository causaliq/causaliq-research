"""Check whether LLM's persistent FN edges are found by BNSL.

Loads LLM and BNSL PDGs from the shared pdgs.db cache and compares
which GT edges each method finds vs misses.
"""
import sys
import xml.etree.ElementTree as ET
from io import StringIO
from pathlib import Path

for pkg in ["causaliq-core", "causaliq-workflow", "causaliq-analysis"]:
    p = Path(__file__).resolve().parents[2] / pkg / "src"
    if p.exists():
        sys.path.insert(0, str(p))

from causaliq_core.graph.io.graphml import read_pdg
from causaliq_workflow.cache import WorkflowCache


def load_ground_truth(xdsl_path):
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


def gt_canonical(gt_edges):
    return {tuple(sorted([s, t])) for s, t in gt_edges}


def gt_dir(gt_edges, a, b):
    if (a, b) in gt_edges:
        return "fwd"
    if (b, a) in gt_edges:
        return "bwd"
    return None


def f(v):
    return " .  " if v < 0.005 else f"{v:.2f}"


def load_pdgs_by_filter(db_path, network, is_llm):
    """Load PDGs grouped by key."""
    pdgs = []
    with WorkflowCache(db_path) as cache:
        for info in cache.list_entries():
            mv = info["matrix_values"]
            if mv.get("network") != network:
                continue
            if is_llm and mv.get("llm_model") is None:
                continue
            if not is_llm and mv.get("series") is None:
                continue
            entry = cache.get(mv)
            obj = entry.get_object("pdg")
            if obj:
                pdg = read_pdg(StringIO(obj.content))
                pdgs.append((mv, pdg))
    return pdgs


def load_bnsl_pdgs_from_traces(bnsl_db_path, network):
    """Build BNSL PDGs by merging FGES traces from bnsl.db.

    Merges all traces for each (network, series, sample_size) combo
    into a single PDG using average strategy, mimicking what
    bnsl-pdgs.yml does.
    """
    from causaliq_analysis.merge import merge_graphs
    from causaliq_core.graph.io import graphml

    pdgs = []
    # Group traces by (series, sample_size)
    groups = {}
    with WorkflowCache(bnsl_db_path) as cache:
        for info in cache.list_entries():
            mv = info["matrix_values"]
            if mv.get("network") != network:
                continue
            key = (mv.get("series"), mv.get("sample_size"))
            entry = cache.get(mv)
            obj = entry.get_object("dag")
            if obj:
                g = graphml.read(StringIO(obj.content))
                if key not in groups:
                    groups[key] = []
                groups[key].append(g)

    for (series, sample_size), graphs in groups.items():
        if len(graphs) < 2:
            continue
        pdg = merge_graphs(graphs, strategy="average")
        mv = {
            "network": network,
            "series": series,
            "sample_size": sample_size,
        }
        pdgs.append((mv, pdg))

    return pdgs


def main():
    base = Path(__file__).resolve().parents[1]
    results = base / "papers" / "pdg-merge" / "results"
    db_path = str(results / "pdgs.db")

    gt_edges = load_ground_truth(
        base / "networks" / "sachs" / "sachs.xdsl"
    )
    gt_pairs = sorted(gt_canonical(gt_edges))
    print(f"Ground truth: {len(gt_edges)} directed edges\n")

    # Load all LLM and BNSL PDGs
    llm_pdgs = load_pdgs_by_filter(db_path, "sachs", is_llm=True)

    # Try pdgs.db first; fall back to merging from bnsl.db
    bnsl_pdgs = load_pdgs_by_filter(db_path, "sachs", is_llm=False)
    if not bnsl_pdgs:
        bnsl_db = str(results / "bnsl.db")
        bnsl_pdgs = load_bnsl_pdgs_from_traces(bnsl_db, "sachs")
        if bnsl_pdgs:
            print("(BNSL PDGs built from bnsl.db traces)")

    print(f"LLM PDGs:  {len(llm_pdgs)}")
    print(f"BNSL PDGs: {len(bnsl_pdgs)}\n")

    # For each GT edge, compute coverage across methods
    print(
        f"  {'GT Edge':<20} {'Dir':>4}  "
        f"{'LLM exist (mean/min/max)':>26}  "
        f"{'BNSL exist (mean/min/max)':>26}  "
        f"{'Verdict'}"
    )
    print("  " + "-" * 95)

    llm_only = []
    bnsl_only = []
    both = []
    neither = []

    for a, b in gt_pairs:
        d = gt_dir(gt_edges, a, b)

        # LLM existence across all seeds/models
        llm_exist = []
        for mv, pdg in llm_pdgs:
            ep = pdg.get_probabilities(a, b)
            llm_exist.append(ep.p_exist)

        # BNSL existence across all seeds/sample sizes
        bnsl_exist = []
        for mv, pdg in bnsl_pdgs:
            ep = pdg.get_probabilities(a, b)
            bnsl_exist.append(ep.p_exist)

        llm_mean = sum(llm_exist) / len(llm_exist) if llm_exist else 0
        llm_min = min(llm_exist) if llm_exist else 0
        llm_max = max(llm_exist) if llm_exist else 0

        bnsl_mean = sum(bnsl_exist) / len(bnsl_exist) if bnsl_exist else 0
        bnsl_min = min(bnsl_exist) if bnsl_exist else 0
        bnsl_max = max(bnsl_exist) if bnsl_exist else 0

        llm_finds = llm_mean > 0.3
        bnsl_finds = bnsl_mean > 0.3

        if llm_finds and bnsl_finds:
            verdict = "BOTH"
            both.append((a, b))
        elif llm_finds:
            verdict = "LLM only"
            llm_only.append((a, b))
        elif bnsl_finds:
            verdict = "BNSL only"
            bnsl_only.append((a, b))
        else:
            verdict = "NEITHER"
            neither.append((a, b))

        print(
            f"  {a:>8}->{b:<8}  {d:>4}  "
            f"  {f(llm_mean)} ({f(llm_min)}-{f(llm_max)})       "
            f"  {f(bnsl_mean)} ({f(bnsl_min)}-{f(bnsl_max)})       "
            f"  {verdict}"
        )

    print()
    print(f"  BOTH find:   {len(both):>2} — {both}")
    print(f"  LLM only:    {len(llm_only):>2} — {llm_only}")
    print(f"  BNSL only:   {len(bnsl_only):>2} — {bnsl_only}")
    print(f"  NEITHER:     {len(neither):>2} — {neither}")
    print()

    complement = len(both) + len(llm_only) + len(bnsl_only)
    print(
        f"  Fusion potential: {complement}/{len(gt_pairs)} GT edges "
        f"found by at least one method"
    )

    # Also check FP edges: non-GT edges proposed by LLM
    print("\n" + "=" * 78)
    print("Non-GT edges (potential FPs)")
    print("=" * 78)

    all_nodes = set()
    for _, pdg in llm_pdgs + bnsl_pdgs:
        all_nodes.update(pdg.nodes)
    all_nodes = sorted(all_nodes)

    all_pairs = []
    for i, a in enumerate(all_nodes):
        for b2 in all_nodes[i + 1:]:
            all_pairs.append((a, b2))

    gt_set = set(gt_pairs)
    non_gt = [p for p in all_pairs if p not in gt_set]

    print(
        f"\n  {'Non-GT Edge':<20}  "
        f"{'LLM exist (mean)':>16}  "
        f"{'BNSL exist (mean)':>17}  "
        f"{'Risk'}"
    )
    print("  " + "-" * 70)

    for a, b in non_gt:
        llm_exist = []
        for mv, pdg in llm_pdgs:
            ep = pdg.get_probabilities(a, b)
            llm_exist.append(ep.p_exist)
        bnsl_exist = []
        for mv, pdg in bnsl_pdgs:
            ep = pdg.get_probabilities(a, b)
            bnsl_exist.append(ep.p_exist)

        llm_mean = sum(llm_exist) / len(llm_exist) if llm_exist else 0
        bnsl_mean = (
            sum(bnsl_exist) / len(bnsl_exist) if bnsl_exist else 0
        )

        # Only show edges with non-trivial probability
        if llm_mean > 0.1 or bnsl_mean > 0.1:
            risk = ""
            if llm_mean > 0.5:
                risk += "LLM-FP "
            if bnsl_mean > 0.5:
                risk += "BNSL-FP "
            print(
                f"  {a:>8}->{b:<8}    "
                f"{f(llm_mean):>8}            "
                f"{f(bnsl_mean):>8}            "
                f"  {risk}"
            )

    print()


if __name__ == "__main__":
    main()
