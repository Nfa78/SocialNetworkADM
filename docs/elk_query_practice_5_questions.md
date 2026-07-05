# Elasticsearch / ELK Query Practice

This file contains **5 practice questions** and **5 complete answers** covering the most common Elasticsearch Query DSL patterns used in exam-style questions.

> In the ELK stack, the actual search engine is **Elasticsearch**. So when we say “ELK queries”, we usually mean **Elasticsearch Query DSL**.

---

## Basic Mapping Used in These Questions

Assume we have this index:

```http
products
```

And this mapping:

```json
{
  "mappings": {
    "properties": {
      "name": {
        "type": "text"
      },
      "description": {
        "type": "text"
      },
      "category": {
        "type": "keyword"
      },
      "brand": {
        "type": "keyword"
      },
      "tags": {
        "type": "keyword"
      },
      "price": {
        "type": "float"
      },
      "rating": {
        "type": "float"
      },
      "in_stock": {
        "type": "boolean"
      },
      "created_at": {
        "type": "date"
      }
    }
  }
}
```

---

## Quick Cheat Sheet

| Need | Query / Feature |
|---|---|
| Search words in a `text` field | `match` |
| Search exact phrase in a `text` field | `match_phrase` |
| Search same text in many fields | `multi_match` |
| Exact value on `keyword` or `boolean` | `term` |
| Field is one of many exact values | `terms` |
| Numeric/date comparison | `range` |
| Field exists | `exists` |
| Combine conditions | `bool` |
| AND | `must` or `filter` |
| OR | `should` + `minimum_should_match` |
| NOT | `must_not` |
| Projection / returned fields | `_source` |
| Sorting | `sort` |
| Limit results | `size` |
| Pagination | `from` + `size` |
| Grouping | `aggs` with `terms`, `date_histogram`, etc. |

---

## Filter and Group Examples

### Filter example

Use `filter` inside a `bool` query when the condition is exact and does not need relevance scoring.

This example returns products that are in stock, in the `electronics` category, and cost at most `900`.

```json
GET products/_search
{
  "query": {
    "bool": {
      "filter": [
        {
          "term": {
            "in_stock": true
          }
        },
        {
          "term": {
            "category": "electronics"
          }
        },
        {
          "range": {
            "price": {
              "lte": 900
            }
          }
        }
      ]
    }
  }
}
```

SQL-style idea:

```sql
WHERE in_stock = true
  AND category = 'electronics'
  AND price <= 900
```

### Group example

Use `aggs` for grouping. A `terms` aggregation is the most common way to group by an exact-value field.

This example groups products by `category` and counts how many products are in each category.

```json
GET products/_search
{
  "size": 0,
  "aggs": {
    "products_by_category": {
      "terms": {
        "field": "category"
      }
    }
  }
}
```

SQL-style idea:

```sql
SELECT category, COUNT(*)
FROM products
GROUP BY category;
```

### Filter first, then group

Filtering and grouping are often used together. The `query` filters the documents first, then `aggs` groups only the matching documents.

This example filters to in-stock electronics products, then groups them by `brand`.

```json
GET products/_search
{
  "size": 0,
  "query": {
    "bool": {
      "filter": [
        {
          "term": {
            "in_stock": true
          }
        },
        {
          "term": {
            "category": "electronics"
          }
        }
      ]
    }
  },
  "aggs": {
    "products_by_brand": {
      "terms": {
        "field": "brand"
      },
      "aggs": {
        "average_price": {
          "avg": {
            "field": "price"
          }
        }
      }
    }
  }
}
```

SQL-style idea:

```sql
SELECT brand, COUNT(*), AVG(price)
FROM products
WHERE in_stock = true
  AND category = 'electronics'
GROUP BY brand;
```

---

# Question 1 — Basic Search with AND Conditions

Write a query to retrieve products where:

1. `name` contains the word `laptop`
2. `category` is exactly `electronics`
3. `price` is less than or equal to `900`
4. `in_stock` is `true`

---

## Answer 1

```json
GET products/_search
{
  "query": {
    "bool": {
      "must": [
        {
          "match": {
            "name": "laptop"
          }
        },
        {
          "term": {
            "category": "electronics"
          }
        },
        {
          "range": {
            "price": {
              "lte": 900
            }
          }
        },
        {
          "term": {
            "in_stock": true
          }
        }
      ]
    }
  }
}
```

### Concepts used

- `match` because `name` is a `text` field.
- `term` because `category` is a `keyword` field.
- `range` because `price` is numeric.
- `term` because `in_stock` is boolean.
- `must` because all conditions must be true.

---

# Question 2 — Phrase Search Across Multiple Fields + Projection + Sorting

Write a query to retrieve products where:

1. the exact phrase `wireless headphones` appears in either `name` or `description`
2. `rating` is greater than or equal to `4.0`
3. return only `name`, `brand`, `price`, and `rating`
4. return only the first `10` results
5. sort results by `price` ascending

---

## Answer 2

