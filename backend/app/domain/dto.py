from sqlmodel import SQLModel


class EventCreate(SQLModel):
    title: str
    description: str
    start_date: str  # ISO format date string
    capacity: int
    artist_name: int


class EventResponse(SQLModel):
    id: int
    title: str
    description: str
    start_date: str  # ISO format date string
    capacity: int
    artist_name: str


class ArtistCreate(SQLModel):
    title: str
    description: str


class ArtistResponse(SQLModel):
    id: int
    title: str
    description: str


class VisitorCreate(SQLModel):
    name: str
    email: str
    phone: str


class VisitorResponse(SQLModel):
    id: int
    name: str
    email: str
    phone: str


class RegistrationCreate(SQLModel):
    event_id: int
    visitor_id: int
    status: str  # Should be one of the Status enum values
