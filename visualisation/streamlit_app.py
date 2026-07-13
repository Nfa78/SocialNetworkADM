from __future__ import annotations

from datetime import UTC, date, datetime, time
from time import perf_counter
from typing import Any, Callable

import pandas as pd
import streamlit as st

from charts import bar_chart, donut_chart, line_chart, map_chart, scatter_chart
from data_access import check_mongo_connection, check_neo4j_connection, get_mongo_database, get_neo4j_driver
from mongo_queries import (
    DashboardFilters,
    FilterOption,
    content_by_style,
    content_by_type,
    content_over_time,
    duration_by_source,
    get_date_bounds,
    get_filter_options,
    get_overview_metrics,
    hydrate_content_candidates,
    most_active_users,
    most_engaged_venues,
    most_engaged_users,
    recommendations_from_engaged_content,
    recommendations_from_liked_content,
    recommendations_from_similar_user_likes,
    sentiment_distribution,
    sentiment_over_time,
    top_content,
    top_cuisines,
    top_hashtags,
    top_viewed_content,
    users_by_city,
    venue_map_points,
    venue_price_rating_points,
    venue_rating_by_city,
    venues_by_city,
    viral_content,
    viral_interactions_over_time,
    virality_baseline,
    views_by_source,
    views_over_time,
)
from neo4j_queries import (
    content_from_followed_authors,
    content_similarity,
    recommendations_from_liked_content_graph,
    recommendations_from_similar_user_likes_graph,
    recommendations_from_viewed_content_graph,
    top_creators,
    top_followed_users,
    top_followed_venues,
    top_liked_content,
    top_viewed_content_graph,
)


st.set_page_config(page_title="Social Analytics Dashboard", layout="wide")

CACHE_TTL_SECONDS = 300
CONNECTION_CHECK_TTL_SECONDS = 30
RECOMMENDATION_LIMIT_OPTIONS = [5, 10, 15, 25, 50]
SLOW_QUERY_LOG_SECONDS = 0.5
VIRALITY_CONTENT_TYPE_OPTIONS = ["post", "comment"]
VIRALITY_LIMIT_OPTIONS = [10, 25, 50, 100]
DASHBOARD_PAGES = [
    "Overview",
    "Content",
    "Engagement",
    "Virality",
    "User Feed",
    "Venues / Location",
    "Relations",
]
FILTER_WIDGET_KEYS = (
    "filter_date_range",
    "filter_city",
    "filter_content_type",
    "filter_style",
    "filter_category",
    "filter_sentiment",
    "filter_interaction_source",
)

MONGO_QUERY_FUNCTIONS: dict[str, Callable[..., Any]] = {
    "content_by_style": content_by_style,
    "content_by_type": content_by_type,
    "content_over_time": content_over_time,
    "duration_by_source": duration_by_source,
    "get_overview_metrics": get_overview_metrics,
    "most_active_users": most_active_users,
    "most_engaged_venues": most_engaged_venues,
    "most_engaged_users": most_engaged_users,
    "sentiment_distribution": sentiment_distribution,
    "sentiment_over_time": sentiment_over_time,
    "top_content": top_content,
    "top_cuisines": top_cuisines,
    "top_hashtags": top_hashtags,
    "top_viewed_content": top_viewed_content,
    "users_by_city": users_by_city,
    "venue_map_points": venue_map_points,
    "venue_price_rating_points": venue_price_rating_points,
    "venue_rating_by_city": venue_rating_by_city,
    "venues_by_city": venues_by_city,
    "viral_content": viral_content,
    "viral_interactions_over_time": viral_interactions_over_time,
    "virality_baseline": virality_baseline,
    "views_by_source": views_by_source,
    "views_over_time": views_over_time,
}

RECOMMENDATION_QUERY_FUNCTIONS: dict[str, Callable[..., list[dict]]] = {
    "recommendations_from_liked_content": recommendations_from_liked_content,
    "recommendations_from_engaged_content": recommendations_from_engaged_content,
    "recommendations_from_similar_user_likes": recommendations_from_similar_user_likes,
}

NEO4J_QUERY_FUNCTIONS: dict[str, Callable[..., list[dict]]] = {
    "content_similarity": content_similarity,
    "top_creators": top_creators,
    "top_followed_users": top_followed_users,
    "top_followed_venues": top_followed_venues,
    "top_liked_content": top_liked_content,
    "top_viewed_content_graph": top_viewed_content_graph,
}

