from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    mongo_uri: str = "mongodb://admin:admin_password@localhost:27017/social_analytics?authSource=admin"
    mongo_database: str = "social_analytics"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "neo4j_password"
    kafka_bootstrap_servers: str = "localhost:9094"
    kafka_activity_topic: str = "activity-events"
    kafka_enabled: bool = False
    kafka_source_service: str = "social-analytics-api"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
