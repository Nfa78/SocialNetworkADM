from src.db import neo4j_session


NEO4J_INDEX_STATEMENTS = {
    "user_id_idx": "CREATE INDEX user_id_idx IF NOT EXISTS FOR (node:User) ON (node.id)",
    "user_city_idx": "CREATE INDEX user_city_idx IF NOT EXISTS FOR (node:User) ON (node.city)",
    "venue_id_idx": "CREATE INDEX venue_id_idx IF NOT EXISTS FOR (node:Venue) ON (node.id)",
    "venue_city_idx": "CREATE INDEX venue_city_idx IF NOT EXISTS FOR (node:Venue) ON (node.city)",
    "venue_category_idx": "CREATE INDEX venue_category_idx IF NOT EXISTS FOR (node:Venue) ON (node.category)",
    "content_id_idx": "CREATE INDEX content_id_idx IF NOT EXISTS FOR (node:Content) ON (node.id)",
    "content_created_at_idx": "CREATE INDEX content_created_at_idx IF NOT EXISTS FOR (node:Content) ON (node.created_at)",
    "content_type_idx": "CREATE INDEX content_type_idx IF NOT EXISTS FOR (node:Content) ON (node.type)",
    "content_style_idx": "CREATE INDEX content_style_idx IF NOT EXISTS FOR (node:Content) ON (node.style)",
    "content_category_idx": "CREATE INDEX content_category_idx IF NOT EXISTS FOR (node:Content) ON (node.category)",
    "content_sentiment_idx": "CREATE INDEX content_sentiment_idx IF NOT EXISTS FOR (node:Content) ON (node.sentiment_label)",
    "content_venue_idx": "CREATE INDEX content_venue_idx IF NOT EXISTS FOR (node:Content) ON (node.venue_id)",
    "follows_created_at_idx": "CREATE INDEX follows_created_at_idx IF NOT EXISTS FOR ()-[rel:FOLLOWS]-() ON (rel.created_at)",
    "liked_created_at_idx": "CREATE INDEX liked_created_at_idx IF NOT EXISTS FOR ()-[rel:LIKED]-() ON (rel.created_at)",
    "similar_score_idx": "CREATE INDEX similar_score_idx IF NOT EXISTS FOR ()-[rel:SIMILAR_TO]-() ON (rel.score)",
}


def initialize_neo4j_indexes() -> dict[str, str]:
    results = {}
    with neo4j_session() as session:
        for index_name, statement in NEO4J_INDEX_STATEMENTS.items():
            session.run(statement).consume()
            results[index_name] = "ensured"
    return results
