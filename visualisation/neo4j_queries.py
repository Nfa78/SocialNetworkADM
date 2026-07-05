from __future__ import annotations

from typing import Any

from neo4j import Driver

from mongo_queries import DashboardFilters


def _params(filters: DashboardFilters, limit: int) -> dict[str, Any]:
    return {
        "start_iso": filters.start.isoformat() if filters.start else None,
        "end_iso": filters.end.isoformat() if filters.end else None,
        "city": filters.city,
        "content_type": filters.content_type,
        "style": filters.style,
        "category": filters.category,
        "sentiment": filters.sentiment,
        "limit": limit,
    }


def _run(driver: Driver, query: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    with driver.session() as session:
        return [record.data() for record in session.run(query, params)]


def top_followed_users(driver: Driver, filters: DashboardFilters, limit: int = 20) -> list[dict[str, Any]]:
    query = """
    MATCH (:User)-[rel:FOLLOWS]->(target:User)
    WHERE ($start_iso IS NULL OR rel.created_at >= $start_iso)
      AND ($end_iso IS NULL OR rel.created_at <= $end_iso)
    RETURN target.id AS user_id, count(rel) AS followers
    ORDER BY followers DESC
    LIMIT $limit
    """
    return _run(driver, query, _params(filters, limit))


def top_followed_venues(driver: Driver, filters: DashboardFilters, limit: int = 20) -> list[dict[str, Any]]:
    query = """
    MATCH (:User)-[rel:FOLLOWS]->(venue:Venue)
    WHERE ($start_iso IS NULL OR rel.created_at >= $start_iso)
      AND ($end_iso IS NULL OR rel.created_at <= $end_iso)
      AND ($city IS NULL OR venue.city = $city)
    RETURN venue.id AS venue_id,
           coalesce(venue.name, venue.id) AS name,
           venue.city AS city,
           venue.category AS category,
           count(rel) AS followers
    ORDER BY followers DESC
    LIMIT $limit
    """
    return _run(driver, query, _params(filters, limit))


def top_liked_content(driver: Driver, filters: DashboardFilters, limit: int = 20) -> list[dict[str, Any]]:
    query = """
    MATCH (:User)-[rel:LIKED]->(content:Content)
    OPTIONAL MATCH (venue:Venue)
    WHERE venue.id = content.venue_id
    WITH content, rel, venue
    WHERE ($start_iso IS NULL OR rel.created_at >= $start_iso)
      AND ($end_iso IS NULL OR rel.created_at <= $end_iso)
      AND ($city IS NULL OR venue.city = $city)
      AND ($content_type IS NULL OR content.type = $content_type)
      AND ($style IS NULL OR content.style = $style)
      AND ($category IS NULL OR content.category = $category)
      AND ($sentiment IS NULL OR content.sentiment_label = $sentiment)
    RETURN content.id AS content_id,
           content.type AS type,
           content.style AS style,
           content.category AS category,
           content.sentiment_label AS sentiment,
           venue.city AS city,
           count(rel) AS likes
    ORDER BY likes DESC
    LIMIT $limit
    """
    return _run(driver, query, _params(filters, limit))


def content_similarity(driver: Driver, filters: DashboardFilters, limit: int = 50) -> list[dict[str, Any]]:
    query = """
    MATCH (source:Content)-[rel:SIMILAR_TO]->(target:Content)
    OPTIONAL MATCH (venue:Venue)
    WHERE venue.id = source.venue_id
    WITH source, target, rel, venue
    WHERE ($start_iso IS NULL OR source.created_at >= $start_iso)
      AND ($end_iso IS NULL OR source.created_at <= $end_iso)
      AND ($city IS NULL OR venue.city = $city)
      AND ($content_type IS NULL OR source.type = $content_type)
      AND ($style IS NULL OR source.style = $style)
      AND ($category IS NULL OR source.category = $category)
      AND ($sentiment IS NULL OR source.sentiment_label = $sentiment)
    RETURN source.id AS source_content_id,
           target.id AS target_content_id,
           rel.score AS score,
           rel.reason AS reason,
           rel.shared_hashtags AS shared_hashtags
    ORDER BY score DESC
    LIMIT $limit
    """
    return _run(driver, query, _params(filters, limit))
