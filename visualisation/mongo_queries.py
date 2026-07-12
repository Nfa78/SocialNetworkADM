from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pymongo.database import Database


@dataclass(frozen=True)
class DashboardFilters:
    start: datetime | None = None
    end: datetime | None = None
    city: str | None = None
    content_type: str | None = None
    style: str | None = None
    category: str | None = None
    sentiment: str | None = None
    interaction_source: str | None = None


@dataclass(frozen=True)
class FilterOption:
    value: str
    relevance: int


VIRALITY_CONTENT_TYPES = ("post", "comment")


def _clean_values(values: list[Any]) -> list[str]:
    return sorted({str(value).strip() for value in values if str(value).strip()})


def _add_relevance_score(scores: dict[str, int], value: Any, amount: Any) -> None:
    option_value = str(value).strip() if value is not None else ""
    if not option_value:
        return

    try:
        score = int(amount or 0)
    except (TypeError, ValueError):
        score = 0

    scores[option_value] = scores.get(option_value, 0) + score


def _ranked_filter_options(scores: dict[str, int]) -> list[FilterOption]:
    return [
        FilterOption(value=value, relevance=relevance)
        for value, relevance in sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    ]


def _add_collection_field_counts(
    database: Database[dict[str, Any]],
    scores: dict[str, int],
    collection: str,
    field: str,
) -> None:
    rows = _aggregate(
        database,
        collection,
        [
            {"$group": {"_id": f"${field}", "count": {"$sum": 1}}},
        ],
    )
    for row in rows:
        _add_relevance_score(scores, row.get("_id"), row.get("count"))


def _city_filter_options(database: Database[dict[str, Any]]) -> list[FilterOption]:
    scores: dict[str, int] = {}
    _add_collection_field_counts(database, scores, "users", "city")
    _add_collection_field_counts(database, scores, "venues", "city")
    return _ranked_filter_options(scores)


def _content_attribute_filter_options(database: Database[dict[str, Any]], field: str) -> list[FilterOption]:
    scores: dict[str, int] = {}
    _add_collection_field_counts(database, scores, "content", field)
    return _ranked_filter_options(scores)


def _interaction_source_filter_options(database: Database[dict[str, Any]]) -> list[FilterOption]:
    scores: dict[str, int] = {}
    _add_collection_field_counts(database, scores, "interactions", "source")
    return _ranked_filter_options(scores)


def _date_condition(filters: DashboardFilters) -> dict[str, Any]:
    condition: dict[str, Any] = {"$type": "date"}
    if filters.start is not None:
        condition["$gte"] = filters.start
    if filters.end is not None:
        condition["$lte"] = filters.end
    return condition


def _date_match(field: str, filters: DashboardFilters) -> dict[str, Any]:
    return {field: _date_condition(filters)}


def _content_attribute_match(filters: DashboardFilters, prefix: str = "") -> dict[str, Any]:
    match: dict[str, Any] = {}
    if filters.content_type:
        match[f"{prefix}type"] = filters.content_type
    if filters.style:
        match[f"{prefix}style"] = filters.style
    if filters.category:
        match[f"{prefix}category"] = filters.category
    if filters.sentiment:
        match[f"{prefix}sentiment.label"] = filters.sentiment
    return match


def _virality_content_types(filters: DashboardFilters, content_types: tuple[str, ...] | None = None) -> tuple[str, ...]:
    allowed = set(VIRALITY_CONTENT_TYPES)
    selected = tuple(content_type for content_type in (content_types or VIRALITY_CONTENT_TYPES) if content_type in allowed)

    if filters.content_type:
        if filters.content_type not in allowed:
            return ()
        if selected and filters.content_type not in selected:
            return ()
        return (filters.content_type,)

    return selected


def _content_pipeline_prefix(filters: DashboardFilters) -> list[dict[str, Any]]:
    match = {
        **_date_match("created_at", filters),
        **_content_attribute_match(filters),
    }
    pipeline: list[dict[str, Any]] = [{"$match": match}]

    if filters.city:
        pipeline.extend(
            [
                {"$lookup": {"from": "venues", "localField": "venue_id", "foreignField": "_id", "as": "venue"}},
                {"$unwind": "$venue"},
                {"$match": {"venue.city": filters.city}},
            ]
        )

    return pipeline


def _interaction_pipeline_prefix(filters: DashboardFilters) -> list[dict[str, Any]]:
    match = _date_match("created_at", filters)
    if filters.interaction_source:
        match["source"] = filters.interaction_source

    pipeline: list[dict[str, Any]] = [{"$match": match}]
    needs_content_lookup = any(
        [
            filters.content_type,
            filters.style,
            filters.category,
            filters.sentiment,
            filters.city,
        ]
    )

    if needs_content_lookup:
        pipeline.extend(
            [
                {"$lookup": {"from": "content", "localField": "content_id", "foreignField": "_id", "as": "content_doc"}},
                {"$unwind": "$content_doc"},
            ]
        )

        content_match = _content_attribute_match(filters, "content_doc.")
        if content_match:
            pipeline.append({"$match": content_match})

        if filters.city:
            pipeline.extend(
                [
                    {"$lookup": {"from": "venues", "localField": "content_doc.venue_id", "foreignField": "_id", "as": "venue"}},
                    {"$unwind": "$venue"},
                    {"$match": {"venue.city": filters.city}},
                ]
            )

    return pipeline


def _user_match(filters: DashboardFilters) -> dict[str, Any]:
    match = _date_match("created_at", filters)
    if filters.city:
        match["city"] = filters.city
    return match


def _venue_match(filters: DashboardFilters) -> dict[str, Any]:
    if filters.city:
        return {"city": filters.city}
    return {}


