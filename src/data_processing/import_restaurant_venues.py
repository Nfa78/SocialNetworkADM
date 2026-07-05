import argparse
import csv
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.data_processing.paths import RESTAURANT_DATASET_PATH
from src.repositories.mongo_repository import VenueRepository
from src.repositories.neo4j_repository import Neo4jRepository


def parse_float(value: str) -> float | None:
    value = value.strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def split_cuisines(value: str) -> list[str]:
    return [cuisine.strip() for cuisine in value.split(",") if cuisine.strip()]


def build_venue_document(row: dict[str, str]) -> dict[str, Any]:
    restaurant_id = row["Restaurant ID"].strip()
    longitude = parse_float(row.get("Longitude", ""))
    latitude = parse_float(row.get("Latitude", ""))
    cuisines = split_cuisines(row.get("Cuisines", ""))
    primary_category = cuisines[0] if cuisines else "restaurant"

    document: dict[str, Any] = {
        "_id": f"restaurant_{restaurant_id}",
        "source": "kaggle_restaurant_dataset",
        "source_id": restaurant_id,
        "name": row["Restaurant Name"].strip(),
        "domain": "gastronomy",
        "category": primary_category,
        "city": row["City"].strip(),
        "created_at": datetime.now(UTC),
        "address": row.get("Address", "").strip(),
        "locality": row.get("Locality", "").strip(),
        "locality_verbose": row.get("Locality Verbose", "").strip(),
        "cuisines": cuisines,
        "country_code": row.get("Country Code", "").strip(),
        "pricing": {
            "average_cost_for_two": parse_float(row.get("Average Cost for two", "")),
            "currency": row.get("Currency", "").strip(),
            "price_range": parse_float(row.get("Price range", "")),
        },
        "features": {
            "has_table_booking": row.get("Has Table booking", "").strip().lower() == "yes",
            "has_online_delivery": row.get("Has Online delivery", "").strip().lower() == "yes",
            "is_delivering_now": row.get("Is delivering now", "").strip().lower() == "yes",
        },
        "rating": {
            "aggregate_rating": parse_float(row.get("Aggregate rating", "")),
            "rating_color": row.get("Rating color", "").strip(),
            "rating_text": row.get("Rating text", "").strip(),
            "votes": parse_float(row.get("Votes", "")),
        },
    }

    if latitude is not None and longitude is not None:
        document["location"] = {
            "type": "Point",
            "coordinates": [longitude, latitude],
        }

    return document


def import_restaurant_venues(csv_path: Path, dry_run: bool = False) -> dict[str, int]:
    repository = VenueRepository()
    graph_repository = Neo4jRepository()
    imported_count = 0

    with csv_path.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            document = build_venue_document(row)
            if not dry_run:
                repository.upsert(document)
                graph_repository.project_venue(document)
            imported_count += 1

    return {"processed": imported_count, "upserted": 0 if dry_run else imported_count}


def main() -> None:
    parser = argparse.ArgumentParser(description="Import restaurant dataset rows as venue documents.")
    parser.add_argument("--csv-path", type=Path, default=RESTAURANT_DATASET_PATH)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.csv_path.exists():
        raise FileNotFoundError(f"Dataset file not found: {args.csv_path}")

    result = import_restaurant_venues(args.csv_path, dry_run=args.dry_run)
    print(result)


if __name__ == "__main__":
    main()
