"""Analyse LLM PDG diversity across seeds.

For each model/prompt combination, loads all seed PDGs and compares
edge probabilities to identify which edges vary and whether those
are the incorrect arcs.
"""
import sys
import xml.etree.ElementTree as ET
from io import StringIO
from pathlib import Path

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


def gt_canonical(gt_edges):
    """Canonical pair set from directed GT edges."""
    return {tuple(sorted([s, t])) for s, t in gt_edges}


def gt_dir(gt_edges, a, b):
    """GT direction for canonical pair (a < b)."""
    if (a, b) in gt_edges:
        return "fwd"
    if (b, a) in gt_edges:
        return "bwd"
    return None


def load_seed_pdgs(db_path, network, llm_model, prompt_detail):
    """Load all seed PDGs for a model/prompt combo."""
    pdgs = {}
    with WorkflowCache(db_path) as cache:
        for info in cache.list_entries():
            mv = info["matrix_values"]
            if (
                mv.get("network") == network
                and mv.get("llm_model") == llm_model
                and mv.get("prompt_detail") == prompt_detail
            ):
                seed = mv.get("llm_seed")
                entry = cache.get(mv)
                obj = entry.get_object("pdg")
                if obj:
                    pdg = read_pdg(StringIO(obj.content))
                    pdgs[seed] = pdg
    return pdgs


def f(v):
    """Format probability."""
    return " .  " if v < 0.005 else f"{v:.2f}"


def main():
    base = Path(__file__).resolve().parents[1]
    results = base / "papers" / "pdg-merge" / "results"
    db_path = str(results / "pdgs.db")

    gt_edges = load_ground_truth(
        base / "networks" / "sachs" / "sachs.xdsl"
    )
    gt_pairs = gt_canonical(gt_edges)
    print(f"Ground truth: {len(gt_edges)} directed edges\n")

    # Discover model/prompt combos
    combos = set()
    with WorkflowCache(db_path) as cache:
        for info in cache.list_entries():
            mv = info["matrix_values"]
            if (
                mv.get("network") == "sachs"
                and mv.get("llm_model") is not None
            ):
                combos.add((mv["llm_model"], mv["prompt_detail"]))

    for llm_model, prompt_detail in sorted(combos):
        pdgs = load_seed_pdgs(
            db_path, "sachs", llm_model, prompt_detail
        )
        if not pdgs:
            continue

        seeds = sorted(pdgs.keys())
        all_nodes = set()
        for pdg in pdgs.values():
            all_nodes.update(pdg.nodes)
        all_nodes = sorted(all_nodes)

        # Canonical pairs
        pairs = []
        for i, a in enumerate(all_nodes):
            for b in all_nodes[i + 1:]:
                pairs.append((a, b))

        print("=" * 78)
        print(
            f"{llm_model} | {prompt_detail} | "
            f"{len(seeds)} seeds: {seeds}"
        )
        print("=" * 78)

        varying = []
        stable = []

        for a, b in pairs:
            sp = {}
            for seed in seeds:
                sp[seed] = pdgs[seed].get_probabilities(a, b)

            # Check diversity
            sigs = [
                (
                    round(ep.forward, 4),
                    round(ep.backward, 4),
                    round(ep.undirected, 4),
                )
                for ep in sp.values()
            ]
            varies = len(set(sigs)) > 1

            is_gt = (a, b) in gt_pairs
            d = gt_dir(gt_edges, a, b)

            if varies:
                varying.append((a, b, sp, is_gt, d))
            else:
                ep0 = list(sp.values())[0]
                if ep0.p_exist > 0.01 or is_gt:
                    stable.append((a, b, ep0, is_gt, d))

        # Print
        if varying:
            print(f"\n  VARYING ({len(varying)} pairs):")
            hdr = f"  {'Pair':<20} {'GT':>4}"
            for s in seeds:
                hdr += f"  seed={s}: fwd/bwd/und (ex)"
            print(hdr)

            for a, b, sp, is_gt, d in varying:
                gs = f" {d}" if d else "    "
                line = f"  {a:>8}->{b:<8}  {gs}"
                for s in seeds:
                    ep = sp[s]
                    line += (
                        f"  {f(ep.forward)}/{f(ep.backward)}"
                        f"/{f(ep.undirected)}"
                        f" ({f(ep.p_exist)})"
                    )
                print(line)

            # Summary: which varying edges are GT vs not
            gt_vary = sum(1 for _, _, _, ig, _ in varying if ig)
            fp_vary = sum(1 for _, _, _, ig, _ in varying if not ig)
            print(
                f"\n  Varying: {gt_vary} GT edges, "
                f"{fp_vary} non-GT edges"
            )
        else:
            print("\n  NO varying edges — ZERO diversity!")

        if stable:
            print(f"\n  STABLE ({len(stable)} pairs):")
            for a, b, ep, is_gt, d in stable:
                gs = f" {d}" if d else "    "
                ex = ep.p_exist
                st = ep.most_likely_state()
                cls = ""
                if ex > 0.5 and is_gt:
                    cls = "TP"
                elif ex > 0.5 and not is_gt:
                    cls = "FP"
                elif ex <= 0.5 and is_gt:
                    cls = "FN"
                print(
                    f"  {a:>8}->{b:<8}  {gs}  "
                    f"{f(ep.forward)}/{f(ep.backward)}"
                    f"/{f(ep.undirected)}  "
                    f"ex={f(ex)}  {st:>10}  {cls}"
                )

        # Overall diversity metric
        n_vary = len(varying)
        n_total = len(varying) + len(stable)
        n_all = len(pairs)
        print(
            f"\n  Diversity: {n_vary}/{n_total} non-zero pairs vary "
            f"({n_vary}/{n_all} of all pairs)"
        )
        print()


if __name__ == "__main__":
    main()
