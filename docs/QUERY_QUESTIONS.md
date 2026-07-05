# Query Questions

These questions are based on the social network analytics database:
- `users`
- `content`
- `interactions`
- `relationships`
- `venues`

## MongoDB Filter and Group Examples

### Simple filter with `find`

Use `find` when you only need to filter and return matching documents.

This example returns food posts with at least `20` likes and only shows selected fields.

```javascript
db.content.find(
  {
    type: "post",
    style: "food",
    "metrics.like_count": { $gte: 20 }
  },
  {
    _id: 1,
    author_id: 1,
    style: 1,
    hashtags: 1,
    "metrics.like_count": 1
  }
).sort({
  "metrics.like_count": -1
}).limit(10)
```

SQL-style idea:

```sql
SELECT _id, author_id, style, hashtags, metrics.like_count
FROM content
WHERE type = 'post'
  AND style = 'food'
  AND metrics.like_count >= 20
ORDER BY metrics.like_count DESC
LIMIT 10;
```

### More `find` query examples

Use `find` for normal document retrieval. It can filter, project fields, sort, skip, and limit results.

Important: `find` does not group documents. For grouping, use `aggregate` with `$group`.

#### Exact match

Find users from Turin.

```javascript
db.users.find(
  {
    city: "Turin"
  },
  {
    _id: 0,
    username: 1,
    display_name: 1,
    city: 1
  }
)
```

#### Comparison filter

Find venues with rating at least `4.5` and at least `200` votes.

```javascript
db.venues.find(
  {
    "rating.aggregate_rating": { $gte: 4.5 },
    "rating.votes": { $gte: 200 }
  },
  {
    _id: 0,
    name: 1,
    city: 1,
    category: 1,
    "rating.aggregate_rating": 1,
    "rating.votes": 1
  }
).sort({
  "rating.votes": -1
})
```

#### Array contains value

Find content that contains the hashtag `culture`.

```javascript
db.content.find(
  {
    hashtags: "culture"
  },
  {
    _id: 1,
    author_id: 1,
    style: 1,
    hashtags: 1
  }
)
```

#### Match one of several values with `$in`

Find posts whose style is either `food`, `travel`, or `culture`.

```javascript
db.content.find(
  {
    type: "post",
    style: {
      $in: ["food", "travel", "culture"]
    }
  },
  {
    _id: 1,
    author_id: 1,
    style: 1,
    category: 1
  }
)
```

#### OR condition with `$or`

Find venues that are either highly rated or have many votes.

```javascript
db.venues.find(
  {
    $or: [
      {
        "rating.aggregate_rating": { $gte: 4.8 }
      },
      {
        "rating.votes": { $gte: 500 }
      }
    ]
  },
  {
    _id: 0,
    name: 1,
    city: 1,
    "rating.aggregate_rating": 1,
    "rating.votes": 1
  }
)
```

#### Array size or existence

Find users who have at least one recent interaction.

```javascript
db.users.find(
  {
    "recent_interactions.0": {
      $exists: true
    }
  },
  {
    _id: 0,
    username: 1,
    city: 1,
    recent_interactions: 1
  }
)
```

#### Date range

Find relationships created on or after `2026-06-01`.

```javascript
db.relationships.find(
  {
    created_at: {
      $gte: new Date("2026-06-01T00:00:00Z")
    }
  },
  {
    _id: 1,
    type: 1,
    source_user_id: 1,
    target_type: 1,
    target_id: 1,
    created_at: 1
  }
).sort({
  created_at: -1
})
```

#### Pagination with `skip` and `limit`

Find the second page of food posts, assuming `10` results per page.

```javascript
db.content.find(
  {
    type: "post",
    style: "food"
  },
  {
    _id: 1,
    author_id: 1,
    style: 1,
    "metrics.like_count": 1
  }
).sort({
  "metrics.like_count": -1
}).skip(10).limit(10)
```

### Filter with `$match` in an aggregation pipeline

Use `$match` when filtering is part of a larger aggregation pipeline.

This example filters venues by city, rating, and vote count.