GRAPH_RECOMMENDATION_QUERY_FUNCTIONS: dict[str, Callable[..., list[dict]]] = {
    "content_from_followed_authors": content_from_followed_authors,
    "recommendations_from_liked_content_graph": recommendations_from_liked_content_graph,
    "recommendations_from_similar_user_likes_graph": recommendations_from_similar_user_likes_graph,
    "recommendations_from_viewed_content_graph": recommendations_from_viewed_content_graph,
}


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SECONDS)
def cached_date_bounds(database_name: str, _database: Any) -> tuple[datetime | None, datetime | None]:
    started_at = perf_counter()
    try:
        return get_date_bounds(_database)
    finally:
        log_query_duration("mongo", "get_date_bounds", started_at)


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SECONDS)
def cached_filter_options(database_name: str, _database: Any) -> dict[str, list[FilterOption]]:
    started_at = perf_counter()
    try:
        return get_filter_options(_database)
    finally:
        log_query_duration("mongo", "get_filter_options", started_at)


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SECONDS)
def cached_mongo_query(
    query_name: str,
    database_name: str,
    _database: Any,
    filters: DashboardFilters,
    limit: int | None = None,
    **kwargs: Any,
) -> Any:
    started_at = perf_counter()
    try:
        query = MONGO_QUERY_FUNCTIONS[query_name]
        if limit is None:
            return query(_database, filters, **kwargs)
        return query(_database, filters, limit=limit, **kwargs)
    finally:
        log_query_duration("mongo", query_name, started_at)


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SECONDS)
def cached_recommendations(
    query_name: str,
    database_name: str,
    _database: Any,
    filters: DashboardFilters,
    user_ids: tuple[Any, ...],
    venue_ids: tuple[Any, ...],
    limit: int,
) -> list[dict]:
    started_at = perf_counter()
    try:
        query = RECOMMENDATION_QUERY_FUNCTIONS[query_name]
        return query(_database, filters, list(user_ids), list(venue_ids), limit=limit)
    finally:
        log_query_duration("recommendation", query_name, started_at)


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SECONDS)
def cached_neo4j_query(query_name: str, _driver: Any, filters: DashboardFilters, limit: int) -> list[dict]:
    started_at = perf_counter()
    try:
        query = NEO4J_QUERY_FUNCTIONS[query_name]
        return query(_driver, filters, limit=limit)
    finally:
        log_query_duration("neo4j", query_name, started_at)


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SECONDS)
def cached_graph_recommendations(
    query_name: str,
    database_name: str,
    _database: Any,
    _driver: Any,
    filters: DashboardFilters,
    user_ids: tuple[Any, ...],
    venue_ids: tuple[Any, ...],
    limit: int,
) -> list[dict]:
    started_at = perf_counter()
    try:
        query = GRAPH_RECOMMENDATION_QUERY_FUNCTIONS[query_name]
        graph_rows = query(_driver, filters, list(user_ids), limit=max(limit * 5, limit))
        return hydrate_content_candidates(_database, filters, graph_rows, list(venue_ids), limit=limit)
    finally:
        log_query_duration("graph_recommendation", query_name, started_at)


@st.cache_data(show_spinner=False, ttl=CONNECTION_CHECK_TTL_SECONDS)
def cached_mongo_connection_check(database_name: str, _database: Any) -> None:
    check_mongo_connection(_database)


@st.cache_data(show_spinner=False, ttl=CONNECTION_CHECK_TTL_SECONDS)
def cached_neo4j_connection_check(_driver: Any) -> None:
    check_neo4j_connection(_driver)


