# Architecture

## Baseline stack
- `MongoDB` is the main operational and analytical document store.
- `Neo4j` stores relationship projections for social network analysis.
- `Python` glues ingestion, transformation, API endpoints, and cross-store synchronization.
- `Docker Compose` runs the full local stack.

## Why MongoDB is the main database
The project sources are heterogeneous: tweets, engagement logs, social usage records, Yelp reviews, venues, photos, and check-ins do not share one clean relational schema. MongoDB is the primary store because it can preserve source-shaped documents while still supporting useful indexes and aggregation pipelines.

The intended MongoDB collections are:
- `users`
- `posts`
- `interactions`
- `venues`
- `reviews`
- `checkins`
- `ingestion_runs`

## Why Neo4j is separate
Neo4j is used for graph-native access patterns:
- follower and followee traversals
- influence analysis
- community detection
- multi-hop recommendations
- user, post, topic, and venue relationships

MongoDB remains the source for full document details. Neo4j stores the relationship projection needed for graph queries.

## Python service responsibilities
- Initialize database indexes and graph constraints.
- Run ingestion and transformation jobs.
- Synchronize graph projections from MongoDB into Neo4j.
- Expose small API endpoints for health checks, demo queries, and later analytics.

## Data flow
1. Raw datasets are placed under `data/`.
2. Python ingestion reads source files and writes canonical documents to MongoDB.
3. Python projection jobs create or update relationship nodes and edges in Neo4j.
4. Demo APIs query MongoDB for documents and Neo4j for graph relationships.
