# Social Network Analytics Platform

Dockerized project with MongoDB, Neo4j, Kafka, FastAPI, and a Streamlit dashboard.

MongoDB stores the canonical documents. Neo4j stores graph projections for relationship and recommendation queries. Kafka is used for the activity-event stream.

## Requirements

- Docker Desktop or Docker Engine with Docker Compose.

## Run From A Clean Checkout

From the project root:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Wait until the services are running, then stop the simulator before loading initial data:

```powershell
docker compose stop simulator
```

Initialize schemas and indexes:

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/bootstrap
```

Import data:

```powershell
docker compose exec app python -m src.data_processing.import_seed_data --limit-sentiment140 1000
```

If `data/raw/` or `data/synthetic/` files are missing, the importer automatically creates compact sample data, so the project still runs from a clean submission.

Build Neo4j recommendation edges:

```powershell
docker compose exec app python -m src.data_processing.project_graph_edges
docker compose exec app python -m src.data_processing.project_post_similarity
```

Open the dashboard:

```text
http://localhost:8501
```

## Useful URLs

- Dashboard: `http://localhost:8501`
- API docs: `http://localhost:8000/docs`
- API health: `http://localhost:8000/health`
- Neo4j Browser: `http://localhost:7474`
- Kafka UI: `http://localhost:8080`

Neo4j login:

```text
username: neo4j
password: neo4j_password
```

## Optional Full Dataset Setup

If internet/KaggleHub access is available, download the larger raw datasets before importing:

```powershell
docker compose exec app python -m src.scripts.download_restaurant_dataset
docker compose exec app python -m src.data_processing.download_sentiment140
docker compose exec app python -m src.data_processing.generate_connected_synthetic_corpus
docker compose exec app python -m src.data_processing.import_seed_data --limit-sentiment140 1000
docker compose exec app python -m src.data_processing.project_graph_edges
docker compose exec app python -m src.data_processing.project_post_similarity
```

## Reset Local Databases

```powershell
docker compose down -v
```

Then repeat the run steps.

## Notes For Submission

Do not rely on local Docker volumes. They are not part of Git or a normal ZIP submission.

Submit the code, Docker files, schema, docs, and `.env.example`. The data can be regenerated with:

```powershell
docker compose exec app python -m src.data_processing.import_seed_data --limit-sentiment140 1000
```

For an offline demo, you may also include:

```text
data/synthetic/
data/raw/restaurant-dataset/Dataset .csv
```

The project still runs without those files because compact sample data is generated automatically.
