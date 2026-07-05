# Neo4j Query Questions

These questions are based on the social network analytics graph:
- `(:User)`
- `(:Content)`
- `(:Venue)`
- `[:FOLLOWS]`
- `[:LIKED]`
- `[:SIMILAR_TO]`

## Question 1 — User follow network

Given that users are connected through `FOLLOWS` relationships:

- write a Cypher query that returns the users followed by a given user
- include the followed user id and the relationship creation time
- sort results by the follow time in descending order

### Answer

```cypher
MATCH (u:User {id: "user_001"})-[f:FOLLOWS]->(u2:User)
RETURN u2.id AS followed_user_id, u2.username AS followed_username, f.created_at AS follow_time
ORDER BY follow_time DESC
```

## Question 2 — Most liked posts

Given that users like content through `LIKED` relationships:

- write a Cypher query that finds the top 10 posts with the highest number of incoming `LIKED` relationships
- return the post id and number of likes
- sort by likes in descending order

### Answer

```cypher
MATCH (:User)-[:LIKED]->(p:Post)
WITH p, count(*) AS total_likes
RETURN p.id AS post_id, total_likes
ORDER BY total_likes DESC
LIMIT 10
```

## Question 3 — Similar content recommendations

Given that some posts are connected with `SIMILAR_TO`:

- write a Cypher query that finds posts similar to a given post
- return the similar post id, similarity score, and shared hashtags if available
- only keep results with a similarity score greater than or equal to `0.5`

### Answer

```cypher
MATCH (p:Post {id: "content_2050"})<-[r:SIMILAR_TO]-(p2:Post)
WHERE r.score >= 0.5
RETURN p2.id AS similar_post_id, r.score AS similarity_score, r.shared_hashtags AS shared_hashtags
ORDER BY similarity_score DESC
```

## Question 4 — Taste-based user recommendation

Given a user and the content they have liked:

- write a Cypher query that finds other users who liked the same content
- count how many liked posts they have in common
- return the user ids and the overlap count
- sort by overlap count in descending order

### Answer

```cypher
MATCH (u1:User {id: "user_004"})-[:LIKED]->(c:Content)<-[:LIKED]-(u2:User)
WHERE u1 <> u2
WITH u1.id AS main_user, u2.id AS similar_user, count(DISTINCT c) AS overlap_count
RETURN main_user, similar_user, overlap_count
ORDER BY overlap_count DESC
LIMIT 10
```

## Question 5 — Venue popularity

Given venue nodes in the graph:

- write a Cypher query that finds venues followed by the most users
- return the venue id and the number of followers
- sort by follower count in descending order

### Answer

```cypher
MATCH (:User)-[:FOLLOWS]->(v:Venue)
WITH v, count(*) AS follower_count
RETURN v.id AS venue_id, v.name AS venue_name, follower_count
ORDER BY follower_count DESC
LIMIT 5
```

