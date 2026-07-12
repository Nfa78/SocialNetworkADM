# Social Network Analytics Platform

Minimum Dockerized baseline for a university social network analytics project.

## Stack
- `MongoDB`: main database for heterogeneous social, engagement, and gastronomy documents.
- `Neo4j`: graph database for relationships and social network analysis.
- `Kafka`: real-time activity event stream for content, relationship, and known-user view events.
- `Python`: glue layer for ingestion, transformation, graph projection, and API endpoints.

## Start
Create a local environment file:

```powershell
Copy-Item .env.example .env
```

Start the stack:

```powershell
docker compose up --build
```

This starts MongoDB, Neo4j, Kafka, Kafka UI, the API, the Streamlit dashboard, the Kafka activity consumer, and the realtime simulator.
It also runs a one-shot bootstrap service that applies MongoDB validators/indexes and Neo4j indexes before the API and dashboard start.

## Useful URLs
- API health: `http://localhost:8000/health`
- API docs: `http://localhost:8000/docs`
- Neo4j browser: `http://localhost:7474`
- MongoDB: `localhost:27017`
- Kafka broker from host: `localhost:9094`
- Kafka UI: `http://localhost:8080`

## Initialize MongoDB Collections
The Docker Compose stack runs the bootstrap automatically. To re-apply the collection validators and indexes manually after the services are running:

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/bootstrap
```

You can also run the initializer directly inside the Python container:

```powershell
docker compose exec app python -m src.init_mongodb
docker compose exec app python -m src.init_neo4j
```

The initializer creates missing collections, updates validators on existing collections, and ensures MongoDB/Neo4j indexes used by the dashboard queries.

## Data Processing
Import the Kaggle restaurant dataset as venue documents:

```powershell
docker compose exec app python -m src.data_processing.import_restaurant_venues
```

Preview without writing to MongoDB:

```powershell
docker compose exec app python -m src.data_processing.import_restaurant_venues --dry-run
```

Import Sentiment140 tweets as content posts:

```powershell
docker compose exec app python -m src.data_processing.import_sentiment140_posts --limit 1000
```

Import everything we have so far through the service layer:

```powershell
docker compose exec app python -m src.data_processing.import_seed_data --limit-sentiment140 1000
```

Import synthetic relationships through the service layer:

```powershell
docker compose exec app python -m src.data_processing.import_relationships
```

## Kafka Activity Stream

Kafka is used as the real-time activity stream. MongoDB remains the canonical source of truth, and Neo4j remains a graph projection. The first topic is `activity-events`.

Activity events are written to MongoDB first. After the MongoDB insert succeeds, the API publishes the same event envelope to Kafka on a best-effort basis. If Kafka is unavailable, the MongoDB write still succeeds and the publish failure is logged.

Useful environment variables:

```text
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_ACTIVITY_TOPIC=activity-events
KAFKA_ENABLED=true
KAFKA_SOURCE_SERVICE=social-analytics-api
```

For local Python execution outside Docker, use the host listener:

```powershell
$env:KAFKA_BOOTSTRAP_SERVERS="localhost:9094"
```

The Kafka consumer starts automatically with Docker Compose. To run an extra manual consumer inside the app container:

```powershell
docker compose exec app python -m src.kafka_activity_consumer
```

The consumer logs messages and upserts them into MongoDB collection `activity_event_consumption_log` so the demo can show both stored activity events and consumed Kafka messages.

## Realtime Demo Simulator

The project includes a simulator that runs as a Docker service and creates one realistic event every 3 seconds. It creates real users, content, likes, follows, unfollows, unlikes, and known-user views through the FastAPI API, so MongoDB, Neo4j, activity events, Kafka, and the dashboard all see normal application writes.

Default demo startup:

```powershell
docker compose up --build
```

Stop only the simulator if you want the stack running without automatic writes:

```powershell
docker compose stop simulator
```

Change the event interval in `.env`:

```text
SIMULATOR_INTERVAL_SECONDS=3
```

Watch the stream in:

- Kafka UI: `http://localhost:8080`
- API docs: `http://localhost:8000/docs`
- Streamlit dashboard: `http://localhost:8501`
- Simulator logs: `docker compose logs -f simulator`
- Kafka consumer logs: `docker compose logs -f activity-consumer`

## Project Docs
- Requirements: `REQUIREMENTS.md`
- Architecture: `docs/ARCHITECTURE.md`
- Data model and analytics overview: `docs/DATA_MODEL_AND_ANALYTICS.md`
