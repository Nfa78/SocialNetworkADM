# Data Visualisation Plan

This document describes what can be visualised from the current project schemas and available data, and how those visualisations can support statistics, trends, interesting findings, and relationship analysis.

The project currently has two main database layers:

- MongoDB: document store for users, content, interactions, relationships, activity events, and venues.
- Neo4j: graph projection for users, venues, content, follows, likes, and content similarity.

The recommended implementation path is a Streamlit dashboard backed by MongoDB aggregation queries and Neo4j Cypher queries, with Neo4j Browser kept available for direct graph exploration.

## Dashboard Runtime Data Sources

The dashboard should retrieve live data from the databases, not directly from the raw CSV or JSON files.

Use the raw and synthetic files only for ingestion, bootstrap, repeatable seeding, and documentation of what data is available. After import, the visualisation layer should read from:

- MongoDB collections: `users`, `content`, `interactions`, `relationships`, `venues`, and later `activity_events`.
- Neo4j graph: `User`, `Venue`, `Content`, `FOLLOWS`, `LIKED`, and `SIMILAR_TO`.

This keeps the dashboard aligned with the actual database state, including imported data, projected graph relationships, counters, and future updates.

## Running The Dashboard

The dashboard is implemented as a dedicated Docker Compose service.

```powershell
docker compose up --build
```

Useful URLs:

- FastAPI: `http://localhost:8000`
- Streamlit dashboard: `http://localhost:8501`
- Neo4j Browser: `http://localhost:7474`

The dashboard port can be changed with `DASHBOARD_PORT` in `.env`.

Implemented dashboard files:

```text
visualisation/
  README.md
  streamlit_app.py
  data_access.py
  mongo_queries.py
  neo4j_queries.py
  charts.py
```

## Available Imported Or Importable Data

Observed local files on 2026-06-28:

| Source | Available volume | Main fields | Main visualisation dimensions |
| --- | ---: | --- | --- |
| `data/synthetic/users.json` | 10,000 users | `_id`, `username`, `display_name`, `city`, `interests`, `created_at` | city, interests, signup time, user activity |
| `data/synthetic/content.json` | 15,000 content items | `type`, `author_id`, `text`, `style`, `category`, `venue_id`, `hashtags`, `location`, `sentiment`, `created_at`, `metrics` | time, content type, style, category, sentiment, hashtags, venue, location, engagement |
| `data/synthetic/interactions.json` | 50,000 views | `type`, `user_id`, `content_id`, `source`, `session_id`, `duration_ms`, `created_at` | time, source, session, user, content, viewing duration |
| `data/synthetic/relationships.json` | 30,000 likes/follows | `type`, `source_user_id`, `target_type`, `target_id`, `created_at` | time, relationship type, source user, target user/content/venue |
| `data/raw/restaurant-dataset/Dataset .csv` | 9,551 venues | restaurant name, city, address, locality, longitude, latitude, cuisines, price, booking/delivery flags, rating, votes | city, map location, cuisine, price, rating, votes, venue features |
| `data/raw/sentiment140/training.1600000.processed.noemoticon.csv` | 1.6M raw tweets | polarity, tweet id, date, query, author, text | tweet time, sentiment, author, hashtags after import |
| MongoDB `activity_events` collection | schema exists, no seed file found | `type`, `actor_user_id`, `target_type`, `target_id`, `metadata`, `created_at` | event timeline, user activity, target type, audit/history |
| Neo4j graph | projected from imports | `User`, `Venue`, `Content`, `FOLLOWS`, `LIKED`, `SIMILAR_TO` | graph topology, communities, influence, recommendations |

Important time ranges in the synthetic data:

| Dataset | Approximate date range |
| --- | --- |
| Users | 2024-12-31 to 2026-06-19 |
| Content | 2025-06-18 to 2026-06-19 |
| Interactions/views | 2025-07-03 to 2026-06-19 |
| Relationships | 2025-01-26 to 2026-06-19 |

## High-Level Dashboard Pages

### 1. Overview