def rows_frame(rows: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    for column in ("date", "created_at", "first_interaction_at", "last_interaction_at", "last_seen_at", "latest_created_at", "last_viewed_at"):
        if column in frame.columns:
            frame[column] = pd.to_datetime(frame[column])
    return frame


def log_query_duration(query_type: str, query_name: str, started_at: float) -> None:
    elapsed = perf_counter() - started_at
    if elapsed >= SLOW_QUERY_LOG_SECONDS:
        print(f"[streamlit-perf] {query_type} {query_name} took {elapsed:.2f}s")


def select_dashboard_page() -> str:
    with st.sidebar:
        st.header("Navigation")
        return st.radio("Page", DASHBOARD_PAGES, label_visibility="collapsed")


def optional_select(label: str, options: list[FilterOption], key: str) -> str | None:
    labels = {option.value: f"{option.value} [{format_int(option.relevance)}]" for option in options}
    values = [option.value for option in options]

    selected = st.sidebar.selectbox(
        label,
        [None, *values],
        format_func=lambda value: "All" if value is None else labels.get(value, str(value)),
        key=key,
    )
    return selected


def selected_date_bounds(min_value: datetime | None, max_value: datetime | None) -> tuple[datetime, datetime]:
    today = date.today()
    min_day = min_value.date() if min_value else today
    max_day = max_value.date() if max_value else today
    if min_day > max_day:
        min_day = max_day

    selected = st.sidebar.date_input(
        "Date range",
        value=(min_day, max_day),
        min_value=min_day,
        max_value=max_day,
        key="filter_date_range",
    )
    if isinstance(selected, tuple):
        if len(selected) == 2:
            start_day, end_day = selected
        elif len(selected) == 1:
            start_day = selected[0]
            end_day = max(today, start_day)
        else:
            start_day = end_day = max_day
    else:
        start_day = end_day = selected

    start = datetime.combine(start_day, time.min, tzinfo=UTC)
    end = datetime.combine(end_day, time.max, tzinfo=UTC)
    return start, end


def build_filters() -> DashboardFilters:
    database = st.session_state.database

    with st.sidebar:
        st.header("Filters")
        action_columns = st.columns(2)
        if action_columns[0].button("Refresh data", use_container_width=True):
            st.cache_data.clear()
        if action_columns[1].button("Reset filters", use_container_width=True):
            for key in FILTER_WIDGET_KEYS:
                st.session_state.pop(key, None)
            st.rerun()

    min_date, max_date = cached_date_bounds(database.name, database)
    options = cached_filter_options(database.name, database)

    with st.sidebar:
        start, end = selected_date_bounds(min_date, max_date)
        city = optional_select("City", options["cities"], key="filter_city")
        content_type = optional_select("Content type", options["content_types"], key="filter_content_type")
        style = optional_select("Content style", options["styles"], key="filter_style")
        category = optional_select("Content category", options["categories"], key="filter_category")
        sentiment = optional_select("Sentiment", options["sentiments"], key="filter_sentiment")
        interaction_source = optional_select(
            "Interaction source",
            options["interaction_sources"],
            key="filter_interaction_source",
        )

    return DashboardFilters(
        start=start,
        end=end,
        city=city,
        content_type=content_type,
        style=style,
        category=category,
        sentiment=sentiment,
        interaction_source=interaction_source,
    )


def format_int(value: object) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "0"


def score_sum(*values: object) -> int:
    total = 0
    for value in values:
        try:
            total += int(value or 0)
        except (TypeError, ValueError):
            continue
    return total


def format_seconds(milliseconds: object) -> str:
    if milliseconds is None:
        return "n/a"
    try:
        return f"{float(milliseconds) / 1000:.1f}s"
    except (TypeError, ValueError):
        return "n/a"


def format_rating(value: object) -> str:
    if value is None:
        return "n/a"
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "n/a"


def format_decimal(value: object, suffix: str = "", decimals: int = 2) -> str:
    if value is None:
        return "n/a"
    try:
        return f"{float(value):.{decimals}f}{suffix}"
    except (TypeError, ValueError):
        return "n/a"


def add_duration_seconds(frame: pd.DataFrame) -> pd.DataFrame:
    if "avg_duration_ms" in frame.columns:
        frame = frame.copy()
        frame["avg_duration_s"] = (pd.to_numeric(frame["avg_duration_ms"], errors="coerce") / 1000).round(2)
    return frame


def show_table(title: str, frame: pd.DataFrame, height: int = 360) -> None:
    st.subheader(title)
    if frame.empty:
        st.info("No rows for the selected filters.")
        return
    st.dataframe(frame, use_container_width=True, hide_index=True, height=height)


def user_option_label(user: dict[str, object]) -> str:
    user_id = str(user.get("user_id") or "")
    username = str(user.get("username") or user.get("display_name") or user_id)
    city = user.get("city")
    engaged_content_count = format_int(user.get("engaged_content_count"))
    views = format_int(user.get("views"))
    relevance = score_sum(user.get("views"), user.get("engaged_content_count"))

    details = [f"{engaged_content_count} content", f"{views} views"]
    if city:
        details.insert(0, str(city))

    return f"{username} [{format_int(relevance)}] ({' | '.join(details)})"


def venue_option_label(venue: dict[str, object]) -> str:
    venue_id = str(venue.get("venue_id") or "")
    name = str(venue.get("name") or venue_id)
    city = venue.get("city")
    engaged_content_count = format_int(venue.get("engaged_content_count"))
    views = format_int(venue.get("views"))
    viewer_count = format_int(venue.get("viewer_count"))
    relevance = score_sum(venue.get("views"), venue.get("engaged_content_count"), venue.get("viewer_count"))

    details = [f"{engaged_content_count} content", f"{views} views", f"{viewer_count} viewers"]
    if city:
        details.insert(0, str(city))

    return f"{name} [{format_int(relevance)}] ({' | '.join(details)})"


def selected_user_frame(frame: pd.DataFrame, user_ids: list[object]) -> pd.DataFrame:
    if frame.empty or "user_id" not in frame.columns:
        return pd.DataFrame()

    selected = frame[frame["user_id"].isin(user_ids)].copy()
    columns = [
        "user_id",
        "username",
        "display_name",
        "city",
        "engaged_content_count",
        "views",
        "avg_duration_s",
        "last_seen_at",
    ]
    return selected[[column for column in columns if column in selected.columns]]


def selected_venue_frame(frame: pd.DataFrame, venue_ids: list[object]) -> pd.DataFrame:
    if frame.empty or "venue_id" not in frame.columns:
        return pd.DataFrame()

    selected = frame[frame["venue_id"].isin(venue_ids)].copy()
    columns = [
        "venue_id",
        "name",
        "city",
        "category",
        "rating",
        "engaged_content_count",
        "viewer_count",
        "views",
        "avg_duration_s",
        "last_seen_at",
    ]
    return selected[[column for column in columns if column in selected.columns]]


def format_list_cell(value: object) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value[:6] if item is not None)
    return "" if value is None else str(value)


