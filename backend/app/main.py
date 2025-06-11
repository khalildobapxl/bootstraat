import logging
from .domain.models import *
from .domain.dto import *

from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime
from typing import AsyncGenerator, Optional
from fastapi import FastAPI, Depends, HTTPException, status
from sqlmodel import SQLModel, Field, Relationship, select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.orm import sessionmaker, selectinload
from fastapi.middleware.cors import CORSMiddleware


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Base directory for the database
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "bootstraat.db"

DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"
engine: AsyncEngine = create_async_engine(DATABASE_URL, echo=True, future=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        # Create the database tables if they do not exist
        await conn.run_sync(SQLModel.metadata.create_all)
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# region Events

# Should add (title, date, artist) constraint to avoid duplicates


@app.post("/events", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    payload: EventCreate, session: AsyncSession = Depends(get_session)
) -> EventResponse:

    event = Event.model_validate(payload)
    result = await session.exec(
        select(Artist).where(Artist.title == payload.artist_name)
    )

    artist = result.first()

    if artist is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artist '{payload.artist_name}' not found.",
        )

    event.artist_id = artist.id
    event.artist = artist

    session.add(event)
    await session.commit()
    await session.refresh(event, attribute_names=["artist"])

    return event


@app.get("/events", response_model=List[EventResponse])
async def get_events(
    session: AsyncSession = Depends(get_session),
) -> List[EventResponse]:
    result = await session.exec(
        select(Event)
        .options(selectinload(Event.artist))
        .where(Event.start_date >= datetime.now())
        .order_by(Event.start_date)
    )

    events = result.all()

    if not events:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No upcoming events found.")

    logger.info(f"Retrieved events: {events}")

    return events


@app.get("/events/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: int, session: AsyncSession = Depends(get_session)
) -> EventResponse:

    result = await session.exec(
        select(Event).where(Event.id == event_id).options(selectinload(Event.artist))
    )

    event = result.first()

    logger.info(f"Retrieved event: {event}")

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found."
        )
    return event


# @app.put("/events/{event_id}", response_model=EventResponse)
# async def update_event(
#     event_id: int,
#     payload: EventCreate,
#     session: AsyncSession = Depends(get_session),
# ) -> EventResponse:

#     event = await session.get(Event, event_id)
#     if not event:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND, detail="Event not found."
#         )

#     # Update the event fields
#     for field, value in payload.model_dump().items():
#         setattr(event, field, value)

#     result = await session.exec(
#         select(Artist).where(Artist.title == payload.artist_name)
#     )
#     artist = result.first()

#     if artist is None:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Artist '{payload.artist_name}' not found.",
#         )

#     event.artist = artist

#     await session.commit()
#     await session.refresh(event)

#     return event


@app.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(event_id: int, session: AsyncSession = Depends(get_session)):
    event = await session.get(Event, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found."
        )

    await session.delete(event)
    await session.commit()
    logging.info(f"Deleted event with ID: {event_id}")


# endregion

# region Artists


@app.post(
    "/artists", response_model=ArtistResponse, status_code=status.HTTP_201_CREATED
)
async def create_artist(
    payload: ArtistCreate, session: AsyncSession = Depends(get_session)
) -> ArtistResponse:
    artist = Artist.model_validate(payload)
    session.add(artist)
    logging.info(f"Creating artist: {artist.title}")
    await session.commit()
    await session.refresh(artist, attribute_names=["events"])
    return artist


@app.get("/artists", response_model=List[ArtistResponse])
async def get_artists(
    session: AsyncSession = Depends(get_session),
) -> List[ArtistResponse]:

    artists = await session.exec(
        select(Artist).order_by(Artist.id).options(selectinload(Artist.events))
    )

    artists_objects = artists.all()
    logging.info(f"Retrieved artists: {artists_objects}")

    if artists_objects is None or len(artists_objects) == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No artists found.")

    return artists_objects


@app.get("/artists/{artist_id}", response_model=ArtistResponse)
async def get_artist(
    artist_id: int, session: AsyncSession = Depends(get_session)
) -> ArtistResponse:
    result = await session.exec(
        select(Artist)
        .where(Artist.id == artist_id)
        .options(selectinload(Artist.events))
    )

    artist = result.first()
    if not artist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Artist not found."
        )

    return artist


@app.delete("/artists/{artist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_artist(artist_id: int, session: AsyncSession = Depends(get_session)):
    artist = await session.get(Artist, artist_id)
    if not artist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Artist not found."
        )

    await session.delete(artist)
    await session.commit()
    logging.info(f"Deleted artist with ID: {artist_id}")


