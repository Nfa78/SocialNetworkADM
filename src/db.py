from contextlib import contextmanager
from typing import Iterator

from neo4j import GraphDatabase
from pymongo import MongoClient

from src.settings import settings


mongo_client: MongoClient = MongoClient(settings.mongo_uri)
mongo_db = mongo_client[settings.mongo_database]

neo4j_driver = GraphDatabase.driver(
    settings.neo4j_uri,
    auth=(settings.neo4j_user, settings.neo4j_password),
)


@contextmanager
def neo4j_session() -> Iterator:
    with neo4j_driver.session() as session:
        yield session


def close_connections() -> None:
    mongo_client.close()
    neo4j_driver.close()