def recommendation_frame(rows: list[dict]) -> pd.DataFrame:
    frame = rows_frame(rows)
    if frame.empty:
        return frame

    for column in ("matched_hashtags",):
        if column in frame.columns:
            frame[column] = frame[column].apply(format_list_cell)

    columns = [
        "content_id",
        "recommendation_source",
        "score",
        "similar_user_count",
        "type",
        "style",
        "category",
        "sentiment",
        "venue_name",
        "city",
        "views",
        "likes",
        "comments",
        "matched_hashtags",
        "created_at",
        "text",
    ]
    return frame[[column for column in columns if column in frame.columns]]


def virality_frame(rows: list[dict]) -> pd.DataFrame:
    frame = add_duration_seconds(rows_frame(rows))
    if frame.empty:
        return frame

    for column in ("avg_interactions", "viral_threshold", "avg_unique_viewers", "avg_interactions_for_type", "virality_ratio"):
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce").round(2)

    columns = [
        "content_id",
        "type",
        "interaction_count",
        "virality_ratio",
        "avg_interactions_for_type",
        "viral_threshold",
        "unique_viewer_count",
        "avg_duration_s",
        "style",
        "category",
        "sentiment",
        "author_id",
        "created_at",
        "last_interaction_at",
        "text",
    ]
    return frame[[column for column in columns if column in frame.columns]]


def render_recommendation_section(title: str, key: str, fetch_rows: Callable[[int], list[dict]]) -> None:
    title_column, limit_column = st.columns([3, 1])
    with title_column:
        st.subheader(title)
    with limit_column:
        limit = st.selectbox(
            "Posts",
            options=RECOMMENDATION_LIMIT_OPTIONS,
            index=RECOMMENDATION_LIMIT_OPTIONS.index(15),
            key=f"{key}_limit",
        )

    frame = recommendation_frame(fetch_rows(limit))
    if frame.empty:
        st.info("No recommendations found for this selection.")
        return

    st.dataframe(frame, use_container_width=True, hide_index=True, height=360)


def metric_grid(metrics: dict[str, object]) -> None:
    row_one = st.columns(4)
    row_one[0].metric("Users", format_int(metrics["users"]))
    row_one[1].metric("Venues", format_int(metrics["venues"]))
    row_one[2].metric("Content", format_int(metrics["content"]))
    row_one[3].metric("Views", format_int(metrics["views"]))

    row_two = st.columns(4)
    row_two[0].metric("Likes", format_int(metrics["likes"]))
    row_two[1].metric("Follows", format_int(metrics["follows"]))
    row_two[2].metric("Avg view duration", format_seconds(metrics["avg_duration_ms"]))
    row_two[3].metric("Avg venue rating", format_rating(metrics["avg_rating"]))

    active_day = metrics.get("most_active_day")
    if active_day:
        day_label = pd.to_datetime(active_day).strftime("%Y-%m-%d")
        st.caption(f"Most active day: {day_label} with {format_int(metrics['most_active_day_views'])} views")


