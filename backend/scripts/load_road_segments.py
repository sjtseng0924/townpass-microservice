"""Load road centerline GeoJSON into the road_segments table."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text

# When this script is executed directly (python scripts/load_road_segments.py)
# the package root (backend/) may not be on sys.path. Ensure the project
# root is first on sys.path so `from app.config import settings` resolves.
import sys
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.config import settings


def normalize_osmid(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return ",".join(str(item) for item in value)
    return str(value)


def parse_oneway(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "t", "1", "yes", "y"}:
            return True
        if lowered in {"false", "f", "0", "no", "n"}:
            return False
    return None


def parse_length(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def load_rows(file_path: Path) -> list[dict[str, Any]]:
    data = json.loads(file_path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []

    for feature in data.get("features", []):
        geometry = feature.get("geometry")
        if not geometry or geometry.get("type") != "LineString":
            continue

        properties = feature.get("properties") or {}
        osmid = normalize_osmid(properties.get("osmid"))
        if not osmid:
            continue

        rows.append(
            {
                "osmid": osmid,
                "name": properties.get("name"),
                "highway": properties.get("highway"),
                "lanes": properties.get("lanes"),
                "oneway": parse_oneway(properties.get("oneway")),
                "length_m": parse_length(properties.get("length")),
                "properties": json.dumps(properties, ensure_ascii=False),
                "geometry": json.dumps(geometry, ensure_ascii=False),
            }
        )

    return rows


def ingest(file_path: Path) -> int:
    rows = load_rows(file_path)
    if not rows:
        return 0

    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    insert_sql = text(
        """
        INSERT INTO road_segments
            (osmid, name, highway, lanes, oneway, length_m, properties, geometry)
        VALUES
            (:osmid, :name, :highway, :lanes, :oneway, :length_m,
             CAST(:properties AS JSONB), CAST(:geometry AS JSONB))
        ON CONFLICT (osmid) DO UPDATE
        SET name = EXCLUDED.name,
            highway = EXCLUDED.highway,
            lanes = EXCLUDED.lanes,
            oneway = EXCLUDED.oneway,
            length_m = EXCLUDED.length_m,
            properties = EXCLUDED.properties,
            geometry = EXCLUDED.geometry;
        """
    )

    with engine.begin() as connection:
        for row in rows:
            connection.execute(insert_sql, row)

    engine.dispose()
    return len(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load road GeoJSON into Postgres")
    parser.add_argument(
        "geojson",
        type=Path,
        nargs="?",
        default=Path(__file__).resolve().parents[1] / "data" / "TaipeiRoadCenterLine.geojson",
        help="Path to the GeoJSON file (default: data/TaipeiRoadCenterLine.geojson)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    file_path: Path = args.geojson.resolve()
    if not file_path.exists():
        raise FileNotFoundError(f"GeoJSON file not found: {file_path}")

    inserted = ingest(file_path)
    print(f"Processed {inserted} road segments from {file_path}")


if __name__ == "__main__":
    main()
