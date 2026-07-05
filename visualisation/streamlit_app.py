from __future__ import annotations

from datetime import UTC, date, datetime, time
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
    views_by_source,
    views_over_time,
)
from neo4j_queries import content_similarity, top_followed_users, top_followed_venues, top_liked_content


st.set_page_config(page_title="Social Analytics Dashboard", layout="wide")

CACHE_TTL_SECONDS = 300
CONNECTION_CHECK_TTL_SECONDS = 30
RECOMMENDATION_LIMIT_OPTIONS = [5, 10, 15, 25, 50]

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
    "top_followed_users": top_followed_users,
    "top_followed_venues": top_followed_venues,
    "top_liked_content": top_liked_content,
}


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SECONDS)
def cached_date_bounds(database_name: str, _database: Any) -> tuple[datetime | None, datetime | None]:
    return get_date_bounds(_database)


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SECONDS)
def cached_filter_options(database_name: str, _database: Any) -> dict[str, list[FilterOption]]:
    return get_filter_options(_database)


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SECONDS)
def cached_mongo_query(query_name: str, database_name: str, _database: Any, filters: DashboardFilters, limit: int | None = None) -> Any:
    query = MONGO_QUERY_FUNCTIONS[query_name]
    if limit is None:
        return query(_database, filters)
    return query(_database, filters, limit=limit)


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
    query = RECOMMENDATION_QUERY_FUNCTIONS[query_name]
    return query(_database, filters, list(user_ids), list(venue_ids), limit=limit)


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SECONDS)
def cached_neo4j_query(query_name: str, _driver: Any, filters: DashboardFilters, limit: int) -> list[dict]:
    query = NEO4J_QUERY_FUNCTIONS[query_name]
    return query(_driver, filters, limit=limit)


@st.cache_data(show_spinner=False, ttl=CONNECTION_CHECK_TTL_SECONDS)
def cached_mongo_connection_check(database_name: str, _database: Any) -> None:
    check_mongo_connection(_database)


@st.cache_data(show_spinner=False, ttl=CONNECTION_CHECK_TTL_SECONDS)
def cached_neo4j_connection_check(_driver: Any) -> None:
    check_neo4j_connection(_driver)


def rows_frame(rows: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    for column in ("date", "created_at"):
        if column in frame.columns:
            frame[column] = pd.to_datetime(frame[column])
    return frame


def optional_select(label: str, options: list[FilterOption]) -> str | None:
    labels = {option.value: f"{option.value} [{format_int(option.relevance)}]" for option in options}
    values = [option.value for option in options]

    selected = st.sidebar.selectbox(
        label,
        [None, *values],
        format_func=lambda value: "All" if value is None else labels.get(value, str(value)),
    )
    return selected


def selected_date_bounds(min_value: datetime | None, max_value: datetime | None) -> tuple[datetime, datetime]:
    today = date.today()
    min_day = min_value.date() if min_value else today
    max_day = max_value.date() if max_value else today
    if min_day > max_day:
        min_day = max_day

    selected = st.sidebar.date_input("Date range", value=(min_day, max_day), min_value=min_day, max_value=max_day)
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
        if st.button("Refresh data"):
            st.cache_data.clear()

    min_date, max_date = cached_date_bounds(database.name, database)
    options = cached_filter_options(database.name, database)

    with st.sidebar:
        start, end = selected_date_bounds(min_date, max_date)
        city = optional_select("City", options["cities"])
        content_type = optional_select("Content type", options["content_types"])
        style = optional_select("Content style", options["styles"])
        category = optional_select("Content category", options["categories"])
        sentiment = optional_select("Sentiment", options["sentiments"])
        interaction_source = optional_select("Interaction source", options["interaction_sources"])

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
                default=user_ids[:1],
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
        render_recommendation_section(
            "Posts Similar to Previously Liked Content",
            "liked_content_recommendations",
            lambda limit: cached_recommendations(
                "recommendations_from_liked_content",
                database.name,
                database,
                filters,
                tuple(selected_user_ids),
                tuple(selected_venue_ids),
                limit,
            ),
        )
        render_recommendation_section(
            "Posts Similar to Previously Engaged Content",
            "engaged_content_recommendations",
            lambda limit: cached_recommendations(
                "recommendations_from_engaged_content",
                database.name,
                database,
                filters,
                tuple(selected_user_ids),
                tuple(selected_venue_ids),
                limit,
            ),
        )
        render_recommendation_section(
            "Posts Liked by Similar Users",
            "similar_user_like_recommendations",
            lambda limit: cached_recommendations(
                "recommendations_from_similar_user_likes",
                database.name,
                database,
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

    filters = build_filters()

    overview_tab, content_tab, engagement_tab, user_feed_tab, venues_tab, relations_tab = st.tabs(
        ["Overview", "Content", "Engagement", "User Feed", "Venues / Location", "Relations"]
    )

    with overview_tab:
        render_overview(filters)
    with content_tab:
        render_content(filters)
    with engagement_tab:
        render_engagement(filters)
    with user_feed_tab:
        render_user_feed(filters)
    with venues_tab:
        render_venues(filters)
    with relations_tab:
        render_relations(filters)


if __name__ == "__main__":
    main()