def render_overview(filters: DashboardFilters) -> None:
    database = st.session_state.database
    metrics = cached_mongo_query("get_overview_metrics", database.name, database, filters)
    metric_grid(metrics)

    if not any(metrics[key] for key in ("users", "venues", "content", "views", "likes", "follows")):
        st.info("No database rows found for the selected filters.")

    left, right = st.columns(2)
    with left:
        st.plotly_chart(
            donut_chart(rows_frame(cached_mongo_query("content_by_type", database.name, database, filters)), "type", "count", "Content mix"),
            use_container_width=True,
            key="overview_content_mix",
        )
    with right:
        st.plotly_chart(
            donut_chart(
                rows_frame(cached_mongo_query("sentiment_distribution", database.name, database, filters)),
                "sentiment",
                "count",
                "Sentiment share",
            ),
            use_container_width=True,
            key="overview_sentiment_share",
        )

    left, right = st.columns(2)
    with left:
        st.plotly_chart(
            bar_chart(rows_frame(cached_mongo_query("views_by_source", database.name, database, filters)), "source", "views", "Views by source"),
            use_container_width=True,
            key="overview_views_by_source",
        )
    with right:
        st.plotly_chart(
            bar_chart(rows_frame(cached_mongo_query("users_by_city", database.name, database, filters)), "city", "users", "Users by city"),
            use_container_width=True,
            key="overview_users_by_city",
        )


def render_content(filters: DashboardFilters) -> None:
    database = st.session_state.database

    st.plotly_chart(
        line_chart(
            rows_frame(cached_mongo_query("content_over_time", database.name, database, filters)),
            "date",
            "count",
            "Content over time",
            color="type",
            height=420,
        ),
        use_container_width=True,
        key="content_over_time",
    )

    left, right = st.columns(2)
    with left:
        st.plotly_chart(
            line_chart(
                rows_frame(cached_mongo_query("sentiment_over_time", database.name, database, filters)),
                "date",
                "count",
                "Sentiment over time",
                color="sentiment",
            ),
            use_container_width=True,
            key="content_sentiment_over_time",
        )
    with right:
        st.plotly_chart(
            bar_chart(rows_frame(cached_mongo_query("content_by_style", database.name, database, filters)), "style", "count", "Content by style"),
            use_container_width=True,
            key="content_by_style",
        )

    left, right = st.columns([1, 1.4])
    with left:
        hashtags = rows_frame(cached_mongo_query("top_hashtags", database.name, database, filters))
        st.plotly_chart(
            bar_chart(hashtags, "count", "hashtag", "Top hashtags", orientation="h", height=520),
            use_container_width=True,
            key="content_top_hashtags",
        )
    with right:
        show_table("Top content", rows_frame(cached_mongo_query("top_content", database.name, database, filters)), height=520)


def render_engagement(filters: DashboardFilters) -> None:
    database = st.session_state.database

    st.plotly_chart(
        line_chart(
            rows_frame(cached_mongo_query("views_over_time", database.name, database, filters)),
            "date",
            "views",
            "Views over time",
            color="source",
            height=420,
        ),
        use_container_width=True,
        key="engagement_views_over_time",
    )

    left, right = st.columns(2)
    with left:
        st.plotly_chart(
            bar_chart(rows_frame(cached_mongo_query("views_by_source", database.name, database, filters)), "source", "views", "Views by source"),
            use_container_width=True,
            key="engagement_views_by_source",
        )
    with right:
        duration = add_duration_seconds(rows_frame(cached_mongo_query("duration_by_source", database.name, database, filters)))
        st.plotly_chart(
            bar_chart(duration, "source", "avg_duration_s", "Average duration by source"),
            use_container_width=True,
            key="engagement_avg_duration_by_source",
        )

    left, right = st.columns(2)
    with left:
        show_table(
            "Top viewed content",
            add_duration_seconds(rows_frame(cached_mongo_query("top_viewed_content", database.name, database, filters))),
            height=440,
        )
    with right:
        show_table(
            "Most active users",
            add_duration_seconds(rows_frame(cached_mongo_query("most_active_users", database.name, database, filters))),
            height=440,
        )


