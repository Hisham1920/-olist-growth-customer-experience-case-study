from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"


def main() -> None:
    audit: dict[str, object] = {}
    for path in sorted(RAW.glob("*.csv")):
        df = pd.read_csv(path, low_memory=False)
        audit[path.name] = {
            "rows": int(len(df)),
            "columns": list(df.columns),
            "duplicate_rows": int(df.duplicated().sum()),
            "nulls": {
                column: int(count)
                for column, count in df.isna().sum().items()
                if count
            },
        }

    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
