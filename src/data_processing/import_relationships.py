from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.domain.models import RelationshipCreate
from src.services.relationship_service import RelationshipService


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RELATIONSHIPS_PATH = PROJECT_ROOT / "data" / "synthetic" / "relationships.json"


def load_json_list(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def import_relationships(relationships_path: Path = DEFAULT_RELATIONSHIPS_PATH, dry_run: bool = False) -> dict[str, int]:
    relationship_service = RelationshipService()
    processed = 0

    for row in load_json_list(relationships_path):
        relationship = RelationshipCreate.model_validate(row)
        if not dry_run:
            relationship_service.create_relationship(relationship)
        processed += 1

    return {"processed": processed, "inserted": 0 if dry_run else processed}


def main() -> None:
    parser = argparse.ArgumentParser(description="Import synthetic relationships through the service layer.")
    parser.add_argument("--relationships-path", type=Path, default=DEFAULT_RELATIONSHIPS_PATH)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.relationships_path.exists():
        raise FileNotFoundError(f"Relationships file not found: {args.relationships_path}")

    result = import_relationships(relationships_path=args.relationships_path, dry_run=args.dry_run)
    print(result)


if __name__ == "__main__":
    main()