```javascript
db.venues.aggregate([
  {
    $match: {
      city: "Makati City",
      "rating.aggregate_rating": { $gte: 4.5 },
      "rating.votes": { $gte: 200 }
    }
  },
  {
    $project: {
      _id: 0,
      name: 1,
      city: 1,
      category: 1,
      "rating.aggregate_rating": 1,
      "rating.votes": 1
    }
  }
])
```

SQL-style idea:

```sql
SELECT name, city, category, rating.aggregate_rating, rating.votes
FROM venues
WHERE city = 'Makati City'
  AND rating.aggregate_rating >= 4.5
  AND rating.votes >= 200;
```

### Group with `$group`

Use `$group` to group documents and calculate aggregate values such as counts, sums, and averages.

This example groups content by `style` and calculates the number of posts plus average likes.

```javascript
db.content.aggregate([
  {
    $match: {
      type: "post"
    }
  },
  {
    $group: {
      _id: "$style",
      total_posts: { $sum: 1 },
      average_likes: { $avg: "$metrics.like_count" }
    }
  },
  {
    $sort: {
      total_posts: -1
    }
  }
])
```

SQL-style idea:

```sql
SELECT style, COUNT(*) AS total_posts, AVG(metrics.like_count) AS average_likes
FROM content
WHERE type = 'post'
GROUP BY style
ORDER BY total_posts DESC;
```

### Filter first, then group

In MongoDB aggregation, `$match` normally comes before `$group`. This filters the input documents first, then groups only the matching documents.

This example filters recent `like` relationships for content, then groups them by user.

```javascript
db.relationships.aggregate([
  {
    $match: {
      type: "like",
      target_type: "content",
      created_at: {
        $gte: new Date("2026-06-01T00:00:00Z")
      }
    }
  },
  {
    $group: {
      _id: "$source_user_id",
      total_likes: { $sum: 1 }
    }
  },
  {
    $project: {
      _id: 0,
      source_user_id: "$_id",
      total_likes: 1
    }
  },
  {
    $sort: {
      total_likes: -1
    }
  }
])
```

SQL-style idea:

```sql
SELECT source_user_id, COUNT(*) AS total_likes
FROM relationships
WHERE type = 'like'
  AND target_type = 'content'
  AND created_at >= '2026-06-01T00:00:00Z'
GROUP BY source_user_id
ORDER BY total_likes DESC;
```

## Question 1 — User activity profile

Given the `users` collection:

```json
{
  "_id": "user_001",
  "username": "user_001",
  "display_name": "User 0001",
  "city": "Turin",
  "interests": ["pasta", "museums", "street_food"],
  "recent_interactions": [
    {
      "type": "view",
      "content_id": "content_010",
      "created_at": "2026-06-10T12:30:00Z"
    }
  ]
}
```

Write a MongoDB query that retrieves all users from the city `"Turin"` who have at least one recent interaction, and returns only:
- `username`
- `display_name`
- `city`
- the number of recent interactions

Sort the results by number of recent interactions in descending order.

### Answer

```javascript
db.users.aggregate([
  {
    $match: {
      city: "Turin",
      "recent_interactions.0": { $exists: true }
    }
  },
  {
    $project: {
      _id: 0,
      username: 1,
      display_name: 1,
      city: 1,
      recent_interactions_count: { $size: "$recent_interactions" }
    }
  },
  {
    $sort: { recent_interactions_count: -1 }
  }
])
```

## Question 2 — Popular content by style

Given the `content` collection:

```json
{
  "_id": "content_120",
  "type": "post",
  "author_id": "user_014",
  "style": "food",
  "category": "food",
  "hashtags": ["pasta", "local", "restaurant"],
  "metrics": {
    "view_count": 123,
    "like_count": 41,
    "comment_count": 8
  }
}
```

Write a MongoDB query that finds the top 10 `post` documents with:
- `style = "food"`
- at least 20 likes
- at least 50 views

Return only:
- `_id`
- `author_id`
- `style`
- `hashtags`
- `metrics.view_count`
- `metrics.like_count`