def render_virality(filters: DashboardFilters) -> None:
    database = st.session_state.database

    if filters.content_type and filters.content_type not in VIRALITY_CONTENT_TYPE_OPTIONS:
        st.warning("The current virality definition covers posts and comments. Clear the review content-type filter to see viral candidates.")
        return

    type_options = [filters.content_type] if filters.content_type in VIRALITY_CONTENT_TYPE_OPTIONS else VIRALITY_CONTENT_TYPE_OPTIONS
    controls = st.columns([1.4, 1, 1, 1, 1])
    with controls[0]:
        selected_types = st.multiselect("Content types", type_options, default=type_options)
    with controls[1]:
        minimum_interactions = st.number_input("Minimum interactions", min_value=1, max_value=10000, value=20, step=5)
    with controls[2]:
        multiplier = st.slider("Average multiplier", min_value=1.0, max_value=10.0, value=3.0, step=0.5)
    with controls[3]:
        limit = st.selectbox("Rows", VIRALITY_LIMIT_OPTIONS, index=VIRALITY_LIMIT_OPTIONS.index(25))
    with controls[4]:
        trend_count = st.slider("Trend lines", min_value=1, max_value=10, value=5, step=1)

    if not selected_types:
        st.info("Select at least one content type.")
        return

    content_types = tuple(selected_types)
    baseline = cached_mongo_query(
        "virality_baseline",
        database.name,
        database,
        filters,
        content_types=content_types,
        multiplier=float(multiplier),
    )
    candidates = cached_mongo_query(
        "viral_content",
        database.name,
        database,
        filters,
        limit=int(limit),
        content_types=content_types,
        multiplier=float(multiplier),
        minimum_interactions=int(minimum_interactions),
    )

    baseline_frame = rows_frame(baseline)
    for column in ("avg_interactions", "viral_threshold", "avg_unique_viewers"):
        if column in baseline_frame.columns:
            baseline_frame[column] = pd.to_numeric(baseline_frame[column], errors="coerce").round(2)

    candidate_frame = virality_frame(candidates)

    def baseline_value(content_type: str, column: str) -> object:
        if baseline_frame.empty or column not in baseline_frame.columns:
            return None
        rows = baseline_frame[baseline_frame["type"] == content_type]
        if rows.empty:
            return None
        return rows.iloc[0][column]

    top_ratio = candidate_frame["virality_ratio"].max() if "virality_ratio" in candidate_frame.columns and not candidate_frame.empty else None
    top_interactions = candidate_frame["interaction_count"].max() if "interaction_count" in candidate_frame.columns and not candidate_frame.empty else 0

    metrics = st.columns(5)
    metrics[0].metric("Viral items", format_int(len(candidate_frame)))
    metrics[1].metric("Top ratio", format_decimal(top_ratio, suffix="x"))
    metrics[2].metric("Top interactions", format_int(top_interactions))
    metrics[3].metric("Post avg", format_decimal(baseline_value("post", "avg_interactions")))
    metrics[4].metric("Comment avg", format_decimal(baseline_value("comment", "avg_interactions")))

    if baseline_frame.empty:
        st.info("No post or comment interactions for the selected filters.")
        return

    baseline_columns = [
        "type",
        "content_count",
        "total_interactions",
        "avg_interactions",
        "viral_threshold",
        "max_interactions",
        "avg_unique_viewers",
        "last_interaction_at",
    ]
    baseline_frame = baseline_frame[[column for column in baseline_columns if column in baseline_frame.columns]]

    left, right = st.columns(2)
    with left:
        st.plotly_chart(
            bar_chart(baseline_frame, "type", "avg_interactions", "Average interactions by type"),
            use_container_width=True,
            key="virality_average_interactions",
        )
    with right:
        st.plotly_chart(
            bar_chart(baseline_frame, "type", "viral_threshold", "Viral threshold by type"),
            use_container_width=True,
            key="virality_threshold_by_type",
        )

    left, right = st.columns([1, 1.6])
    with left:
        show_table("Virality baseline", baseline_frame, height=300)
    with right:
        show_table("Viral posts and comments", candidate_frame, height=420)

    if candidate_frame.empty or "content_id" not in candidate_frame.columns:
        st.info("No content meets the current virality criteria.")
        return

    trend_ids = tuple(candidate_frame["content_id"].dropna().head(int(trend_count)).tolist())
    trend_frame = rows_frame(
        cached_mongo_query(
            "viral_interactions_over_time",
            database.name,
            database,
            filters,
            content_ids=trend_ids,
        )
    )
    if trend_frame.empty:
        return

    trend_frame["content_label"] = trend_frame.apply(
        lambda row: f"{row.get('type', 'content')}:{str(row.get('content_id', ''))[:12]}",
        axis=1,
    )
    st.plotly_chart(
        line_chart(
            trend_frame,
            "date",
            "interactions",
            "Viral interactions over time",
            color="content_label",
            height=420,
        ),
        use_container_width=True,
        key="virality_interactions_over_time",
    )


