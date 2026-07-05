# InfluxDB Flux Query Practice

This file contains **5 practice questions** and **5 complete answers** covering the most common InfluxDB **Flux** query patterns used in exam-style questions.

The focus is on fast learning: each question has a complete query, explanation, and common syntax notes.

---

## Basic Data Model Used in These Questions

Assume the data is stored in InfluxDB with:

```text
bucket: IoT
measurement: home
fields: temp, hum
tag: room
```

Example data conceptually looks like this:

| _time | _measurement | room | _field | _value |
|---|---|---|---|---|
| 2026-06-21T10:00:00Z | home | kitchen | temp | 24.5 |
| 2026-06-21T10:00:00Z | home | kitchen | hum | 55 |
| 2026-06-21T10:00:00Z | home | bedroom | temp | 22.1 |
| 2026-06-21T10:00:00Z | home | bedroom | hum | 60 |

---

## Flux Mental Model

Most Flux queries follow this pipeline:

```flux
from(bucket: "bucket_name")
  |> range(start: -time)
  |> filter(fn: (r) => condition)
  |> transformation()
```

Important built-in columns:

| Column | Meaning |
|---|---|
| `_time` | timestamp of the point |
| `_measurement` | measurement name, like a table name |
| `_field` | field name, for example `temp` or `hum` |
| `_value` | actual numeric/string value of the field |
| `room` | tag column in this example |

---

## Quick Cheat Sheet

| Need | Flux function / syntax |
|---|---|
| Select bucket | `from(bucket: "IoT")` |
| Select time range | `range(start: -2h)` |
| Filter measurement | `filter(fn: (r) => r._measurement == "home")` |
| Filter field | `filter(fn: (r) => r._field == "temp")` |
| Filter tag | `filter(fn: (r) => r.room == "kitchen")` |
| Filter value | `filter(fn: (r) => r._value > 25.0)` |
| Average | `mean()` |
| Minimum | `min()` |
| Maximum | `max()` |
| Count | `count()` |
| Latest value | `last()` |
| Group by tag | `group(columns: ["room"])` |
| Windowed aggregation | `aggregateWindow(every: 10m, fn: mean)` |
| Sort | `sort(columns: ["_time"], desc: true)` |
| Limit rows | `limit(n: 10)` |
| Select columns | `keep(columns: ["_time", "room", "_value"])` |
| Convert fields into columns | `pivot(...)` |

---

# Question 1 — Average Temperature Per Room Over the Last 2 Hours

Write a Flux query to compute the **average temperature per room** over the last **2 hours**.

Use:

```text
bucket: IoT
measurement: home
field: temp
tag: room
```

---

## Answer 1

```flux
from(bucket: "IoT")
  |> range(start: -2h)
  |> filter(fn: (r) => r._measurement == "home")
  |> filter(fn: (r) => r._field == "temp")
  |> group(columns: ["room"])
  |> mean()
```

### Explanation

```flux
from(bucket: "IoT")
```

Selects the bucket.

```flux
range(start: -2h)
```

Keeps only data from the last 2 hours.

```flux
filter(fn: (r) => r._measurement == "home")
```

Keeps only rows from the `home` measurement.

```flux
filter(fn: (r) => r._field == "temp")
```

Keeps only temperature values.

```flux
group(columns: ["room"])
```

Groups data by room.

```flux
mean()
```

Computes the average `_value` for each room.

### SQL-like idea

```sql
SELECT room, AVG(temp)
FROM home
WHERE time >= now() - 2 hours
GROUP BY room;
```

---

# Question 2 — Average Temperature Every 10 Minutes Per Room

Write a Flux query to compute the **average temperature every 10 minutes per room** over the last **2 hours**.

This is different from Question 1 because now we want a time series of averages, not one average per room.

---

## Answer 2

```flux
from(bucket: "IoT")
  |> range(start: -2h)
  |> filter(fn: (r) => r._measurement == "home")
  |> filter(fn: (r) => r._field == "temp")
  |> group(columns: ["room"])
  |> aggregateWindow(every: 10m, fn: mean, createEmpty: false)
```

### Explanation

```flux
group(columns: ["room"])
```

Keeps each room separate.

```flux
aggregateWindow(every: 10m, fn: mean, createEmpty: false)
```

Divides time into 10-minute windows and calculates the average temperature in each window.

`createEmpty: false` avoids returning empty time windows with no data.

### When to use `mean()` vs `aggregateWindow()`

Use this:

```flux
mean()
```

when you want **one final average**.

Use this:

```flux
aggregateWindow(every: 10m, fn: mean)
```

when you want **averages over repeated time windows**.

---

# Question 3 — Latest Humidity Value in One Room

Write a Flux query to retrieve the **latest humidity value** measured in the `kitchen` over the last **24 hours**.

Return only:

```text
_time, room, _field, _value
```

---

## Answer 3

```flux
from(bucket: "IoT")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "home")
  |> filter(fn: (r) => r._field == "hum")
  |> filter(fn: (r) => r.room == "kitchen")
  |> last()
  |> keep(columns: ["_time", "room", "_field", "_value"])
```