Purpose: give a fast summary of platform size and health.

Useful widgets:

- Total users.
- Total venues.
- Total content items, split by `post`, `review`, and `comment`.
- Total interactions/views.
- Total likes.
- Total follows.
- Average view duration.
- Average venue rating.
- Positive/neutral/negative sentiment share.
- Top cities by users.
- Top cities by venues.
- Most active day or week.

Recommended charts:

- KPI cards.
- Bar chart: content count by type.
- Bar chart: users by city.
- Bar chart: interactions by source.
- Donut or stacked bar: sentiment distribution.
- Line chart: total activity over time.

### 2. Content Analytics

Purpose: understand what content exists and which content performs best.

Visualisable fields:

- `type`: post, review, comment.
- `style`: food, culture, travel, lifestyle, event, guide.
- `category`.
- `hashtags`.
- `sentiment.label`, `sentiment.score`, `sentiment.polarity`.
- `created_at`.
- `venue_id`.
- `location`.
- `metrics.view_count`, `metrics.like_count`, `metrics.comment_count`, `metrics.share_count`, `metrics.last_viewed_at`.

Useful questions:

- How many posts, reviews, and comments are created over time?
- Which content styles are most common?
- Which styles or categories receive the most views?
- Which hashtags are growing or declining?
- Which content has unusually high engagement?
- Are positive posts viewed or liked more than negative posts?
- Are venue-linked posts more engaging than generic posts?
- Which venues receive the most content mentions?

Recommended charts:

- Time series: content created per day/week/month.
- Stacked time series: content by type over time.
- Bar chart: top hashtags.
- Bar chart: content count by style/category.
- Scatter plot: view count vs like count.
- Heatmap: style/category vs sentiment.
- Table: top content by views, likes, or comments.

### 3. Engagement And Behaviour

Purpose: understand how users consume content.

Visualisable fields:

- `interactions.type`: currently `view`.
- `interactions.source`: feed, profile, search, venue, recommendation, direct, unknown.
- `interactions.duration_ms`.
- `interactions.session_id`.
- `interactions.user_id`.
- `interactions.content_id`.
- `interactions.created_at`.
- Embedded `users.recent_interactions`.

Useful questions:

- Which traffic source generates the most views?
- Which source has the longest average view duration?
- Does recommendation traffic perform better than feed/search/direct traffic?
- Which users view the most content?
- Which content receives the most repeat views?
- What times or days have the highest viewing activity?
- Are sessions short and frequent, or long and deep?

Recommended charts:

- Bar chart: views by source.
- Line chart: views over time.
- Box plot or histogram: view duration distribution.
- Bar chart: average duration by source.
- Table: top viewed content.
- Table: most active users.
- Heatmap: hour of day vs day of week, if timestamps are converted into local time buckets.

### 4. Venue And Location Analytics

Purpose: make location a first-class analysis variable.

Visualisable fields:

- Venue city, locality, address, country code.
- Venue latitude and longitude from the restaurant CSV.
- Venue cuisines.
- Venue `pricing.average_cost_for_two`, `pricing.currency`, `pricing.price_range`.
- Venue `features.has_table_booking`, `features.has_online_delivery`, `features.is_delivering_now`.
- Venue `rating.aggregate_rating`, `rating.rating_text`, `rating.votes`.
- User city.
- Content `location` or `venue_id`.

Useful questions:

- Which cities have the most venues?
- Which cities have the most users?
- Where do users and venues overlap?
- Which cities or localities have the highest-rated venues?
- Which cuisines are most common by city?
- Which cuisines have high ratings but low visibility?
- Which venues receive the most follows, likes, reviews, posts, or views?
- Do high-price venues receive better ratings?
- Does online delivery or table booking correlate with rating or votes?

Recommended charts:

- Map: venue points by latitude/longitude.
- Bar chart: venues by city.
- Bar chart: users by city.
- Bar chart: top cuisines.
- Scatter plot: price range vs aggregate rating.
- Scatter plot: votes vs aggregate rating.
- Map or table: top-rated venues by city.
- Choropleth-style city summary if city boundaries are added later.

