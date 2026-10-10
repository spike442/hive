from datetime import UTC, datetime

from core.domain import AgentDomain, AgentStatus
from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from hive.persistence.database import Base, Database


class AgentRecord(Base):
    __tablename__ = "agent"

    domain: Mapped[str] = mapped_column(String(64), primary_key=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AgentRepository:
    def __init__(self, database: Database, domains: list[AgentDomain]):
        self.database = database
        self.domains = domains

    def ensure_agents(self) -> None:
        now = datetime.now(UTC)
        with self.database.sessions.begin() as session:
            for domain in self.domains:
                if session.get(AgentRecord, domain) is None:
                    session.add(AgentRecord(domain=domain, active=False, updated_at=now))

    def is_active(self, domain: AgentDomain) -> bool:
        with self.database.sessions() as session:
            record = session.get(AgentRecord, domain)
            return bool(record and record.active)

    def set_status(self, domain: AgentDomain, status: AgentStatus) -> None:
        now = datetime.now(UTC)
        with self.database.sessions.begin() as session:
            record = session.get(AgentRecord, domain)
            if record is None:
                record = AgentRecord(domain=domain, active=False, updated_at=now)
                session.add(record)
            record.active = status == AgentStatus.ACTIVE
            record.updated_at = now