### Explanation

```flux
filter(fn: (r) => r._field == "hum")
```

Selects humidity readings.

```flux
filter(fn: (r) => r.room == "kitchen")
```

Selects only the kitchen. `room` is a tag.

```flux
last()
```

Returns the latest point in the selected time range.

```flux
keep(columns: ["_time", "room", "_field", "_value"])
```

Acts like projection: it keeps only the requested columns.

### SQL-like idea

```sql
SELECT time, room, hum
FROM home
WHERE room = 'kitchen'
ORDER BY time DESC
LIMIT 1;
```

---

# Question 4 — Retrieve Temperature and Humidity Together Using Pivot

Write a Flux query to retrieve both `temp` and `hum` for the `bedroom` over the last **1 hour**, and convert them into separate columns.

The output should look conceptually like:

| _time | room | temp | hum |
|---|---|---|---|
| 10:00 | bedroom | 22.4 | 58 |
| 10:05 | bedroom | 22.5 | 57 |

---

## Answer 4

```flux
from(bucket: "IoT")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "home")
  |> filter(fn: (r) => r.room == "bedroom")
  |> filter(fn: (r) => r._field == "temp" or r._field == "hum")
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> keep(columns: ["_time", "room", "temp", "hum"])
```

### Explanation

In InfluxDB, fields are usually stored vertically:

| _time | _field | _value |
|---|---|---|
| 10:00 | temp | 22.4 |
| 10:00 | hum | 58 |

`pivot()` converts this into a wider table:

| _time | temp | hum |
|---|---|---|
| 10:00 | 22.4 | 58 |

The key part is:

```flux
pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
```

Meaning:

```text
Each time becomes a row.
Each field name becomes a column.
The value comes from _value.
```

---

# Question 5 — Count High Temperature Readings Per Room

Write a Flux query to count how many temperature readings were greater than `28.0` in each room over the last **24 hours**.

Use:

```text
measurement: home
field: temp
threshold: _value > 28.0
grouping tag: room
```

---

## Answer 5

```flux
from(bucket: "IoT")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "home")
  |> filter(fn: (r) => r._field == "temp")
  |> filter(fn: (r) => r._value > 28.0)
  |> group(columns: ["room"])
  |> count()
```

### Explanation

```flux
filter(fn: (r) => r._value > 28.0)
```

Keeps only temperature readings above 28.0.

```flux
group(columns: ["room"])
```

Separates the data by room.

```flux
count()
```

Counts how many rows are left in each room group.

### SQL-like idea

```sql
SELECT room, COUNT(*)
FROM home
WHERE temp > 28.0
AND time >= now() - 24 hours
GROUP BY room;
```

---

# Common Flux Syntax Rules

## 1. Strings use quotes

```flux
r._measurement == "home"
r._field == "temp"
r.room == "kitchen"
```

## 2. Durations do not use quotes

Correct:

```flux
range(start: -2h)
```

Wrong:

```flux
range(start: "-2h")
```

## 3. Numbers do not use quotes

Correct:

```flux
r._value > 28.0
```

Wrong:

```flux
r._value > "28.0"
```

## 4. Booleans do not use quotes

```flux
true
false
```

## 5. Every pipeline step uses `|>`

```flux
from(bucket: "IoT")
  |> range(start: -2h)
  |> filter(fn: (r) => r._field == "temp")
  |> mean()
```

## 6. Filter functions usually look like this

```flux
filter(fn: (r) => r.columnName == "value")
```

Examples:

```flux
filter(fn: (r) => r._measurement == "home")
filter(fn: (r) => r._field == "temp")
filter(fn: (r) => r.room == "kitchen")
filter(fn: (r) => r._value > 25.0)
```

---

# Most Important Template to Memorize

```flux
from(bucket: "BUCKET_NAME")
  |> range(start: -TIME_RANGE)
  |> filter(fn: (r) => r._measurement == "MEASUREMENT_NAME")
  |> filter(fn: (r) => r._field == "FIELD_NAME")
  |> filter(fn: (r) => r.TAG_NAME == "TAG_VALUE")
  |> group(columns: ["TAG_NAME"])
  |> AGGREGATION_FUNCTION()
```

Example:

```flux
from(bucket: "IoT")
  |> range(start: -2h)
  |> filter(fn: (r) => r._measurement == "home")
  |> filter(fn: (r) => r._field == "temp")
  |> group(columns: ["room"])
  |> mean()
```

---

# Final Exam Tips

1. Always start with `from(bucket: "...")`.
2. Always add a `range(...)`; Flux usually requires a time range for queries.
3. Filter `_measurement` to select the measurement.
4. Filter `_field` to select the field.
5. Filter tags directly, like `r.room == "kitchen"`.
6. Use `_value` for numeric comparisons.
7. Use `group(columns: [...])` before aggregation if the question asks “per room”, “per device”, or “per host”.
8. Use `aggregateWindow(...)` when the question says “every 5 minutes”, “per hour”, “daily average”, etc.
9. Use `pivot(...)` when the question wants multiple fields as columns.
10. Use `keep(...)` when the question asks to return only specific columns.

