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
        "interaction_source": filters.interaction_source,
        "limit": limit,
    }


def _user_params(filters: DashboardFilters, user_ids: list[Any], limit: int) -> dict[str, Any]:
    return {
        **_params(filters, limit),
        "user_ids": user_ids,
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


def top_creators(driver: Driver, filters: DashboardFilters, limit: int = 20) -> list[dict[str, Any]]:
    query = """
    MATCH (creator:User)-[rel:CREATED]->(content:Content)
    OPTIONAL MATCH (venue:Venue)
    WHERE venue.id = content.venue_id
    WITH creator, content, rel, venue
    WHERE ($start_iso IS NULL OR rel.created_at >= $start_iso)
      AND ($end_iso IS NULL OR rel.created_at <= $end_iso)
      AND ($city IS NULL OR venue.city = $city)
      AND ($content_type IS NULL OR content.type = $content_type)
      AND ($style IS NULL OR content.style = $style)
      AND ($category IS NULL OR content.category = $category)
      AND ($sentiment IS NULL OR content.sentiment_label = $sentiment)
    RETURN creator.id AS user_id,
           creator.username AS username,
           creator.display_name AS display_name,
           creator.city AS user_city,
           count(content) AS created_content,
           max(rel.created_at) AS latest_created_at
    ORDER BY created_content DESC, latest_created_at DESC
    LIMIT $limit
    """
    return _run(driver, query, _params(filters, limit))


def top_viewed_content_graph(driver: Driver, filters: DashboardFilters, limit: int = 20) -> list[dict[str, Any]]:
    query = """
    MATCH (:User)-[viewed:VIEWED]->(content:Content)
    OPTIONAL MATCH (venue:Venue)
    WHERE venue.id = content.venue_id
    WITH content, viewed, venue
    WHERE ($start_iso IS NULL OR viewed.last_viewed_at >= $start_iso)
      AND ($end_iso IS NULL OR viewed.last_viewed_at <= $end_iso)
      AND ($interaction_source IS NULL OR viewed.last_source = $interaction_source)
      AND ($city IS NULL OR venue.city = $city)
      AND ($content_type IS NULL OR content.type = $content_type)
      AND ($style IS NULL OR content.style = $style)
      AND ($category IS NULL OR content.category = $category)
      AND ($sentiment IS NULL OR content.sentiment_label = $sentiment)
    WITH content,
         venue,
         sum(coalesce(viewed.count, 0)) AS views,
         count(DISTINCT viewed) AS unique_viewer_edges,
         sum(coalesce(viewed.total_duration_ms, 0)) AS total_duration_ms,
         max(viewed.last_viewed_at) AS last_viewed_at
    RETURN content.id AS content_id,
           content.type AS type,
           content.style AS style,
           content.category AS category,
           content.sentiment_label AS sentiment,
           venue.city AS city,
           views,
           unique_viewer_edges,
           CASE
               WHEN views > 0 THEN toFloat(total_duration_ms) / views
               ELSE null
           END AS avg_duration_ms,
           last_viewed_at
    ORDER BY views DESC, unique_viewer_edges DESC, last_viewed_at DESC
    LIMIT $limit
    """
    return _run(driver, query, _params(filters, limit))


def content_from_followed_authors(
    driver: Driver,
    filters: DashboardFilters,
    user_ids: list[Any],
    limit: int = 20,
) -> list[dict[str, Any]]:
    if not user_ids:
        return []

    query = """
    MATCH (viewer:User)-[:FOLLOWS]->(author:User)-[created:CREATED]->(content:Content)
    WHERE viewer.id IN $user_ids
      AND ($start_iso IS NULL OR created.created_at >= $start_iso)
      AND ($end_iso IS NULL OR created.created_at <= $end_iso)
      AND NOT EXISTS {
          MATCH (selected:User)-[:LIKED|VIEWED]->(content)
          WHERE selected.id IN $user_ids
      }
    OPTIONAL MATCH (venue:Venue)
    WHERE venue.id = content.venue_id
    WITH content, author, venue, count(DISTINCT viewer) AS follower_paths, max(created.created_at) AS latest_created_at
    WHERE ($city IS NULL OR venue.city = $city)
      AND ($content_type IS NULL OR content.type = $content_type)
      AND ($style IS NULL OR content.style = $style)
      AND ($category IS NULL OR content.category = $category)
      AND ($sentiment IS NULL OR content.sentiment_label = $sentiment)
    RETURN content.id AS content_id,
           content.type AS type,
           content.style AS style,
           content.category AS category,
           content.sentiment_label AS sentiment,
           content.venue_id AS venue_id,
           venue.name AS venue_name,
           venue.city AS city,
           author.id AS author_id,
           author.username AS author_username,
           latest_created_at AS created_at,
           follower_paths AS score,
           "Content from followed authors" AS recommendation_source
    ORDER BY score DESC, created_at DESC
    LIMIT $limit
    """
    return _run(driver, query, _user_params(filters, user_ids, limit))


def recommendations_from_liked_content_graph(
    driver: Driver,
    filters: DashboardFilters,
    user_ids: list[Any],
    limit: int = 20,
) -> list[dict[str, Any]]:
    if not user_ids:
        return []

    query = """
    MATCH (viewer:User)-[liked_rel:LIKED]->(liked:Content)-[sim:SIMILAR_TO]->(candidate:Content)
    WHERE viewer.id IN $user_ids
      AND ($start_iso IS NULL OR liked_rel.created_at >= $start_iso)
      AND ($end_iso IS NULL OR liked_rel.created_at <= $end_iso)
      AND NOT EXISTS {
          MATCH (selected:User)-[:LIKED|VIEWED]->(candidate)
          WHERE selected.id IN $user_ids
      }
    OPTIONAL MATCH (venue:Venue)
    WHERE venue.id = candidate.venue_id
    WITH candidate,
         venue,
         sum(coalesce(sim.score, 0.0)) AS score,
         count(DISTINCT liked) AS based_on_count,
         collect(DISTINCT liked.id)[0..5] AS based_on_content_ids
    WHERE ($city IS NULL OR venue.city = $city)
      AND ($start_iso IS NULL OR candidate.created_at >= $start_iso)
      AND ($end_iso IS NULL OR candidate.created_at <= $end_iso)
      AND ($content_type IS NULL OR candidate.type = $content_type)
      AND ($style IS NULL OR candidate.style = $style)
      AND ($category IS NULL OR candidate.category = $category)
      AND ($sentiment IS NULL OR candidate.sentiment_label = $sentiment)
    RETURN candidate.id AS content_id,
           candidate.type AS type,
           candidate.style AS style,
           candidate.category AS category,
           candidate.sentiment_label AS sentiment,
           candidate.venue_id AS venue_id,
           venue.name AS venue_name,
           venue.city AS city,
           candidate.author_id AS author_id,
           candidate.created_at AS created_at,
           score,
           based_on_count,
           based_on_content_ids,
           "Similar to liked content" AS recommendation_source
    ORDER BY score DESC, based_on_count DESC, created_at DESC
    LIMIT $limit
    """
    return _run(driver, query, _user_params(filters, user_ids, limit))


def recommendations_from_similar_user_likes_graph(
    driver: Driver,
    filters: DashboardFilters,
    user_ids: list[Any],
    limit: int = 20,
) -> list[dict[str, Any]]:
    if not user_ids:
        return []

    query = """
    MATCH (selected:User)-[selected_like:LIKED]->(common:Content)<-[other_like:LIKED]-(other:User)
    WHERE selected.id IN $user_ids
      AND NOT (other.id IN $user_ids)
      AND ($start_iso IS NULL OR selected_like.created_at >= $start_iso)
      AND ($end_iso IS NULL OR selected_like.created_at <= $end_iso)
      AND ($start_iso IS NULL OR other_like.created_at >= $start_iso)
      AND ($end_iso IS NULL OR other_like.created_at <= $end_iso)
    WITH other, count(DISTINCT common) AS overlap_count
    ORDER BY overlap_count DESC
    LIMIT 250
    MATCH (other)-[candidate_like:LIKED]->(candidate:Content)
    WHERE ($start_iso IS NULL OR candidate_like.created_at >= $start_iso)
      AND ($end_iso IS NULL OR candidate_like.created_at <= $end_iso)
      AND NOT EXISTS {
          MATCH (selected:User)-[:LIKED|VIEWED]->(candidate)
          WHERE selected.id IN $user_ids
      }
    OPTIONAL MATCH (venue:Venue)
    WHERE venue.id = candidate.venue_id
    WITH candidate,
         venue,
         sum(overlap_count) AS score,
         count(DISTINCT other) AS similar_user_count
    WHERE ($city IS NULL OR venue.city = $city)
      AND ($start_iso IS NULL OR candidate.created_at >= $start_iso)
      AND ($end_iso IS NULL OR candidate.created_at <= $end_iso)
      AND ($content_type IS NULL OR candidate.type = $content_type)
      AND ($style IS NULL OR candidate.style = $style)
      AND ($category IS NULL OR candidate.category = $category)
      AND ($sentiment IS NULL OR candidate.sentiment_label = $sentiment)
    RETURN candidate.id AS content_id,
           candidate.type AS type,
           candidate.style AS style,
           candidate.category AS category,
           candidate.sentiment_label AS sentiment,
           candidate.venue_id AS venue_id,
           venue.name AS venue_name,
           venue.city AS city,
           candidate.author_id AS author_id,
           candidate.created_at AS created_at,
           score,
           similar_user_count,
           "Liked by similar users" AS recommendation_source
    ORDER BY score DESC, similar_user_count DESC, created_at DESC
    LIMIT $limit
    """
    return _run(driver, query, _user_params(filters, user_ids, limit))


def recommendations_from_viewed_content_graph(
    driver: Driver,
    filters: DashboardFilters,
    user_ids: list[Any],
    limit: int = 20,
) -> list[dict[str, Any]]:
    if not user_ids:
        return []

    query = """
    MATCH (viewer:User)-[viewed:VIEWED]->(seen:Content)-[sim:SIMILAR_TO]->(candidate:Content)
    WHERE viewer.id IN $user_ids
      AND ($start_iso IS NULL OR viewed.last_viewed_at >= $start_iso)
      AND ($end_iso IS NULL OR viewed.last_viewed_at <= $end_iso)
      AND ($interaction_source IS NULL OR viewed.last_source = $interaction_source)
      AND NOT EXISTS {
          MATCH (selected:User)-[:LIKED|VIEWED]->(candidate)
          WHERE selected.id IN $user_ids
      }
    OPTIONAL MATCH (venue:Venue)
    WHERE venue.id = candidate.venue_id
    WITH candidate,
         venue,
         sum(coalesce(viewed.count, 1) * coalesce(sim.score, 0.0)) AS score,
         count(DISTINCT seen) AS based_on_count,
         collect(DISTINCT seen.id)[0..5] AS based_on_content_ids
    WHERE ($city IS NULL OR venue.city = $city)
      AND ($start_iso IS NULL OR candidate.created_at >= $start_iso)
      AND ($end_iso IS NULL OR candidate.created_at <= $end_iso)
      AND ($content_type IS NULL OR candidate.type = $content_type)
      AND ($style IS NULL OR candidate.style = $style)
      AND ($category IS NULL OR candidate.category = $category)
      AND ($sentiment IS NULL OR candidate.sentiment_label = $sentiment)
    RETURN candidate.id AS content_id,
           candidate.type AS type,
           candidate.style AS style,
           candidate.category AS category,
           candidate.sentiment_label AS sentiment,
           candidate.venue_id AS venue_id,
           venue.name AS venue_name,
           venue.city AS city,
           candidate.author_id AS author_id,
           candidate.created_at AS created_at,
           score,
           based_on_count,
           based_on_content_ids,
           "Similar to graph-viewed content" AS recommendation_source
    ORDER BY score DESC, based_on_count DESC, created_at DESC
    LIMIT $limit
    """
    return _run(driver, query, _user_params(filters, user_ids, limit))


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