def _relationship_match(filters: DashboardFilters, relationship_type: str | None = None) -> dict[str, Any]:
    match = _date_match("created_at", filters)
    if relationship_type:
        match["type"] = relationship_type
    return match


def _count_pipeline(database: Database[dict[str, Any]], collection: str, pipeline: list[dict[str, Any]]) -> int:
    rows = list(database[collection].aggregate([*pipeline, {"$count": "count"}], allowDiskUse=True))
    return int(rows[0]["count"]) if rows else 0


def _aggregate(database: Database[dict[str, Any]], collection: str, pipeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return list(database[collection].aggregate(pipeline, allowDiskUse=True))


def _non_empty(values: list[Any]) -> list[Any]:
    return [value for value in values if value is not None and value != ""]


def _content_profile(rows: list[dict[str, Any]]) -> dict[str, list[Any]]:
    profile: dict[str, set[Any]] = {
        "content_ids": set(),
        "types": set(),
        "styles": set(),
        "categories": set(),
        "sentiments": set(),
        "venue_ids": set(),
        "hashtags": set(),
    }

    for row in rows:
        if row.get("content_id"):
            profile["content_ids"].add(row["content_id"])
        if row.get("type"):
            profile["types"].add(row["type"])
        if row.get("style"):
            profile["styles"].add(row["style"])
        if row.get("category"):
            profile["categories"].add(row["category"])
        if row.get("sentiment"):
            profile["sentiments"].add(row["sentiment"])
        if row.get("venue_id"):
            profile["venue_ids"].add(row["venue_id"])

        hashtags = row.get("hashtags") or []
        if isinstance(hashtags, list):
            profile["hashtags"].update(str(hashtag).lower() for hashtag in hashtags if str(hashtag).strip())

    return {key: list(values) for key, values in profile.items()}


def _liked_content_rows(database: Database[dict[str, Any]], filters: DashboardFilters, user_ids: list[Any]) -> list[dict[str, Any]]:
    if not user_ids:
        return []

    return _aggregate(
        database,
        "relationships",
        [
            {
                "$match": {
                    **_relationship_match(filters, "like"),
                    "source_user_id": {"$in": user_ids},
                    "target_type": "content",
                    "target_id": {"$exists": True, "$ne": None},
                }
            },
            {"$lookup": {"from": "content", "localField": "target_id", "foreignField": "_id", "as": "content"}},
            {"$unwind": "$content"},
            {
                "$project": {
                    "_id": 0,
                    "content_id": "$content._id",
                    "type": "$content.type",
                    "style": "$content.style",
                    "category": "$content.category",
                    "sentiment": "$content.sentiment.label",
                    "venue_id": "$content.venue_id",
                    "hashtags": "$content.hashtags",
                }
            },
        ],
    )


def _engaged_content_rows(database: Database[dict[str, Any]], filters: DashboardFilters, user_ids: list[Any]) -> list[dict[str, Any]]:
    if not user_ids:
        return []

    return _aggregate(
        database,
        "interactions",
        [
            *_interaction_pipeline_prefix(filters),
            {"$match": {"user_id": {"$in": user_ids}, "content_id": {"$exists": True, "$ne": None}}},
            {
                "$group": {
                    "_id": "$content_id",
                    "views": {"$sum": 1},
                    "avg_duration_ms": {"$avg": "$duration_ms"},
                    "last_engaged_at": {"$max": "$created_at"},
                }
            },
            {"$lookup": {"from": "content", "localField": "_id", "foreignField": "_id", "as": "content"}},
            {"$unwind": "$content"},
            {
                "$project": {
                    "_id": 0,
                    "content_id": "$content._id",
                    "type": "$content.type",
                    "style": "$content.style",
                    "category": "$content.category",
                    "sentiment": "$content.sentiment.label",
                    "venue_id": "$content.venue_id",
                    "hashtags": "$content.hashtags",
                    "views": 1,
                    "avg_duration_ms": 1,
                    "last_engaged_at": 1,
                }
            },
        ],
    )


def _user_seen_content_ids(database: Database[dict[str, Any]], filters: DashboardFilters, user_ids: list[Any]) -> list[Any]:
    seen_ids = {
        row["content_id"]
        for row in [
            *_liked_content_rows(database, filters, user_ids),
            *_engaged_content_rows(database, filters, user_ids),
        ]
        if row.get("content_id")
    }
    return list(seen_ids)


def _profile_candidate_recommendations(
    database: Database[dict[str, Any]],
    filters: DashboardFilters,
    profile: dict[str, list[Any]],
    exclude_content_ids: list[Any],
    venue_ids: list[Any] | None,
    limit: int,
    source_label: str,
) -> list[dict[str, Any]]:
    if not profile["content_ids"]:
        return []

    candidate_match: dict[str, Any] = {}
    if exclude_content_ids:
        candidate_match["_id"] = {"$nin": exclude_content_ids}
    selected_venue_ids = _non_empty(venue_ids or [])
    if selected_venue_ids:
        candidate_match["venue_id"] = {"$in": selected_venue_ids}

    pipeline = [*_content_pipeline_prefix(filters)]
    if candidate_match:
        pipeline.append({"$match": candidate_match})

    pipeline.extend(
        [
            {
                "$addFields": {
                    "matched_hashtags": {
                        "$setIntersection": [
                            {
                                "$map": {
                                    "input": {"$ifNull": ["$hashtags", []]},
                                    "as": "hashtag",
                                    "in": {"$toLower": {"$toString": "$$hashtag"}},
                                }
                            },
                            profile["hashtags"],
                        ]
                    }
                }
            },
            {
                "$addFields": {
                    "score": {
                        "$add": [
                            {"$cond": [{"$in": ["$type", profile["types"]]}, 3, 0]},
                            {"$cond": [{"$in": ["$style", profile["styles"]]}, 2, 0]},
                            {"$cond": [{"$in": ["$category", profile["categories"]]}, 2, 0]},
                            {"$cond": [{"$in": ["$sentiment.label", profile["sentiments"]]}, 1, 0]},
                            {"$cond": [{"$in": ["$venue_id", profile["venue_ids"]]}, 1, 0]},
                            {"$size": "$matched_hashtags"},
                        ]
                    }
                }
            },
            {"$match": {"score": {"$gt": 0}}},
            {"$lookup": {"from": "venues", "localField": "venue_id", "foreignField": "_id", "as": "venue"}},
            {"$unwind": {"path": "$venue", "preserveNullAndEmptyArrays": True}},
            {
                "$project": {
                    "_id": 0,
                    "content_id": "$_id",
                    "type": 1,
                    "style": 1,
                    "category": 1,
                    "sentiment": "$sentiment.label",
                    "venue_id": 1,
                    "venue_name": "$venue.name",
                    "city": "$venue.city",
                    "author_id": 1,
                    "created_at": 1,
                    "views": {"$ifNull": ["$metrics.view_count", 0]},
                    "likes": {"$ifNull": ["$metrics.like_count", 0]},
                    "comments": {"$ifNull": ["$metrics.comment_count", 0]},
                    "score": 1,
                    "matched_hashtags": 1,
                    "recommendation_source": {"$literal": source_label},
                    "text": {"$substrCP": [{"$ifNull": ["$text", ""]}, 0, 180]},
                }
            },
            {"$sort": {"score": -1, "likes": -1, "views": -1, "created_at": -1}},
            {"$limit": limit},
        ]
    )

    return _aggregate(database, "content", pipeline)


def hydrate_content_candidates(
    database: Database[dict[str, Any]],
    filters: DashboardFilters,
    graph_rows: list[dict[str, Any]],
    venue_ids: list[Any] | None = None,
    limit: int = 15,
) -> list[dict[str, Any]]:
    if not graph_rows:
        return []

    graph_by_content_id: dict[Any, dict[str, Any]] = {}
    ordered_content_ids: list[Any] = []
    for row in graph_rows:
        content_id = row.get("content_id")
        if not content_id or content_id in graph_by_content_id:
            continue
        graph_by_content_id[content_id] = row
        ordered_content_ids.append(content_id)

    if not ordered_content_ids:
        return []

    candidate_match: dict[str, Any] = {"_id": {"$in": ordered_content_ids}}
    selected_venue_ids = _non_empty(venue_ids or [])
    if selected_venue_ids:
        candidate_match["venue_id"] = {"$in": selected_venue_ids}

    rows = _aggregate(
        database,
        "content",
        [
            *_content_pipeline_prefix(filters),
            {"$match": candidate_match},
            {"$lookup": {"from": "venues", "localField": "venue_id", "foreignField": "_id", "as": "venue"}},
            {"$unwind": {"path": "$venue", "preserveNullAndEmptyArrays": True}},
            {
                "$project": {
                    "_id": 0,
                    "content_id": "$_id",
                    "type": 1,
                    "style": 1,
                    "category": 1,
                    "sentiment": "$sentiment.label",
                    "venue_id": 1,
                    "venue_name": "$venue.name",
                    "city": "$venue.city",
                    "author_id": 1,
                    "created_at": 1,
                    "views": {"$ifNull": ["$metrics.view_count", 0]},
                    "likes": {"$ifNull": ["$metrics.like_count", 0]},
                    "comments": {"$ifNull": ["$metrics.comment_count", 0]},
                    "text": {"$substrCP": [{"$ifNull": ["$text", ""]}, 0, 180]},
                }
            },
        ],
    )

    order = {content_id: index for index, content_id in enumerate(ordered_content_ids)}
    hydrated_rows: list[dict[str, Any]] = []
    for row in rows:
        graph_row = graph_by_content_id.get(row.get("content_id"), {})
        row.update(
            {
                key: value
                for key, value in graph_row.items()
                if key in {
                    "score",
                    "based_on_count",
                    "based_on_content_ids",
                    "author_username",
                    "recommendation_source",
                    "similar_user_count",
                }
            }
        )
        hydrated_rows.append(row)

    hydrated_rows.sort(key=lambda row: order.get(row.get("content_id"), len(order)))
    return hydrated_rows[:limit]


def get_date_bounds(database: Database[dict[str, Any]]) -> tuple[datetime | None, datetime | None]:
    min_date: datetime | None = None
    max_date: datetime | None = None

    for collection in ("users", "content", "interactions", "relationships"):
        rows = _aggregate(
            database,
            collection,
            [
                {"$match": {"created_at": {"$type": "date"}}},
                {"$group": {"_id": None, "min_date": {"$min": "$created_at"}, "max_date": {"$max": "$created_at"}}},
            ],
        )
        if not rows:
            continue

        row = rows[0]
        row_min = row.get("min_date")
        row_max = row.get("max_date")
        if row_min is not None and (min_date is None or row_min < min_date):
            min_date = row_min
        if row_max is not None and (max_date is None or row_max > max_date):
            max_date = row_max

    return min_date, max_date


def get_filter_options(database: Database[dict[str, Any]]) -> dict[str, list[FilterOption]]:
    return {
        "cities": _city_filter_options(database),
        "content_types": _content_attribute_filter_options(database, "type"),
        "styles": _content_attribute_filter_options(database, "style"),
        "categories": _content_attribute_filter_options(database, "category"),
        "sentiments": _content_attribute_filter_options(database, "sentiment.label"),
        "interaction_sources": _interaction_source_filter_options(database),
    }


def get_overview_metrics(database: Database[dict[str, Any]], filters: DashboardFilters) -> dict[str, Any]:
    avg_duration_rows = _aggregate(
        database,
        "interactions",
        [
            *_interaction_pipeline_prefix(filters),
            {"$match": {"duration_ms": {"$type": "number"}}},
            {"$group": {"_id": None, "avg_duration_ms": {"$avg": "$duration_ms"}}},
        ],
    )
    avg_rating_rows = _aggregate(
        database,
        "venues",
        [
            {"$match": {**_venue_match(filters), "rating.aggregate_rating": {"$type": "number"}}},
            {"$group": {"_id": None, "avg_rating": {"$avg": "$rating.aggregate_rating"}}},
        ],
    )
    active_day_rows = _aggregate(
        database,
        "interactions",
        [
            *_interaction_pipeline_prefix(filters),
            {"$group": {"_id": {"$dateTrunc": {"date": "$created_at", "unit": "day"}}, "views": {"$sum": 1}}},
            {"$sort": {"views": -1}},
            {"$limit": 1},
        ],
    )

    return {
        "users": database.users.count_documents(_user_match(filters)),
        "venues": database.venues.count_documents(_venue_match(filters)),
        "content": _count_pipeline(database, "content", _content_pipeline_prefix(filters)),
        "views": _count_pipeline(database, "interactions", _interaction_pipeline_prefix(filters)),
        "likes": database.relationships.count_documents(_relationship_match(filters, "like")),
        "follows": database.relationships.count_documents(_relationship_match(filters, "follow")),
        "avg_duration_ms": avg_duration_rows[0].get("avg_duration_ms") if avg_duration_rows else None,
        "avg_rating": avg_rating_rows[0].get("avg_rating") if avg_rating_rows else None,
        "most_active_day": active_day_rows[0].get("_id") if active_day_rows else None,
        "most_active_day_views": active_day_rows[0].get("views") if active_day_rows else 0,
    }


def content_by_type(database: Database[dict[str, Any]], filters: DashboardFilters) -> list[dict[str, Any]]:
    return _aggregate(
        database,
        "content",
        [
            *_content_pipeline_prefix(filters),
            {"$group": {"_id": "$type", "count": {"$sum": 1}}},
            {"$project": {"_id": 0, "type": "$_id", "count": 1}},
            {"$sort": {"count": -1}},
        ],
    )


def content_by_style(database: Database[dict[str, Any]], filters: DashboardFilters) -> list[dict[str, Any]]:
    return _aggregate(
        database,
        "content",
        [
            *_content_pipeline_prefix(filters),
            {"$group": {"_id": {"$ifNull": ["$style", "unspecified"]}, "count": {"$sum": 1}}},
            {"$project": {"_id": 0, "style": "$_id", "count": 1}},
            {"$sort": {"count": -1}},
        ],
    )


def content_over_time(database: Database[dict[str, Any]], filters: DashboardFilters) -> list[dict[str, Any]]:
    return _aggregate(
        database,
        "content",
        [
            *_content_pipeline_prefix(filters),
            {
                "$group": {
                    "_id": {"date": {"$dateTrunc": {"date": "$created_at", "unit": "day"}}, "type": "$type"},
                    "count": {"$sum": 1},
                }
            },
            {"$project": {"_id": 0, "date": "$_id.date", "type": "$_id.type", "count": 1}},
            {"$sort": {"date": 1, "type": 1}},
        ],
    )


def sentiment_over_time(database: Database[dict[str, Any]], filters: DashboardFilters) -> list[dict[str, Any]]:
    return _aggregate(
        database,
        "content",
        [
            *_content_pipeline_prefix(filters),
            {"$match": {"sentiment.label": {"$exists": True}}},
            {
                "$group": {
                    "_id": {"date": {"$dateTrunc": {"date": "$created_at", "unit": "day"}}, "sentiment": "$sentiment.label"},
                    "count": {"$sum": 1},
                }
            },
            {"$project": {"_id": 0, "date": "$_id.date", "sentiment": "$_id.sentiment", "count": 1}},
            {"$sort": {"date": 1, "sentiment": 1}},
        ],
    )


def sentiment_distribution(database: Database[dict[str, Any]], filters: DashboardFilters) -> list[dict[str, Any]]:
    return _aggregate(
        database,
        "content",
        [
            *_content_pipeline_prefix(filters),
            {"$match": {"sentiment.label": {"$exists": True}}},
            {"$group": {"_id": "$sentiment.label", "count": {"$sum": 1}}},
            {"$project": {"_id": 0, "sentiment": "$_id", "count": 1}},
            {"$sort": {"count": -1}},
        ],
    )


def top_hashtags(database: Database[dict[str, Any]], filters: DashboardFilters, limit: int = 20) -> list[dict[str, Any]]:
    return _aggregate(
        database,
        "content",
        [
            *_content_pipeline_prefix(filters),
            {"$unwind": "$hashtags"},
            {"$group": {"_id": {"$toLower": "$hashtags"}, "count": {"$sum": 1}}},
            {"$project": {"_id": 0, "hashtag": "$_id", "count": 1}},
            {"$sort": {"count": -1}},
            {"$limit": limit},
        ],
    )


def top_content(database: Database[dict[str, Any]], filters: DashboardFilters, limit: int = 20) -> list[dict[str, Any]]:
    return _aggregate(
        database,
        "content",
        [
            *_content_pipeline_prefix(filters),
            {
                "$project": {
                    "_id": 0,
                    "content_id": "$_id",
                    "type": 1,
                    "style": 1,
                    "category": 1,
                    "sentiment": "$sentiment.label",
                    "views": {"$ifNull": ["$metrics.view_count", 0]},
                    "likes": {"$ifNull": ["$metrics.like_count", 0]},
                    "comments": {"$ifNull": ["$metrics.comment_count", 0]},
                    "text": {"$substrCP": [{"$ifNull": ["$text", ""]}, 0, 140]},
                }
            },
            {"$sort": {"views": -1, "likes": -1, "comments": -1}},
            {"$limit": limit},
        ],
    )


def virality_baseline(
    database: Database[dict[str, Any]],
    filters: DashboardFilters,
    content_types: tuple[str, ...] | None = None,
    multiplier: float = 3.0,
) -> list[dict[str, Any]]:
    selected_types = _virality_content_types(filters, content_types)
    if not selected_types:
        return []

    return _aggregate(
        database,
        "interactions",
        [
            *_interaction_pipeline_prefix(filters),
            {"$match": {"content_id": {"$exists": True, "$ne": None}}},
            {
                "$group": {
                    "_id": "$content_id",
                    "interaction_count": {"$sum": 1},
                    "unique_viewers": {"$addToSet": "$user_id"},
                    "last_interaction_at": {"$max": "$created_at"},
                }
            },
            {"$lookup": {"from": "content", "localField": "_id", "foreignField": "_id", "as": "content"}},
            {"$unwind": "$content"},
            {"$match": {"content.type": {"$in": list(selected_types)}}},
            {
                "$addFields": {
                    "unique_viewer_count": {
                        "$size": {"$setDifference": ["$unique_viewers", [None]]}
                    }
                }
            },
            {
                "$group": {
                    "_id": "$content.type",
                    "content_count": {"$sum": 1},
                    "total_interactions": {"$sum": "$interaction_count"},
                    "avg_interactions": {"$avg": "$interaction_count"},
                    "max_interactions": {"$max": "$interaction_count"},
                    "avg_unique_viewers": {"$avg": "$unique_viewer_count"},
                    "last_interaction_at": {"$max": "$last_interaction_at"},
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "type": "$_id",
                    "content_count": 1,
                    "total_interactions": 1,
                    "avg_interactions": 1,
                    "viral_threshold": {"$multiply": ["$avg_interactions", multiplier]},
                    "max_interactions": 1,
                    "avg_unique_viewers": 1,
                    "last_interaction_at": 1,
                }
            },
            {"$sort": {"type": 1}},
        ],
    )


def viral_content(
    database: Database[dict[str, Any]],
    filters: DashboardFilters,
    content_types: tuple[str, ...] | None = None,
    multiplier: float = 3.0,
    minimum_interactions: int = 20,
    limit: int = 25,
) -> list[dict[str, Any]]:
    selected_types = _virality_content_types(filters, content_types)
    if not selected_types:
        return []

    return _aggregate(
        database,
        "interactions",
        [
            *_interaction_pipeline_prefix(filters),
            {"$match": {"content_id": {"$exists": True, "$ne": None}}},
            {
                "$group": {
                    "_id": "$content_id",
                    "interaction_count": {"$sum": 1},
                    "unique_viewers": {"$addToSet": "$user_id"},
                    "avg_duration_ms": {"$avg": "$duration_ms"},
                    "last_interaction_at": {"$max": "$created_at"},
                    "first_interaction_at": {"$min": "$created_at"},
                }
            },
            {"$lookup": {"from": "content", "localField": "_id", "foreignField": "_id", "as": "content"}},
            {"$unwind": "$content"},
            {"$match": {"content.type": {"$in": list(selected_types)}}},
            {
                "$setWindowFields": {
                    "partitionBy": "$content.type",
                    "output": {
                        "avg_interactions_for_type": {"$avg": "$interaction_count"},
                    },
                }
            },
            {
                "$addFields": {
                    "viral_threshold": {"$multiply": ["$avg_interactions_for_type", multiplier]},
                    "virality_ratio": {
                        "$cond": [
                            {"$gt": ["$avg_interactions_for_type", 0]},
                            {"$divide": ["$interaction_count", "$avg_interactions_for_type"]},
                            0,
                        ]
                    },
                    "unique_viewer_count": {
                        "$size": {"$setDifference": ["$unique_viewers", [None]]}
                    },
                }
            },
            {
                "$match": {
                    "interaction_count": {"$gte": minimum_interactions},
                    "$expr": {"$gte": ["$interaction_count", "$viral_threshold"]},
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "content_id": "$_id",
                    "type": "$content.type",
                    "style": "$content.style",
                    "category": "$content.category",
                    "sentiment": "$content.sentiment.label",
                    "author_id": "$content.author_id",
                    "venue_id": "$content.venue_id",
                    "interaction_count": 1,
                    "unique_viewer_count": 1,
                    "avg_duration_ms": 1,
                    "avg_interactions_for_type": 1,
                    "viral_threshold": 1,
                    "virality_ratio": 1,
                    "created_at": "$content.created_at",
                    "first_interaction_at": 1,
                    "last_interaction_at": 1,
                    "text": {"$substrCP": [{"$ifNull": ["$content.text", ""]}, 0, 180]},
                }
            },
            {"$sort": {"virality_ratio": -1, "interaction_count": -1, "last_interaction_at": -1}},
            {"$limit": limit},
        ],
    )


def viral_interactions_over_time(
    database: Database[dict[str, Any]],
    filters: DashboardFilters,
    content_ids: tuple[Any, ...],
) -> list[dict[str, Any]]:
    if not content_ids:
        return []

    return _aggregate(
        database,
        "interactions",
        [
            *_interaction_pipeline_prefix(filters),
            {"$match": {"content_id": {"$in": list(content_ids)}}},
            {
                "$group": {
                    "_id": {
                        "date": {"$dateTrunc": {"date": "$created_at", "unit": "day"}},
                        "content_id": "$content_id",
                    },
                    "interactions": {"$sum": 1},
                    "unique_viewers": {"$addToSet": "$user_id"},
                }
            },
            {"$lookup": {"from": "content", "localField": "_id.content_id", "foreignField": "_id", "as": "content"}},
            {"$unwind": {"path": "$content", "preserveNullAndEmptyArrays": True}},
            {
                "$project": {
                    "_id": 0,
                    "date": "$_id.date",
                    "content_id": "$_id.content_id",
                    "type": "$content.type",
                    "interactions": 1,
                    "unique_viewer_count": {
                        "$size": {"$setDifference": ["$unique_viewers", [None]]}
                    },
                }
            },
            {"$sort": {"date": 1, "interactions": -1}},
        ],
    )


def views_over_time(database: Database[dict[str, Any]], filters: DashboardFilters) -> list[dict[str, Any]]:
    return _aggregate(
        database,
        "interactions",
        [
            *_interaction_pipeline_prefix(filters),
            {
                "$group": {
                    "_id": {"date": {"$dateTrunc": {"date": "$created_at", "unit": "day"}}, "source": "$source"},
                    "views": {"$sum": 1},
                }
            },
            {"$project": {"_id": 0, "date": "$_id.date", "source": "$_id.source", "views": 1}},
            {"$sort": {"date": 1, "source": 1}},
        ],
    )


def views_by_source(database: Database[dict[str, Any]], filters: DashboardFilters) -> list[dict[str, Any]]:
    return _aggregate(
        database,
        "interactions",
        [
            *_interaction_pipeline_prefix(filters),
            {"$group": {"_id": {"$ifNull": ["$source", "unknown"]}, "views": {"$sum": 1}}},
            {"$project": {"_id": 0, "source": "$_id", "views": 1}},
            {"$sort": {"views": -1}},
        ],
    )


def duration_by_source(database: Database[dict[str, Any]], filters: DashboardFilters) -> list[dict[str, Any]]:
    return _aggregate(
        database,
        "interactions",
        [
            *_interaction_pipeline_prefix(filters),
            {"$match": {"duration_ms": {"$type": "number"}}},
            {"$group": {"_id": {"$ifNull": ["$source", "unknown"]}, "avg_duration_ms": {"$avg": "$duration_ms"}, "views": {"$sum": 1}}},
            {"$project": {"_id": 0, "source": "$_id", "avg_duration_ms": 1, "views": 1}},
            {"$sort": {"avg_duration_ms": -1}},
        ],
    )


def top_viewed_content(database: Database[dict[str, Any]], filters: DashboardFilters, limit: int = 20) -> list[dict[str, Any]]:
    return _aggregate(
        database,
        "interactions",
        [
            *_interaction_pipeline_prefix(filters),
            {"$group": {"_id": "$content_id", "views": {"$sum": 1}, "avg_duration_ms": {"$avg": "$duration_ms"}}},
            {"$sort": {"views": -1}},
            {"$limit": limit},
            {"$lookup": {"from": "content", "localField": "_id", "foreignField": "_id", "as": "content"}},
            {"$unwind": {"path": "$content", "preserveNullAndEmptyArrays": True}},
            {
                "$project": {
                    "_id": 0,
                    "content_id": "$_id",
                    "views": 1,
                    "avg_duration_ms": 1,
                    "type": "$content.type",
                    "sentiment": "$content.sentiment.label",
                    "text": {"$substrCP": [{"$ifNull": ["$content.text", ""]}, 0, 140]},
                }
            },
        ],
    )


def most_active_users(database: Database[dict[str, Any]], filters: DashboardFilters, limit: int = 20) -> list[dict[str, Any]]:
    return _aggregate(
        database,
        "interactions",
        [
            *_interaction_pipeline_prefix(filters),
            {"$match": {"user_id": {"$exists": True, "$ne": None}}},
            {"$group": {"_id": "$user_id", "views": {"$sum": 1}, "avg_duration_ms": {"$avg": "$duration_ms"}}},
            {"$sort": {"views": -1}},
            {"$limit": limit},
            {"$lookup": {"from": "users", "localField": "_id", "foreignField": "_id", "as": "user"}},
            {"$unwind": {"path": "$user", "preserveNullAndEmptyArrays": True}},
            {
                "$project": {
                    "_id": 0,
                    "user_id": "$_id",
                    "username": "$user.username",
                    "city": "$user.city",
                    "views": 1,
                    "avg_duration_ms": 1,
                }
            },
        ],
    )


def most_engaged_users(database: Database[dict[str, Any]], filters: DashboardFilters, limit: int = 100) -> list[dict[str, Any]]:
    return _aggregate(
        database,
        "interactions",
        [
            *_interaction_pipeline_prefix(filters),
            {
                "$match": {
                    "user_id": {"$exists": True, "$ne": None},
                    "content_id": {"$exists": True, "$ne": None},
                }
            },
            {
                "$group": {
                    "_id": "$user_id",
                    "views": {"$sum": 1},
                    "content_ids": {"$addToSet": "$content_id"},
                    "avg_duration_ms": {"$avg": "$duration_ms"},
                    "last_seen_at": {"$max": "$created_at"},
                }
            },
            {"$addFields": {"engaged_content_count": {"$size": "$content_ids"}}},
            {"$sort": {"engaged_content_count": -1, "views": -1, "last_seen_at": -1}},
            {"$limit": limit},
            {"$lookup": {"from": "users", "localField": "_id", "foreignField": "_id", "as": "user"}},
            {"$unwind": {"path": "$user", "preserveNullAndEmptyArrays": True}},
            {
                "$project": {
                    "_id": 0,
                    "user_id": "$_id",
                    "username": "$user.username",
                    "display_name": "$user.display_name",
                    "city": "$user.city",
                    "engaged_content_count": 1,
                    "views": 1,
                    "avg_duration_ms": 1,
                    "last_seen_at": 1,
                }
            },
        ],
    )


def most_engaged_venues(database: Database[dict[str, Any]], filters: DashboardFilters, limit: int = 100) -> list[dict[str, Any]]:
    return _aggregate(
        database,
        "interactions",
        [
            *_interaction_pipeline_prefix(filters),
            {"$match": {"content_id": {"$exists": True, "$ne": None}}},
            {"$lookup": {"from": "content", "localField": "content_id", "foreignField": "_id", "as": "feed_content"}},
            {"$unwind": "$feed_content"},
            {"$match": {"feed_content.venue_id": {"$exists": True, "$ne": None}}},
            {"$lookup": {"from": "venues", "localField": "feed_content.venue_id", "foreignField": "_id", "as": "feed_venue"}},
            {"$unwind": {"path": "$feed_venue", "preserveNullAndEmptyArrays": True}},
            {
                "$group": {
                    "_id": "$feed_content.venue_id",
                    "name": {"$first": "$feed_venue.name"},
                    "city": {"$first": "$feed_venue.city"},
                    "category": {"$first": "$feed_venue.category"},
                    "rating": {"$first": "$feed_venue.rating.aggregate_rating"},
                    "views": {"$sum": 1},
                    "content_ids": {"$addToSet": "$content_id"},
                    "viewer_ids": {"$addToSet": "$user_id"},
                    "avg_duration_ms": {"$avg": "$duration_ms"},
                    "last_seen_at": {"$max": "$created_at"},
                }
            },
            {
                "$addFields": {
                    "engaged_content_count": {"$size": "$content_ids"},
                    "viewer_count": {"$size": {"$setDifference": ["$viewer_ids", [None]]}},
                }
            },
            {"$sort": {"engaged_content_count": -1, "views": -1, "viewer_count": -1, "last_seen_at": -1}},
            {"$limit": limit},
            {
                "$project": {
                    "_id": 0,
                    "venue_id": "$_id",
                    "name": 1,
                    "city": 1,
                    "category": 1,
                    "rating": 1,
                    "engaged_content_count": 1,
                    "viewer_count": 1,
                    "views": 1,
                    "avg_duration_ms": 1,
                    "last_seen_at": 1,
                }
            },
        ],
    )


def recommendations_from_liked_content(
    database: Database[dict[str, Any]],
    filters: DashboardFilters,
    user_ids: list[Any],
    venue_ids: list[Any] | None = None,
    limit: int = 15,
) -> list[dict[str, Any]]:
    liked_rows = _liked_content_rows(database, filters, user_ids)
    profile = _content_profile(liked_rows)
    exclude_content_ids = _user_seen_content_ids(database, filters, user_ids)
    return _profile_candidate_recommendations(
        database,
        filters,
        profile,
        exclude_content_ids,
        venue_ids,
        limit,
        "Similar to liked content",
    )


def recommendations_from_engaged_content(
    database: Database[dict[str, Any]],
    filters: DashboardFilters,
    user_ids: list[Any],
    venue_ids: list[Any] | None = None,
    limit: int = 15,
) -> list[dict[str, Any]]:
    engaged_rows = _engaged_content_rows(database, filters, user_ids)
    profile = _content_profile(engaged_rows)
    exclude_content_ids = _user_seen_content_ids(database, filters, user_ids)
    return _profile_candidate_recommendations(
        database,
        filters,
        profile,
        exclude_content_ids,
        venue_ids,
        limit,
        "Similar to engaged content",
    )


def recommendations_from_similar_user_likes(
    database: Database[dict[str, Any]],
    filters: DashboardFilters,
    user_ids: list[Any],
    venue_ids: list[Any] | None = None,
    limit: int = 15,
) -> list[dict[str, Any]]:
    liked_rows = _liked_content_rows(database, filters, user_ids)
    liked_content_ids = [row["content_id"] for row in liked_rows if row.get("content_id")]
    if not liked_content_ids:
        return []

    exclude_content_ids = _user_seen_content_ids(database, filters, user_ids)
    target_id_condition: dict[str, Any] = {"$exists": True, "$ne": None}
    if exclude_content_ids:
        target_id_condition["$nin"] = exclude_content_ids

    candidate_like_match: dict[str, Any] = {
        "candidate_likes.type": "like",
        "candidate_likes.target_type": "content",
        "candidate_likes.target_id": target_id_condition,
        "candidate_likes.created_at": _date_condition(filters),
    }
    content_match = {
        **_date_match("content.created_at", filters),
        **_content_attribute_match(filters, "content."),
    }
    selected_venue_ids = _non_empty(venue_ids or [])
    if selected_venue_ids:
        content_match["content.venue_id"] = {"$in": selected_venue_ids}

    pipeline: list[dict[str, Any]] = [
        {
            "$match": {
                **_relationship_match(filters, "like"),
                "source_user_id": {"$nin": user_ids},
                "target_type": "content",
                "target_id": {"$in": liked_content_ids},
            }
        },
        {
            "$group": {
                "_id": "$source_user_id",
                "shared_like_count": {"$sum": 1},
                "shared_content_ids": {"$addToSet": "$target_id"},
            }
        },
        {"$sort": {"shared_like_count": -1}},
        {"$limit": 250},
        {"$lookup": {"from": "relationships", "localField": "_id", "foreignField": "source_user_id", "as": "candidate_likes"}},
        {"$unwind": "$candidate_likes"},
        {"$match": candidate_like_match},
        {
            "$group": {
                "_id": "$candidate_likes.target_id",
                "score": {"$sum": "$shared_like_count"},
                "similar_user_ids": {"$addToSet": "$_id"},
                "shared_content_ids": {"$addToSet": "$shared_content_ids"},
            }
        },
        {"$addFields": {"similar_user_count": {"$size": "$similar_user_ids"}}},
        {"$lookup": {"from": "content", "localField": "_id", "foreignField": "_id", "as": "content"}},
        {"$unwind": "$content"},
        {"$match": content_match},
        {"$lookup": {"from": "venues", "localField": "content.venue_id", "foreignField": "_id", "as": "venue"}},
        {"$unwind": {"path": "$venue", "preserveNullAndEmptyArrays": True}},
    ]

    if filters.city:
        pipeline.append({"$match": {"venue.city": filters.city}})

    pipeline.extend(
        [
            {
                "$project": {
                    "_id": 0,
                    "content_id": "$content._id",
                    "type": "$content.type",
                    "style": "$content.style",
                    "category": "$content.category",
                    "sentiment": "$content.sentiment.label",
                    "venue_id": "$content.venue_id",
                    "venue_name": "$venue.name",
                    "city": "$venue.city",
                    "author_id": "$content.author_id",
                    "created_at": "$content.created_at",
                    "views": {"$ifNull": ["$content.metrics.view_count", 0]},
                    "likes": {"$ifNull": ["$content.metrics.like_count", 0]},
                    "comments": {"$ifNull": ["$content.metrics.comment_count", 0]},
                    "score": 1,
                    "similar_user_count": 1,
                    "recommendation_source": {"$literal": "Liked by similar users"},
                    "text": {"$substrCP": [{"$ifNull": ["$content.text", ""]}, 0, 180]},
                }
            },
            {"$sort": {"score": -1, "similar_user_count": -1, "likes": -1, "views": -1, "created_at": -1}},
            {"$limit": limit},
        ]
    )

    return _aggregate(database, "relationships", pipeline)


def users_by_city(database: Database[dict[str, Any]], filters: DashboardFilters, limit: int = 20) -> list[dict[str, Any]]:
    return _aggregate(
        database,
        "users",
        [
            {"$match": _user_match(filters)},
            {"$group": {"_id": {"$ifNull": ["$city", "unknown"]}, "users": {"$sum": 1}}},
            {"$project": {"_id": 0, "city": "$_id", "users": 1}},
            {"$sort": {"users": -1}},
            {"$limit": limit},
        ],
    )


def venues_by_city(database: Database[dict[str, Any]], filters: DashboardFilters, limit: int = 20) -> list[dict[str, Any]]:
    return _aggregate(
        database,
        "venues",
        [
            {"$match": _venue_match(filters)},
            {"$group": {"_id": {"$ifNull": ["$city", "unknown"]}, "venues": {"$sum": 1}, "avg_rating": {"$avg": "$rating.aggregate_rating"}}},
            {"$project": {"_id": 0, "city": "$_id", "venues": 1, "avg_rating": 1}},
            {"$sort": {"venues": -1}},
            {"$limit": limit},
        ],
    )


def top_cuisines(database: Database[dict[str, Any]], filters: DashboardFilters, limit: int = 20) -> list[dict[str, Any]]:
    return _aggregate(
        database,
        "venues",
        [
            {"$match": _venue_match(filters)},
            {"$unwind": "$cuisines"},
            {"$group": {"_id": "$cuisines", "venues": {"$sum": 1}, "avg_rating": {"$avg": "$rating.aggregate_rating"}}},
            {"$project": {"_id": 0, "cuisine": "$_id", "venues": 1, "avg_rating": 1}},
            {"$sort": {"venues": -1}},
            {"$limit": limit},
        ],
    )


def venue_rating_by_city(database: Database[dict[str, Any]], filters: DashboardFilters, limit: int = 20) -> list[dict[str, Any]]:
    return _aggregate(
        database,
        "venues",
        [
            {"$match": {**_venue_match(filters), "rating.aggregate_rating": {"$type": "number"}}},
            {"$group": {"_id": "$city", "avg_rating": {"$avg": "$rating.aggregate_rating"}, "venues": {"$sum": 1}}},
            {"$project": {"_id": 0, "city": "$_id", "avg_rating": 1, "venues": 1}},
            {"$sort": {"avg_rating": -1, "venues": -1}},
            {"$limit": limit},
        ],
    )


def venue_price_rating_points(database: Database[dict[str, Any]], filters: DashboardFilters, limit: int = 500) -> list[dict[str, Any]]:
    return _aggregate(
        database,
        "venues",
        [
            {
                "$match": {
                    **_venue_match(filters),
                    "rating.aggregate_rating": {"$type": "number"},
                    "pricing.average_cost_for_two": {"$type": "number"},
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "venue_id": "$_id",
                    "name": 1,
                    "city": 1,
                    "category": 1,
                    "average_cost_for_two": "$pricing.average_cost_for_two",
                    "price_range": "$pricing.price_range",
                    "rating": "$rating.aggregate_rating",
                    "votes": "$rating.votes",
                }
            },
            {"$sort": {"votes": -1, "rating": -1}},
            {"$limit": limit},
        ],
    )


def venue_map_points(database: Database[dict[str, Any]], filters: DashboardFilters, limit: int = 500) -> list[dict[str, Any]]:
    return _aggregate(
        database,
        "venues",
        [
            {
                "$match": {
                    **_venue_match(filters),
                    "location.coordinates.0": {"$type": "number"},
                    "location.coordinates.1": {"$type": "number"},
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "venue_id": "$_id",
                    "name": 1,
                    "city": 1,
                    "category": 1,
                    "rating": "$rating.aggregate_rating",
                    "votes": "$rating.votes",
                    "longitude": {"$arrayElemAt": ["$location.coordinates", 0]},
                    "latitude": {"$arrayElemAt": ["$location.coordinates", 1]},
                }
            },
            {"$sort": {"votes": -1}},
            {"$limit": limit},
        ],
    )