def render_user_feed(filters: DashboardFilters) -> None:
    database = st.session_state.database
    users = cached_mongo_query("most_engaged_users", database.name, database, filters, limit=100)
    venues = cached_mongo_query("most_engaged_venues", database.name, database, filters, limit=100)
    users_frame = add_duration_seconds(rows_frame(users))
    venues_frame = add_duration_seconds(rows_frame(venues))
    selected_user_ids: list[object] = []
    selected_venue_ids: list[object] = []

    st.subheader("Feed selection")
    left, right = st.columns(2)
    with left:
        if users_frame.empty:
            st.info("No engaged users for the selected filters.")
            st.session_state.selected_feed_user_ids = []
        else:
            user_ids = users_frame["user_id"].tolist()
            labels = {user["user_id"]: user_option_label(user) for user in users if user.get("user_id") is not None}
            selected_user_ids = st.multiselect(
                "Users",
                options=user_ids,
                default=[],
                format_func=lambda user_id: labels.get(user_id, str(user_id)),
                key="feed_user_ids",
            )
            st.session_state.selected_feed_user_ids = selected_user_ids

    with right:
        if venues_frame.empty:
            st.info("No engaged venues for the selected filters.")
            st.session_state.selected_feed_venue_ids = []
        else:
            venue_ids = venues_frame["venue_id"].tolist()
            labels = {venue["venue_id"]: venue_option_label(venue) for venue in venues if venue.get("venue_id") is not None}
            selected_venue_ids = st.multiselect(
                "Venues",
                options=venue_ids,
                default=[],
                format_func=lambda venue_id: labels.get(venue_id, str(venue_id)),
                key="feed_venue_ids",
            )
            st.session_state.selected_feed_venue_ids = selected_venue_ids

    left, right = st.columns(2)
    with left:
        if selected_user_ids:
            show_table("Selected users", selected_user_frame(users_frame, selected_user_ids), height=220)
        elif not users_frame.empty:
            st.info("Select one or more users to prepare feed results.")

    with right:
        if selected_venue_ids:
            show_table("Selected venues", selected_venue_frame(venues_frame, selected_venue_ids), height=220)
        elif not venues_frame.empty:
            st.info("Select one or more venues to constrain feed results.")

    if selected_user_ids:
        st.divider()

        def feed_recommendations(graph_query_name: str, mongo_query_name: str, limit: int) -> list[dict]:
            if st.session_state.neo4j_available:
                return cached_graph_recommendations(
                    graph_query_name,
                    database.name,
                    database,
                    st.session_state.neo4j_driver,
                    filters,
                    tuple(selected_user_ids),
                    tuple(selected_venue_ids),
                    limit,
                )
            return cached_recommendations(
                mongo_query_name,
                database.name,
                database,
                filters,
                tuple(selected_user_ids),
                tuple(selected_venue_ids),
                limit,
            )

        render_recommendation_section(
            "Posts Similar to Previously Liked Content",
            "liked_content_recommendations",
            lambda limit: feed_recommendations(
                "recommendations_from_liked_content_graph",
                "recommendations_from_liked_content",
                limit,
            ),
        )
        render_recommendation_section(
            "Posts Similar to Previously Engaged Content",
            "engaged_content_recommendations",
            lambda limit: feed_recommendations(
                "recommendations_from_viewed_content_graph",
                "recommendations_from_engaged_content",
                limit,
            ),
        )
        render_recommendation_section(
            "Posts Liked by Similar Users",
            "similar_user_like_recommendations",
            lambda limit: feed_recommendations(
                "recommendations_from_similar_user_likes_graph",
                "recommendations_from_similar_user_likes",
                limit,
            ),
        )
        if st.session_state.neo4j_available:
            render_recommendation_section(
                "Content From Followed Authors",
                "graph_followed_author_recommendations",
                lambda limit: cached_graph_recommendations(
                    "content_from_followed_authors",
                    database.name,
                    database,
                    st.session_state.neo4j_driver,
                    filters,
                    tuple(selected_user_ids),
                    tuple(selected_venue_ids),
                    limit,
                ),
            )
    elif not users_frame.empty:
        st.info("Select one or more users to fetch recommendations.")

    left, right = st.columns(2)
    with left:
        if not users_frame.empty:
            with st.expander("Top 100 engaged users"):
                show_table("Engaged users", selected_user_frame(users_frame, users_frame["user_id"].tolist()), height=420)
    with right:
        if not venues_frame.empty:
            with st.expander("Top 100 engaged venues"):
                show_table("Engaged venues", selected_venue_frame(venues_frame, venues_frame["venue_id"].tolist()), height=420)


