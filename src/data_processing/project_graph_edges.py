from __future__ import annotations

import argparse
import json
from typing import Any

from src.db import mongo_db
from src.domain.models import content_document_adapter
from src.repositories.neo4j_repository import Neo4jRepository


def _isoformat(value: Any) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def project_content_edges(graph_repository: Neo4jRepository) -> int:
    projected = 0
    for stored_content in mongo_db.content.find({}):
        content = content_document_adapter.validate_python(stored_content)
        graph_repository.project_content(content)
        projected += 1
    return projected


def project_viewed_edges(graph_repository: Neo4jRepository) -> int:
    pipeline: list[dict[str, Any]] = [
        {
            "$match": {
                "type": "view",
                "user_id": {"$exists": True, "$ne": None},
                "content_id": {"$exists": True, "$ne": None},
            }
        },
        {"$sort": {"user_id": 1, "content_id": 1, "created_at": 1}},
        {
            "$group": {
                "_id": {"user_id": "$user_id", "content_id": "$content_id"},
                "count": {"$sum": 1},
                "first_viewed_at": {"$first": "$created_at"},
                "last_viewed_at": {"$last": "$created_at"},
                "total_duration_ms": {"$sum": {"$ifNull": ["$duration_ms", 0]}},
                "last_source": {"$last": "$source"},
            }
        },
    ]

    projected = 0
    for row in mongo_db.interactions.aggregate(pipeline, allowDiskUse=True):
        graph_repository.project_viewed_summary(
            user_id=row["_id"]["user_id"],
            content_id=row["_id"]["content_id"],
            count=int(row.get("count") or 0),
            first_viewed_at=_isoformat(row["first_viewed_at"]),
            last_viewed_at=_isoformat(row["last_viewed_at"]),
            total_duration_ms=int(row.get("total_duration_ms") or 0),
            last_source=row.get("last_source"),
        )
        projected += 1
    return projected


def project_graph_edges(skip_content: bool = False, skip_viewed: bool = False) -> dict[str, int]:
    graph_repository = Neo4jRepository()
    result = {"content_projected": 0, "created_edges_projected": 0, "viewed_edges_projected": 0}

    if not skip_content:
        content_count = project_content_edges(graph_repository)
        result["content_projected"] = content_count
        result["created_edges_projected"] = content_count

    if not skip_viewed:
        result["viewed_edges_projected"] = project_viewed_edges(graph_repository)

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Project MongoDB content authorship and known-user views into Neo4j.")
    parser.add_argument("--skip-content", action="store_true", help="Do not re-project content nodes or CREATED edges.")
    parser.add_argument("--skip-viewed", action="store_true", help="Do not rebuild aggregated VIEWED edges.")
    args = parser.parse_args()

    result = project_graph_edges(skip_content=args.skip_content, skip_viewed=args.skip_viewed)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