Important caveat:

- Venue `created_at` is currently import time, not the historical opening date of the restaurant. Use it for data lineage, not for business trend analysis.

### 5. Social Graph And Relations

Purpose: expose relationships that are hard to see in document tables.

Current graph relations:

- `(User)-[:FOLLOWS]->(User)`
- `(User)-[:FOLLOWS]->(Venue)`
- `(User)-[:LIKED]->(Content)`
- `(Content)-[:SIMILAR_TO]->(Content)`

Useful questions:

- Who are the most followed users?
- Which users follow many venues?
- Which venues are most followed?
- Which content is liked by influential users?
- Which content clusters are similar by style, category, venue, hashtags, and sentiment?
- Which users connect otherwise separate communities?
- Are there communities around cities, interests, venue categories, or hashtags?
- Can we recommend content based on similar posts and liked content?
- Can we recommend venues based on follows, content references, and user interests?

Recommended visualisations:

- Neo4j Browser graph view for interactive exploration.
- Small sampled network graph in Streamlit for dashboards.
- Bar chart: top users by in-degree/followers.
- Bar chart: top venues by followers.
- Bar chart: top content by likes.
- Network community view from Neo4j Graph Data Science if added later.
- Table: shortest paths between two users or between a user and a venue.

Graph size warning:

- Do not render the full graph in a single dashboard view. Filter by city, user, venue, hashtag, date range, or graph depth. For Streamlit, use sampled subgraphs such as top 50 nodes or 1-hop/2-hop neighbourhoods.

### 6. Trends And Interesting Findings

Purpose: make the dashboard answer analytical questions, not only display counts.

Good findings to surface:

- Fastest-growing hashtags over the selected period.
- Content styles with high engagement but low volume.
- Cities with many venues but few users.
- Cities with many users but few venues.
- Venues with high ratings but low votes, useful as hidden gems.
- Venues with high follower counts but weak ratings, useful as popularity vs quality contrast.
- Recommendation traffic vs feed/search/direct traffic by duration.
- Sentiment changes over time.
- Negative sentiment spikes by day/week.
- User signup growth by city.
- Influential users by followers, likes generated, or graph centrality.
- Content clusters with strong shared hashtags.
- Cuisine categories with strong engagement.
- Review rating trends by city or venue category.

Recommended chart types:

- Line chart: metric over time.
- Stacked area: sentiment over time.
- Ranking table: top movers compared to previous period.
- Scatter plot: popularity vs quality.
- Heatmap: category vs sentiment or category vs engagement.
- Network graph: community or similarity cluster.

## Time As A Variable

The primary time field is `created_at`.

Use it differently depending on collection:

| Collection | Meaning of `created_at` | Best use |
| --- | --- | --- |
| `users` | signup/account creation time | user growth, cohorts by city |
| `content` | post/review/comment creation time | publishing trend, sentiment trend, content mix |
| `interactions` | view event time | traffic trend, source trend, session behaviour |
| `relationships` | like/follow creation time | social growth, content popularity, venue popularity |
| `activity_events` | event audit time | unified activity feed once populated |
| `venues` | import/document creation time | data ingestion timeline only |
| Sentiment140 raw/imported posts | original tweet date | historical sentiment trend |

Recommended time filters:

- Global date range selector.
- Time bucket selector: day, week, month.
- Optional hour-of-day and day-of-week filters for interaction analysis.
- Compare current period vs previous period.

## Location As A Variable

Location exists in several forms:

- Users have `city`.
- Venues have `city`, `locality`, and latitude/longitude.
- Content can have a string `location`, embedded coordinates, or a `venue_id`.
- Restaurant data includes city, locality, address, longitude, and latitude.

Recommended location joins:

- Content to venues through `content.venue_id = venues._id`.
- Relationships to venues through `relationships.target_type = "venue"` and `relationships.target_id = venues._id`.
- User engagement to city through `interactions.user_id = users._id`.
- Venue engagement to city through content or follows linked to the venue.

