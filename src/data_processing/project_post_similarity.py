from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from typing import Any

from src.repositories.mongo_repository import ContentRepository
from src.repositories.neo4j_repository import Neo4jRepository


MIN_SCORE = 0.35
MAX_NEIGHBORS_PER_POST = 12


def normalize_hashtag(value: str) -> str:
    return value.strip().lower().lstrip("#")


def similarity_score(source: dict[str, Any], target: dict[str, Any], shared_hashtags: list[str]) -> tuple[float, str]:
    score = 0.0
    reason_parts: list[str] = []

    if source.get("style") and source.get("style") == target.get("style"):
        score += 0.45
        reason_parts.append("same_style")
    if source.get("category") and source.get("category") == target.get("category"):
        score += 0.20
        reason_parts.append("same_category")
    if source.get("venue_id") and source.get("venue_id") == target.get("venue_id"):
        score += 0.15
        reason_parts.append("same_venue")
    if shared_hashtags:
        score += min(0.35, 0.10 + 0.08 * len(shared_hashtags))
        reason_parts.append("shared_hashtags")
    if source.get("sentiment", {}).get("label") == target.get("sentiment", {}).get("label"):
        score += 0.05
        reason_parts.append("same_sentiment")

    score = round(min(score, 1.0), 3)
    return score, "+".join(reason_parts) if reason_parts else "metadata_overlap"


def build_candidate_pairs(posts: list[dict[str, Any]]) -> dict[str, set[str]]:
    candidates: dict[str, set[str]] = defaultdict(set)

    by_style: dict[str, list[str]] = defaultdict(list)
    by_category: dict[str, list[str]] = defaultdict(list)
    by_hashtag: dict[str, list[str]] = defaultdict(list)
    by_venue: dict[str, list[str]] = defaultdict(list)

    for post in posts:
        post_id = post["_id"]
        if post.get("style"):
            by_style[post["style"]].append(post_id)
        if post.get("category"):
            by_category[post["category"]].append(post_id)
        if post.get("venue_id"):
            by_venue[post["venue_id"]].append(post_id)
        for hashtag in post.get("hashtags", []):
            by_hashtag[normalize_hashtag(hashtag)].append(post_id)

    for group in (by_style, by_category, by_hashtag, by_venue):
        for members in group.values():
            if len(members) < 2:
                continue
            for post_id in members:
                candidates[post_id].update(member for member in members if member != post_id)

    return candidates


def project_post_similarity() -> dict[str, int]:
    content_repository = ContentRepository()
    graph_repository = Neo4jRepository()

    posts = []
    for stored in content_repository.collection.find({"type": "post"}):
        posts.append(stored)

    candidate_map = build_candidate_pairs(posts)
    by_id = {post["_id"]: post for post in posts}
    created_edges = 0

    for source_id, candidate_ids in candidate_map.items():
        source = by_id[source_id]
        scored_targets: list[tuple[float, str, list[str]]] = []
        source_hashtags = {normalize_hashtag(tag) for tag in source.get("hashtags", [])}

        for target_id in candidate_ids:
            target = by_id[target_id]
            target_hashtags = {normalize_hashtag(tag) for tag in target.get("hashtags", [])}
            shared_hashtags = sorted(source_hashtags & target_hashtags)
            score, reason = similarity_score(source, target, shared_hashtags)
            if score >= MIN_SCORE:
                scored_targets.append((score, target_id, shared_hashtags, reason))

        scored_targets.sort(reverse=True, key=lambda item: item[0])
        for score, target_id, shared_hashtags, reason in scored_targets[:MAX_NEIGHBORS_PER_POST]:
            graph_repository.project_post_similarity(source_id, target_id, score, reason, shared_hashtags)
            created_edges += 1

    return {"posts": len(posts), "edges": created_edges}


def main() -> None:
    result = project_post_similarity()
    print(result)


if __name__ == "__main__":
    main()