```json
GET products/_search
{
  "_source": ["name", "brand", "price", "rating"],
  "size": 10,
  "sort": [
    {
      "price": {
        "order": "asc"
      }
    }
  ],
  "query": {
    "bool": {
      "must": [
        {
          "multi_match": {
            "query": "wireless headphones",
            "fields": ["name", "description"],
            "type": "phrase"
          }
        },
        {
          "range": {
            "rating": {
              "gte": 4.0
            }
          }
        }
      ]
    }
  }
}
```

### Concepts used

- `multi_match` searches the same query in multiple fields.
- `type: "phrase"` means exact phrase search.
- `_source` is projection: it controls which fields are returned.
- `size` limits the number of returned results.
- `sort` orders the results.

---

# Question 3 — OR, NOT, and Exists

Write a query to retrieve products where:

1. `category` is exactly `electronics` OR `gaming`
2. `description` exists
3. `brand` is NOT `Unknown`

---

## Answer 3

```json
GET products/_search
{
  "query": {
    "bool": {
      "filter": [
        {
          "bool": {
            "should": [
              {
                "term": {
                  "category": "electronics"
                }
              },
              {
                "term": {
                  "category": "gaming"
                }
              }
            ],
            "minimum_should_match": 1
          }
        },
        {
          "exists": {
            "field": "description"
          }
        }
      ],
      "must_not": [
        {
          "term": {
            "brand": "Unknown"
          }
        }
      ]
    }
  }
}
```

### Concepts used

- `should` represents OR.
- `minimum_should_match: 1` means at least one OR condition must match.
- `exists` checks whether the field is present.
- `must_not` represents NOT.
- `filter` is often used for exact conditions that do not need scoring.

### Shorter alternative for the OR condition

Because both OR conditions are on the same field, we can also use `terms`:

```json
{
  "terms": {
    "category": ["electronics", "gaming"]
  }
}
```

---

# Question 4 — Grouping with Aggregations

Write a query to answer this question:

> For products that are in stock, group them by `category` and calculate the average, minimum, and maximum `price` for each category.

Do not return actual product documents, only the aggregation result.

---

## Answer 4

```json
GET products/_search
{
  "size": 0,
  "query": {
    "term": {
      "in_stock": true
    }
  },
  "aggs": {
    "products_by_category": {
      "terms": {
        "field": "category"
      },
      "aggs": {
        "average_price": {
          "avg": {
            "field": "price"
          }
        },
        "minimum_price": {
          "min": {
            "field": "price"
          }
        },
        "maximum_price": {
          "max": {
            "field": "price"
          }
        }
      }
    }
  }
}
```

### Concepts used

- `size: 0` means do not return documents, only aggregation results.
- `aggs` is used for grouping/statistics.
- `terms` aggregation groups by exact values, similar to SQL `GROUP BY`.
- `avg`, `min`, and `max` are metric aggregations.
- `doc_count` in the result is similar to `COUNT(*)`.

---

# Question 5 — Date Range + Date Histogram + Pagination

Write a query to retrieve products where:

1. `created_at` is from `2026-01-01` onward
2. `rating` is greater than or equal to `4.0`
3. return only `name`, `category`, `rating`, and `created_at`
4. return page 2, assuming each page has 10 results
5. sort newest products first
6. also group matching products by month using `created_at`

---

## Answer 5

```json
GET products/_search
{
  "_source": ["name", "category", "rating", "created_at"],
  "from": 10,
  "size": 10,
  "sort": [
    {
      "created_at": {
        "order": "desc"
      }
    }
  ],
  "query": {
    "bool": {
      "filter": [
        {
          "range": {
            "created_at": {
              "gte": "2026-01-01"
            }
          }
        },
        {
          "range": {
            "rating": {
              "gte": 4.0
            }
          }
        }
      ]
    }
  },
  "aggs": {
    "products_per_month": {
      "date_histogram": {
        "field": "created_at",
        "calendar_interval": "month"
      }
    }
  }
}
```

### Concepts used

- Date comparisons also use `range`.
- Date values are strings, so they use quotes.
- `from: 10` and `size: 10` means page 2 if page 1 starts at `from: 0`.
- `_source` is projection.
- `sort` orders by date descending.
- `date_histogram` groups documents by time intervals.

---

# Final Syntax Reminders

## Quotes

```text
Keys                 -> quoted
String values         -> quoted
Numbers               -> not quoted
Booleans true/false   -> not quoted
null                  -> not quoted
Arrays []             -> not quoted as a whole
Objects {}            -> not quoted as a whole
```

Examples:

```json
{
  "term": {
    "category": "electronics"
  }
}
```

```json
{
  "range": {
    "price": {
      "lte": 900
    }
  }
}
```

```json
{
  "term": {
    "in_stock": true
  }
}
```

---

# Main Template to Memorize

```json
GET index_name/_search
{
  "query": {
    "bool": {
      "must": [
        {
          "QUERY_TYPE": {
            "field": "value"
          }
        }
      ],
      "filter": [
        {
          "QUERY_TYPE": {
            "field": "value"
          }
        }
      ],
      "should": [
        {
          "QUERY_TYPE": {
            "field": "value"
          }
        }
      ],
      "must_not": [
        {
          "QUERY_TYPE": {
            "field": "value"
          }
        }
      ]
    }
  }
}
```
