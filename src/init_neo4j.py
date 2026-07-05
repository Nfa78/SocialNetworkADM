from src.neo4j_schema import initialize_neo4j_indexes


def main() -> None:
    results = initialize_neo4j_indexes()
    for index_name, status in results.items():
        print(f"{index_name}: {status}")


if __name__ == "__main__":
    main()
