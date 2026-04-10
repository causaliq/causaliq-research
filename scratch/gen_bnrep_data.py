"""Generate xdsl + 100K data for bnRep networks."""

import sys
from pathlib import Path

base = Path(__file__).resolve().parents[1]
for pkg in ["causaliq-core", "causaliq-data"]:
    p = base.parent / pkg / "src"
    if p.exists():
        sys.path.insert(0, str(p))

from causaliq_core.bn.io import read_bn, write_bn
from causaliq_data import Pandas

NETS = [
    "constructionproductivity",
    "corical",
    "earthquake",
    "kosterhavet",
    "pneumonia",
    "urinary",
]
N_SAMPLES = 100_000

for net in NETS:
    net_dir = base / "networks" / net
    dsc_path = net_dir / f"{net}.dsc"
    xdsl_path = net_dir / f"{net}.xdsl"
    ds_dir = net_dir / "datasets"
    csv_path = ds_dir / f"{net}_100k.csv.gz"

    print(f"\n{'='*60}")
    print(f"Processing: {net}")
    print(f"{'='*60}")

    # Read DSC
    bn = read_bn(str(dsc_path))
    print(
        f"  Loaded: {len(bn.dag.nodes)} nodes, "
        f"{len(bn.dag.edges)} edges"
    )

    # Write XDSL
    write_bn(bn, str(xdsl_path))
    print(f"  Written: {xdsl_path.name}")

    # Generate data
    ds_dir.mkdir(exist_ok=True)
    df = bn.generate_cases(n=N_SAMPLES)
    print(
        f"  Generated: {len(df)} rows, "
        f"{len(df.columns)} cols"
    )

    # Write compressed CSV
    data = Pandas(df=df)
    data.write(str(csv_path))
    print(f"  Written: {csv_path.name}")

print(f"\n{'='*60}")
print("Done — all 6 networks processed.")