def render_venues(filters: DashboardFilters) -> None:
    database = st.session_state.database

    left, right = st.columns(2)
    with left:
        st.plotly_chart(
            bar_chart(rows_frame(cached_mongo_query("venues_by_city", database.name, database, filters)), "city", "venues", "Venues by city"),
            use_container_width=True,
            key="venues_by_city",
        )
    with right:
        st.plotly_chart(
            bar_chart(rows_frame(cached_mongo_query("top_cuisines", database.name, database, filters)), "cuisine", "venues", "Top cuisines"),
            use_container_width=True,
            key="venues_top_cuisines",
        )

    left, right = st.columns(2)
    with left:
        st.plotly_chart(
            bar_chart(
                rows_frame(cached_mongo_query("venue_rating_by_city", database.name, database, filters)),
                "city",
                "avg_rating",
                "Average rating by city",
            ),
            use_container_width=True,
            key="venues_rating_by_city",
        )
    with right:
        price_rating = rows_frame(cached_mongo_query("venue_price_rating_points", database.name, database, filters))
        if "votes" in price_rating.columns:
            price_rating["votes"] = pd.to_numeric(price_rating["votes"], errors="coerce").fillna(1).clip(lower=1)
        st.plotly_chart(
            scatter_chart(
                price_rating,
                "average_cost_for_two",
                "rating",
                "Price vs rating",
                color="city" if "city" in price_rating.columns else None,
                size="votes" if "votes" in price_rating.columns else None,
                hover_name="name" if "name" in price_rating.columns else None,
            ),
            use_container_width=True,
            key="venues_price_vs_rating",
        )

    map_points = rows_frame(cached_mongo_query("venue_map_points", database.name, database, filters))
    if "votes" in map_points.columns:
        map_points["votes"] = pd.to_numeric(map_points["votes"], errors="coerce").fillna(1).clip(lower=1)
    st.plotly_chart(map_chart(map_points, "Venue map"), use_container_width=True, key="venues_map")


def neo4j_frame(query_name: str, filters: DashboardFilters, limit: int = 20) -> pd.DataFrame:
    if not st.session_state.neo4j_available:
        return pd.DataFrame()
    return rows_frame(cached_neo4j_query(query_name, st.session_state.neo4j_driver, filters, limit=limit))


def render_relations(filters: DashboardFilters) -> None:
    if not st.session_state.neo4j_available:
        st.warning("Neo4j is not available.")
        return

    try:
        left, right = st.columns(2)
        with left:
            followed_users = neo4j_frame("top_followed_users", filters)
            st.plotly_chart(
                bar_chart(followed_users, "followers", "user_id", "Top followed users", orientation="h"),
                use_container_width=True,
                key="relations_top_followed_users",
            )
        with right:
            followed_venues = neo4j_frame("top_followed_venues", filters)
            st.plotly_chart(
                bar_chart(followed_venues, "followers", "name", "Top followed venues", orientation="h"),
                use_container_width=True,
                key="relations_top_followed_venues",
            )

        left, right = st.columns(2)
        with left:
            creators = neo4j_frame("top_creators", filters)
            st.plotly_chart(
                bar_chart(creators, "created_content", "user_id", "Top creators", orientation="h"),
                use_container_width=True,
                key="relations_top_creators",
            )
        with right:
            graph_viewed = neo4j_frame("top_viewed_content_graph", filters)
            st.plotly_chart(
                bar_chart(graph_viewed, "views", "content_id", "Top graph-viewed content", orientation="h"),
                use_container_width=True,
                key="relations_top_graph_viewed_content",
            )
            show_table("Graph-viewed content details", add_duration_seconds(graph_viewed))

        left, right = st.columns(2)
        with left:
            liked_content = neo4j_frame("top_liked_content", filters)
            st.plotly_chart(
                bar_chart(liked_content, "likes", "content_id", "Top liked content", orientation="h"),
                use_container_width=True,
                key="relations_top_liked_content",
            )
            show_table("Liked content details", liked_content)
        with right:
            show_table("Strongest content similarity", neo4j_frame("content_similarity", filters, limit=50))
    except Exception as exc:
        st.warning(f"Neo4j query failed: {exc}")


def render_dashboard_page(page: str, filters: DashboardFilters) -> None:
    renderers: dict[str, Callable[[DashboardFilters], None]] = {
        "Overview": render_overview,
        "Content": render_content,
        "Engagement": render_engagement,
        "Virality": render_virality,
        "User Feed": render_user_feed,
        "Venues / Location": render_venues,
        "Relations": render_relations,
    }
    renderers[page](filters)


def main() -> None:
    st.title("Social Analytics Dashboard")

    try:
        database = get_mongo_database()
        cached_mongo_connection_check(database.name, database)
        st.session_state.database = database
    except Exception as exc:
        st.error(f"MongoDB connection failed: {exc}")
        return

    try:
        driver = get_neo4j_driver()
        cached_neo4j_connection_check(driver)
        st.session_state.neo4j_driver = driver
        st.session_state.neo4j_available = True
    except Exception:
        st.session_state.neo4j_driver = None
        st.session_state.neo4j_available = False

    page = select_dashboard_page()
    filters = build_filters()
    render_dashboard_page(page, filters)


if __name__ == "__main__":
    main()
