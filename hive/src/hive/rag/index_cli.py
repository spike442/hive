from hive.infrastructure.config import Settings
from hive.persistence.database import Database
from hive.rag.indexer import RagIndexer


def main() -> None:
    settings = Settings.load()
    database = Database(settings.database_dsn)
    indexer = RagIndexer(settings, database)
    try:
        print(f"Indexed {indexer.run()} changed RAG documents")
    finally:
        indexer.close()
        database.close()


if __name__ == "__main__":
    main()