Sort by `metrics.like_count` in descending order.

### Answer

```javascript
db.content.aggregate([
  {
    $match: {
      type: "post",
      style: "food",
      "metrics.like_count": { $gte: 20 },
      "metrics.view_count": { $gte: 50 }
    }
  },
  {
    $sort: { "metrics.like_count": -1 }
  },
  {
    $limit: 10
  },
  {
    $project: {
      _id: 1,
      author_id: 1,
      style: 1,
      hashtags: 1,
      "metrics.view_count": 1,
      "metrics.like_count": 1
    }
  }
])
```

## Question 3 — Venue engagement

Given the `venues` collection:

```json
{
  "_id": "restaurant_6317637",
  "name": "Le Petit Souffle",
  "city": "Makati City",
  "category": "French",
  "cuisines": ["French", "Japanese", "Desserts"],
  "rating": {
    "aggregate_rating": 4.8,
    "votes": 314
  }
}
```

Write a MongoDB query that retrieves venues that:
- belong to city `"Makati City"`
- have an aggregate rating greater than or equal to `4.5`
- have at least `200` votes

Return only:
- `name`
- `city`
- `category`
- `cuisines`
- `rating.aggregate_rating`
- `rating.votes`

Sort by `rating.votes` in descending order.

### Answer

```javascript
db.venues.aggregate([
  {
    $match: {
      city: "Makati City",
      "rating.aggregate_rating": { $gte: 4.5 },
      "rating.votes": { $gte: 200 }
    }
  },
  {
    $project: {
      _id: 0,
      name: 1,
      city: 1,
      category: 1,
      cuisines: 1,
      "rating.aggregate_rating": 1,
      "rating.votes": 1
    }
  },
  {
    $sort: { "rating.votes": -1 }
  }
])
```

## Question 4 — Relationship analysis

Given the `relationships` collection:

```json
{
  "_id": "relationship_001",
  "type": "like",
  "source_user_id": "user_003",
  "target_type": "content",
  "target_id": "content_045",
  "created_at": "2026-05-12T09:00:00Z"
}
```

Write a MongoDB query that finds the users who created the most `like` relationships toward content in the last 30 days.

The result must include:
- `source_user_id`
- the number of likes created

Sort the users by number of likes in descending order and return only the top 5.

### Answer

```javascript
db.relationships.aggregate([
  {
    $match: {
      type: "like",
      target_type: "content",
      created_at: {
        $gte: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)
      }
    }
  },
  {
    $group: {
      _id: "$source_user_id",
      total_likes: { $sum: 1 }
    }
  },
  {
    $sort: {
      total_likes: -1
    }
  },
  {
    $limit: 5
  },
  {
    $project: {
      _id: 0,
      source_user_id: "$_id",
      total_likes: 1
    }
  }
])
```

## Question 5 — Content overlap in MongoDB

Given the `content` collection:

```json
{
  "_id": "content_245",
  "type": "post",
  "author_id": "user_020",
  "style": "travel",
  "category": "travel",
  "hashtags": ["city", "museum", "culture", "walk"],
  "metrics": {
    "view_count": 88,
    "like_count": 17,
    "comment_count": 4
  }
}
```

Write a MongoDB query that finds all `post` documents that:
- have `style = "travel"`
- contain the hashtag `"culture"`
- have at least `10` likes

Return only:
- `_id`
- `author_id`
- `style`
- `category`
- `hashtags`
- `metrics.like_count`

Sort the results by `metrics.like_count` in descending order and return only the top 8 documents.

### Answer

```javascript
db.content.aggregate([
  {
    $match: {
      type: "post",
      style: "travel",
      hashtags: "culture",
      "metrics.like_count": { $gte: 10 }
    }
  },
  {
    $sort: { "metrics.like_count": -1 }
  },
  {
    $limit: 8
  },
  {
    $project: {
      _id: 1,
      author_id: 1,
      style: 1,
      category: 1,
      hashtags: 1,
      "metrics.like_count": 1
    }
  }
])
```
