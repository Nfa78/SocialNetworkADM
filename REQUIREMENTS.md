# Social Network Analytics Requirements

## Scope
Build a Dockerized social network analytics platform for culture and gastronomy data. The platform uses MongoDB as the main database, Neo4j for relationship and social network analysis, and Python for ingestion, transformation, synchronization, and API access.

## Required technologies
- `Docker Compose` for local orchestration.
- `MongoDB` as the primary database for heterogeneous source and curated documents.
- `Neo4j` as the graph database for relationship-heavy analysis.
- `Python` as the glue layer for ETL, database initialization, graph projection, and demo APIs.

## Minimum services
- `mongodb`: stores users, posts, interactions, venues, reviews, check-ins, and ingestion metadata.
- `neo4j`: stores graph projections such as users, posts, topics, venues, and relationships.
- `app`: Python service exposing health checks, bootstrap actions, and future ingestion/analytics endpoints.

## Core access patterns
- Store heterogeneous source-shaped documents without forcing all data into one rigid schema.
- Query recent posts and interactions by time window.
- Retrieve user-centric feeds using social relationships and content metadata.
- Aggregate engagement by post, topic, user, venue, platform, and time period.
- Traverse social relationships such as follows, likes, comments, topics, and venues.
- Support social network analysis such as influence, communities, and multi-hop recommendations.

## Data model requirements
- MongoDB collections must use stable canonical identifiers such as `user_id`, `post_id`, `venue_id`, and `interaction_id`.
- MongoDB documents may preserve source-specific fields, but shared analytical fields must be normalized.
- Neo4j nodes must use the same canonical identifiers as MongoDB documents.
- Neo4j relationships must be derived from MongoDB records so the graph can be rebuilt.

## Initial deliverables
- `docker-compose.yml` for MongoDB, Neo4j, and Python.
- Python dependencies and service container.
- Health check endpoint proving MongoDB and Neo4j connectivity.
- Bootstrap endpoint creating indexes, graph constraints, and sample data.
- Documentation explaining the architecture and technology choices.