Useful location visualisations:

- User distribution by city.
- Venue distribution by city.
- Venue map by rating or cuisine.
- Engagement by city.
- Sentiment by city where content has location or venue linkage.
- Cuisine popularity by city.

## Streamlit Structure

Module responsibilities:

- `streamlit_app.py`: page layout, sidebar filters, tabs, empty states, and table rendering.
- `data_access.py`: cached MongoDB and Neo4j connections from environment variables.
- `mongo_queries.py`: database-side MongoDB aggregations for KPIs, charts, and ranked tables.
- `neo4j_queries.py`: Cypher summaries for relationship rankings and content similarity.
- `charts.py`: reusable Plotly chart builders.

Recommended Python libraries:

- `streamlit`: dashboard framework.
- `pandas`: tabular transformations.
- `plotly`: charts and maps.
- `pymongo`: MongoDB access.
- `neo4j`: Neo4j access.
- `networkx` or `pyvis`: optional graph rendering for small sampled networks.

Recommended dashboard filters:

- Date range.
- City.
- Content type.
- Content style/category.
- Sentiment.
- Interaction source.
- Venue category/cuisine.
- Minimum views/likes/follows.
- Graph depth and maximum node count.

## MongoDB Aggregation Ideas

Useful aggregation outputs:

- Content count by day and type.
- Sentiment count by day.
- Views by day and source.
- Average duration by source.
- Top hashtags.
- Top content by `metrics.view_count`.
- Top users by number of views/interactions.
- Venue count by city/cuisine.
- Average rating by city/category/cuisine.
- Venue follows by city.

Example aggregation shape:

```javascript
[
  { "$match": { "created_at": { "$gte": start_date, "$lte": end_date } } },
  { "$group": { "_id": { "day": "$day_bucket", "type": "$type" }, "count": { "$sum": 1 } } },
  { "$sort": { "_id.day": 1 } }
]
```

In implementation, create the date bucket using MongoDB date operators such as `$dateTrunc` rather than manually formatting timestamps in Python.

## Neo4j Query Ideas

Useful Cypher outputs:

- Most followed users.
- Most followed venues.
- Most liked content.
- User neighbourhood around one selected user.
- Venue audience graph.
- Content similarity graph.
- Shortest path between users.
- Common interests inferred from followed venues and liked content.

Example query shapes:

```cypher
MATCH (u:User)-[:FOLLOWS]->(target:User)
RETURN target.id AS user_id, count(*) AS followers
ORDER BY followers DESC
LIMIT 20;
```

```cypher
MATCH (u:User)-[:FOLLOWS]->(v:Venue)
RETURN v.city AS city, count(*) AS venue_follows
ORDER BY venue_follows DESC;
```

```cypher
MATCH (c1:Content)-[r:SIMILAR_TO]->(c2:Content)
RETURN c1.id AS source, c2.id AS target, r.score AS score, r.reason AS reason
ORDER BY score DESC
LIMIT 100;
```

## Priority Build Order

1. Build the Overview page with KPI cards and basic bar charts.
2. Add global filters for date range, city, content type, and sentiment.
3. Add Content Analytics with content trends, sentiment, hashtags, and top content.
4. Add Engagement Analytics with views over time, sources, and durations.
5. Add Venue And Location Analytics with city summaries and a venue map.
6. Add Neo4j graph summaries for top users, venues, liked content, and sampled neighbourhoods.
7. Add Interesting Findings cards that compare current period vs previous period.

## Data Quality Notes

- The synthetic data is useful for demo analytics but should be labelled as synthetic.
- Sentiment140 provides historical tweet sentiment, but only the imported subset appears in MongoDB unless the import limit is increased.
- The restaurant dataset is mostly a venue/rating snapshot, not a historical event stream.
- `activity_events` is designed for a unified timeline but needs populated data before it becomes useful.
- Content locations are mixed: some are plain labels, some can be coordinates, and many venue-linked items should inherit location from the venue.
- Graph visualisations should be filtered or sampled because the relationship data is already large enough to clutter full-network views.
