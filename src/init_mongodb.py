from src.mongo_schema import initialize_mongodb_collections


def main() -> None:
    results = initialize_mongodb_collections()
    for collection_name, status in results.items():
        print(f"{collection_name}: {status}")


if __name__ == "__main__":
    main()