# @app.put("/artists/{artist_id}", response_model=ArtistResponse)

# endregion

# region Visitors


@app.post(
    "/visitors", response_model=VisitorResponse, status_code=status.HTTP_201_CREATED
)
async def create_visitor(
    payload: VisitorCreate, session: AsyncSession = Depends(get_session)
) -> VisitorResponse:
    visitor = Visitor(name=payload.name, email=payload.email, phone=payload.phone)
    session.add(visitor)
    await session.commit()
    await session.refresh(visitor)

    # Link to events via Registration
    regs = []
    if payload.event_ids:
        for eid in payload.event_ids:
            evt = await session.get(Event, eid)
            if not evt:
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND, detail=f"Event {eid} not found."
                )
            regs.append(Registration(event_id=eid, visitor_id=visitor.id))
        session.add_all(regs)
        await session.commit()

    await session.refresh(visitor, attribute_names=["events"])

    return visitor


@app.get("/visitors", response_model=List[VisitorResponse])
async def get_visitors(
    session: AsyncSession = Depends(get_session),
) -> List[VisitorResponse]:
    result = await session.exec(
        select(Visitor).order_by(Visitor.id).options(selectinload(Visitor.events))
    )

    visitors = result.all()
    if not visitors or len(visitors) == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No visitors found.")

    logging.info(f"Retrieved visitors: {visitors}")
    return visitors


@app.get("/visitors/{visitor_id}", response_model=VisitorResponse)
async def get_visitor(
    visitor_id: int, session: AsyncSession = Depends(get_session)
) -> VisitorResponse:
    result = await session.exec(
        select(Visitor)
        .where(Visitor.id == visitor_id)
        .options(selectinload(Visitor.events))
    )

    visitor = result.first()
    logging.info(f"Retrieved visitor: {visitor}")

    if not visitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Visitor not found."
        )
    return visitor


@app.delete("/visitors/{visitor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_visitor(visitor_id: int, session: AsyncSession = Depends(get_session)):
    visitor = await session.get(Visitor, visitor_id)
    if not visitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Visitor not found."
        )

    await session.delete(visitor)
    await session.commit()
    logging.info(f"Deleted visitor with ID: {visitor_id}")


# endregion

# region register


# Still need to be improved, capacity shouldn't be changed, another field should be added to the event model
# to track the number of registrations, and the capacity should be checked against that field.
# Look into transactions and how to handle them properly in SQLAlchemy. because if two requests come in at the same time, they might both pass the capacity check
# and create registrations, exceeding the event's capacity. + We are doing write and read operations, if an exception occurs, we should rollback the transaction manually.
@app.post("/register", status_code=status.HTTP_201_CREATED)
async def create_registration(
    payload: RegistrationCreate, session: AsyncSession = Depends(get_session)
):
    registration = Registration.model_validate(payload)

    # Check if the event exists
    event = await session.get(Event, registration.event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with ID {registration.event_id} not found.",
        )
    # Check if the visitor exists
    visitor = await session.get(Visitor, registration.visitor_id)
    if not visitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Visitor with ID {registration.visitor_id} not found.",
        )
    # Check if the visitor is already registered for the event
    existing_registration = await session.get(
        Registration, (registration.event_id, registration.visitor_id)
    )
    if existing_registration:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Visitor {registration.visitor_id} is already registered for event {registration.event_id}.",
        )
    # Check if the event has reached its capacity
    if event.capacity <= len(event.visitors):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Event {registration.event_id} has reached its capacity.",
        )

    session.add(registration)
    event.capacity -= 1  # Decrease the event capacity
    registration.status = Status.APPROVED
    logging.info(
        f"Creating registration for event {registration.event_id} and visitor {registration.visitor_id}"
    )

    await session.commit()
    await session.refresh(registration)
    return {"message": "Registration created successfully."}


@app.get("/register", response_model=List[Registration])
async def get_registrations(
    session: AsyncSession = Depends(get_session),
) -> List[Registration]:
    result = await session.exec(select(Registration))
    registrations = result.all()
    logging.info(f"Retrieved registrations: {registrations}")

    if not registrations:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No registrations found.")

    return registrations


@app.delete("/register/{event_id}/{visitor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_registration(
    event_id: int, visitor_id: int, session: AsyncSession = Depends(get_session)
):
    registration = await session.get(Registration, (event_id, visitor_id))
    if not registration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration not found.",
        )

    await session.delete(registration)
    await session.commit()
    logging.info(f"Deleted registration for event {event_id} and visitor {visitor_id}.")


# endregion

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app, host="localhost", port=8000, log_level="info", reload=True, debug=True
    )
