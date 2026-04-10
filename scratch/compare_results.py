"""Quick comparison: BNSL alone vs LLM alone vs Fused."""
from pathlib import Path


def avg(vals):
    return sum(vals) / len(vals) if vals else 0


def read_f1_by_network(csv_path, filter_fn=None):
    """Read F1 scores grouped by network from a CSV."""
    result = {}
    with open(csv_path) as f:
        lines = f.readlines()
    header = [h.strip() for h in lines[0].split(",")]

    for line in lines[1:]:
        parts = [p.strip() for p in line.split(",")]
        if filter_fn and not filter_fn(parts):
            continue
        net = parts[0]
        # Find f1.mean - it's the first metric after key columns
        # Use header length to figure out column positions
        if len(parts) == len(header):
            try:
                idx = header.index("f1.mean")
                f1 = float(parts[idx])
            except (ValueError, IndexError):
                continue
        else:
            # Schema mismatch - skip
            continue
        if net not in result:
            result[net] = []
        result[net].append(f1)
    return result


base = Path(__file__).resolve().parents[1]
results = base / "papers" / "pdg-merge" / "results"

# BNSL
bnsl = read_f1_by_network(results / "bnsl-pdgs.csv")

# LLM
llm = read_f1_by_network(results / "llm-pdgs.csv")

# Fuse - read from fuse.db directly to avoid CSV schema issues
import sys
for pkg in ["causaliq-core", "causaliq-workflow"]:
    p = base.parent / pkg / "src"
    if p.exists():
        sys.path.insert(0, str(p))

from causaliq_workflow.cache import WorkflowCache

fuse = {}
fuse_equiv = {}
with WorkflowCache(str(results / "fuse.db")) as cache:
    for info in cache.list_entries():
        mv = info["matrix_values"]
        entry = cache.get(mv)
        eg = entry.metadata.get("causaliq-analysis", {}).get(
            "evaluate_graph", {}
        )
        net = mv["network"]

        f1 = eg.get("f1")
        equiv_f1 = eg.get("equiv.f1")
        if f1 is not None:
            fuse.setdefault(net, []).append(f1)
        if equiv_f1 is not None:
            fuse_equiv.setdefault(net, []).append(equiv_f1)

print("=" * 85)
print(
    f"{'Network':<10} | {'BNSL F1':>10} | {'LLM F1':>10} | "
    f"{'Fused F1':>10} | {'Best single':>12} | {'Delta':>8}"
)
print("-" * 85)

for net in ["alarm", "asia", "child", "covid", "diarrhoea", "insurance", "property", "sports", "sachs", "water"]:
    b = avg(bnsl.get(net, []))
    l = avg(llm.get(net, []))
    fu = avg(fuse.get(net, []))
    best = max(b, l)
    delta = fu - best
    sign = "+" if delta > 0 else ""
    print(
        f"{net:<10} | {b:>10.3f} | {l:>10.3f} | "
        f"{fu:>10.3f} | {best:>12.3f} | {sign}{delta:>7.3f}"
    )

print()
print("Breakdown by configuration (Fused):")
print("-" * 85)

with WorkflowCache(str(results / "fuse.db")) as cache:
    rows = []
    for info in cache.list_entries():
        mv = info["matrix_values"]
        entry = cache.get(mv)
        eg = entry.metadata.get("causaliq-analysis", {}).get(
            "evaluate_graph", {}
        )
        f1 = eg.get("f1")
        shd = eg.get("shd")
        eq_f1 = eg.get("equiv.f1")
        if f1 is None:
            continue
        rows.append((
            mv["network"],
            mv.get("llm_model", ""),
            mv.get("prompt_detail", ""),
            mv.get("sample_size", ""),
            mv.get("pdg_seed", ""),
            f1, shd, eq_f1,
        ))

    rows.sort()
    print(
        f"{'Net':<7} {'Model':<20} {'Prompt':<10} "
        f"{'Size':<5} {'Seed':<5} "
        f"{'F1':>6} {'SHD':>6} {'eq.F1':>6}"
    )
    for net, model, prompt, size, seed, f1, shd, eq_f1 in rows:
        m = model.split("/")[-1] if model else ""
        print(
            f"{net:<7} {m:<20} {prompt:<10} "
            f"{str(size):<5} {str(seed):<5} "
            f"{f1:>6.3f} {shd:>6.1f} {eq_f1:>6.3f}"
        )
