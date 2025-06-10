from typing import List, Optional
from sqlmodel import SQLModel
from datetime import datetime

from backend.app.domain.models import Artist, Event


class EventCreate(SQLModel):
    title: str
    description: str
    start_date: datetime  # ISO format datetime
    capacity: int
    artist_name: Optional[str] = None

class EventResponse(SQLModel):
    id: int
    title: str
    description: str
    start_date: datetime  # ISO format datetime
    capacity: int
    artist: Optional[Artist] = None


class ArtistCreate(SQLModel):
    title: str
    description: Optional[str] = None


class ArtistResponse(SQLModel):
    id: int
    title: str
    description: Optional[str] = None
    events: Optional[List[EventResponse]] = None

    class Config:
        orm_mode = True
        exclude_none = True


class VisitorCreate(SQLModel):
    name:  str
    email: str
    phone: str
    event_ids: Optional[List[int]] = None


class VisitorResponse(SQLModel):
    id:      int
    name:    str
    email:   str
    phone:   str
    events:  List[EventResponse] = []

    class Config:
        orm_mode = True


class RegistrationCreate(SQLModel):
    event_id: int
    visitor_id: int
    status: str  # Should be one of the Status enum values
