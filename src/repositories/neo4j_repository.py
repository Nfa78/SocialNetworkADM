from typing import Any

from src.db import neo4j_session
from src.domain.enums import RelationshipTargetType, RelationshipType
from src.domain.models import ContentDocument, RelationshipDocument


class Neo4jRepository:
    def project_content(self, content: ContentDocument) -> None:
        node_labels = ["Content", content.type.capitalize()]
        properties: dict[str, Any] = {
            "id": content.id,
            "type": content.type,
            "author_id": content.author_id,
            "created_at": content.created_at.isoformat(),
            "hashtags": list(content.hashtags),
            "source": content.source,
        }

        if getattr(content, "style", None) is not None:
            properties["style"] = content.style
        if getattr(content, "category", None) is not None:
            properties["category"] = content.category
        if getattr(content, "venue_id", None) is not None:
            properties["venue_id"] = content.venue_id
        if getattr(content, "external_id", None) is not None:
            properties["external_id"] = content.external_id
        if getattr(content, "sentiment", None) is not None:
            properties["sentiment_label"] = content.sentiment.label
            if content.sentiment.score is not None:
                properties["sentiment_score"] = content.sentiment.score
            if content.sentiment.polarity is not None:
                properties["sentiment_polarity"] = content.sentiment.polarity

        if content.type == "review" and getattr(content, "rating", None) is not None:
            properties["rating"] = content.rating
        if content.type == "comment" and getattr(content, "parent_content_id", None) is not None:
            properties["parent_content_id"] = content.parent_content_id

        properties = {key: value for key, value in properties.items() if value is not None}
        labels_clause = ":".join(node_labels)

        with neo4j_session() as session:
            session.run(
                f"""
                MERGE (node:{labels_clause} {{id: $content_id}})
                SET node += $properties
                """,
                content_id=content.id,
                properties=properties,
            )

    def project_venue(self, venue: dict[str, Any]) -> None:
        properties: dict[str, Any] = {
            "id": venue.get("_id"),
            "name": venue.get("name"),
            "domain": venue.get("domain"),
            "category": venue.get("category"),
            "city": venue.get("city"),
            "source": venue.get("source"),
            "source_id": venue.get("source_id"),
            "locality": venue.get("locality"),
            "locality_verbose": venue.get("locality_verbose"),
            "cuisines": venue.get("cuisines"),
        }

        created_at = venue.get("created_at")
        if created_at is not None:
            properties["created_at"] = created_at.isoformat()

        pricing = venue.get("pricing")
        if pricing is not None:
            properties["average_cost_for_two"] = pricing.get("average_cost_for_two")
            properties["currency"] = pricing.get("currency")
            properties["price_range"] = pricing.get("price_range")

        rating = venue.get("rating")
        if rating is not None:
            properties["aggregate_rating"] = rating.get("aggregate_rating")
            properties["rating_color"] = rating.get("rating_color")
            properties["rating_text"] = rating.get("rating_text")
            properties["votes"] = rating.get("votes")

        location = venue.get("location")
        if location is not None:
            coordinates = location.get("coordinates")
            if isinstance(coordinates, list) and len(coordinates) == 2:
                properties["longitude"] = coordinates[0]
                properties["latitude"] = coordinates[1]

        properties = {key: value for key, value in properties.items() if value is not None}

        with neo4j_session() as session:
            session.run(
                """
                MERGE (node:Venue {id: $venue_id})
                SET node += $properties
                """,
                venue_id=venue.get("_id"),
                properties=properties,
            )

    def project_post_similarity(
        self,
        source_content_id: str,
        target_content_id: str,
        score: float,
        reason: str,
        shared_hashtags: list[str],
    ) -> None:
        with neo4j_session() as session:
            session.run(
                """
                MATCH (source:Content {id: $source_content_id})
                MATCH (target:Content {id: $target_content_id})
                MERGE (source)-[rel:SIMILAR_TO]->(target)
                SET rel.score = $score,
                    rel.reason = $reason,
                    rel.shared_hashtags = $shared_hashtags
                """,
                source_content_id=source_content_id,
                target_content_id=target_content_id,
                score=score,
                reason=reason,
                shared_hashtags=shared_hashtags,
            )

    def project_relationship(self, relationship: RelationshipDocument) -> None:
        if relationship.type == RelationshipType.FOLLOW:
            self._project_follow(relationship)
            return
        if relationship.type == RelationshipType.LIKE:
            self._project_like(relationship)
            return
        raise ValueError(f"Unsupported relationship type: {relationship.type}")

    def delete_relationship(self, relationship: RelationshipDocument) -> None:
        if relationship.type == RelationshipType.FOLLOW:
            relationship_name = "FOLLOWS"
        elif relationship.type == RelationshipType.LIKE:
            relationship_name = "LIKED"
        else:
            raise ValueError(f"Unsupported relationship type: {relationship.type}")

        with neo4j_session() as session:
            session.run(
                f"""
                MATCH (source {{id: $source_id}})-[rel:{relationship_name}]->(target {{id: $target_id}})
                DELETE rel
                """,
                source_id=relationship.source_user_id,
                target_id=relationship.target_id,
            )

    def _project_follow(self, relationship: RelationshipDocument) -> None:
        if relationship.target_type == RelationshipTargetType.USER:
            target_label = "User"
        elif relationship.target_type == RelationshipTargetType.VENUE:
            target_label = "Venue"
        else:
            raise ValueError("follow relationships can target only users or venues")

        with neo4j_session() as session:
            session.run(
                f"""
                MERGE (source:User {{id: $source_id}})
                MERGE (target:{target_label} {{id: $target_id}})
                MERGE (source)-[rel:FOLLOWS]->(target)
                SET rel.created_at = $created_at
                """,
                source_id=relationship.source_user_id,
                target_id=relationship.target_id,
                created_at=relationship.created_at.isoformat(),
            )

    def _project_like(self, relationship: RelationshipDocument) -> None:
        with neo4j_session() as session:
            session.run(
                """
                MERGE (source:User {id: $source_id})
                MERGE (target:Content {id: $target_id})
                MERGE (source)-[rel:LIKED]->(target)
                SET rel.created_at = $created_at
                """,
                source_id=relationship.source_user_id,
                target_id=relationship.target_id,
                created_at=relationship.created_at.isoformat(),
            )
