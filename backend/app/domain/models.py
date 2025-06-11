from typing import List, Optional
import pydantic
from enum import Enum
from sqlmodel import Relationship, SQLModel, Field
from datetime import datetime


class Status(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Registration(SQLModel, table=True):
    __tablename__ = "registrations"
    event_id: Optional[int] = Field(
        default=None, foreign_key="events.id", primary_key=True
    )
    visitor_id: Optional[int] = Field(
        default=None, foreign_key="visitors.id", primary_key=True
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: Status = Field(default=Status.PENDING)


class Event(SQLModel, table=True):
    __tablename__ = "events"
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: str
    start_date: datetime
    capacity: int
    artist_id: Optional[int] = Field(default=None, foreign_key="artists.id")
    artist: Optional["Artist"] = Relationship(back_populates="events")
    visitors: List["Visitor"] = Relationship(back_populates="events", link_model=Registration)  # type: ignore


class Artist(SQLModel, table=True):
    __tablename__ = "artists"
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: Optional[str] = None
    events: List[Event] = Relationship(back_populates="artist")


class Visitor(SQLModel, table=True):
    __tablename__ = "visitors"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str
    phone: str
    events: List["Event"] = Relationship(back_populates="visitors", link_model=Registration)  # type: ignore
