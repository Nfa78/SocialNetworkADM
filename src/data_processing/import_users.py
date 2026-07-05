from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.domain.models import UserCreate
from src.services.user_service import UserService


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_USERS_PATH = PROJECT_ROOT / "data" / "synthetic" / "users.json"


def load_json_list(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def import_users(users_path: Path = DEFAULT_USERS_PATH, dry_run: bool = False) -> dict[str, int]:
    user_service = UserService()
    processed = 0

    for row in load_json_list(users_path):
        user = UserCreate.model_validate(row)
        if not dry_run:
            user_service.upsert_user(user)
        processed += 1

    return {"processed": processed, "upserted": 0 if dry_run else processed}


def main() -> None:
    parser = argparse.ArgumentParser(description="Import synthetic users through the service layer.")
    parser.add_argument("--users-path", type=Path, default=DEFAULT_USERS_PATH)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.users_path.exists():
        raise FileNotFoundError(f"Users file not found: {args.users_path}")

    result = import_users(users_path=args.users_path, dry_run=args.dry_run)
    print(result)


if __name__ == "__main__":
    main()
