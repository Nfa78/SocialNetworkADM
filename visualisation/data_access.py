from __future__ import annotations

import os
from typing import Any

import streamlit as st
from neo4j import Driver, GraphDatabase
from pymongo import MongoClient
from pymongo.database import Database


DEFAULT_MONGO_URI = "mongodb://admin:admin_password@localhost:27017/social_analytics?authSource=admin"
DEFAULT_MONGO_DATABASE = "social_analytics"
DEFAULT_NEO4J_URI = "bolt://localhost:7687"
DEFAULT_NEO4J_USER = "neo4j"
DEFAULT_NEO4J_PASSWORD = "neo4j_password"


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


@st.cache_resource(show_spinner=False)
def get_mongo_client() -> MongoClient[dict[str, Any]]:
    return MongoClient(_env("MONGO_URI", DEFAULT_MONGO_URI), serverSelectionTimeoutMS=5000)


def get_mongo_database() -> Database[dict[str, Any]]:
    return get_mongo_client()[_env("MONGO_DATABASE", DEFAULT_MONGO_DATABASE)]


@st.cache_resource(show_spinner=False)
def get_neo4j_driver() -> Driver:
    return GraphDatabase.driver(
        _env("NEO4J_URI", DEFAULT_NEO4J_URI),
        auth=(_env("NEO4J_USER", DEFAULT_NEO4J_USER), _env("NEO4J_PASSWORD", DEFAULT_NEO4J_PASSWORD)),
    )


def check_mongo_connection(database: Database[dict[str, Any]]) -> None:
    database.command("ping")


def check_neo4j_connection(driver: Driver) -> None:
    with driver.session() as session:
        session.run("RETURN 1 AS ok").single()
