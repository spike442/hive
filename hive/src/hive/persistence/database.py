from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


class Database:
    def __init__(self, database_dsn: str):
        self.engine = create_engine(database_dsn, connect_args={"connect_timeout": 10}, pool_pre_ping=True)
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)

    def close(self) -> None:
        self.engine.dispose()
