from bootstraat.backend.app.domain.models import *
from bootstraat.backend.app.domain.dto import *

from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator, Optional
from fastapi import FastAPI, Depends, HTTPException, status
from sqlmodel import SQLModel, Field, Relationship, select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.orm import sessionmaker
from fastapi.middleware.cors import CORSMiddleware

DATABASE_URL = "sqlite+aiosqlite:///bootstraat.db"
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


@app.post("/events", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    payload: EventCreate, session: AsyncSession = Depends(get_session)
):
    event = Event.model_validate(payload)
    artist = await session.select(Artist).where(Artist.title == payload.artist_name)
    if artist.all() == []:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artist '{payload.artist_name}' not found.",
        )
    event.artist = artist.first()
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return event


@app.get("/events", response_model=List[EventResponse])
async def get_events(
    session: AsyncSession = Depends(get_session),
) -> List[EventResponse]:
    events = await session.exec(
        select(Event)
        .where(Event.start_date >= datetime.now())
        .order_by(Event.start_date)
    )
    if events.all() == []:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No upcoming events found.")
    return events.all()


@app.get("/events/{event_id}", response_model=EventResponse)
async def get_event(event_id: int, session: AsyncSession = Depends(get_session)):
    event = await session.get(Event, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found."
        )
    return event


@app.post(
    "/artists", response_model=ArtistResponse, status_code=status.HTTP_201_CREATED
)
async def create_artist(
    payload: ArtistCreate, session: AsyncSession = Depends(get_session)
):
    artist = Artist.model_validate(payload)
    session.add(artist)
    await session.commit()
    await session.refresh(artist)
    return artist


@app.get("/artists", response_model=List[ArtistResponse])
async def get_artists(
    session: AsyncSession = Depends(get_session),
) -> List[ArtistResponse]:
    artists = await session.exec(select(Artist).order_by(Artist.id))
    
    return artists.all()


@app.get("/artists/{artist_id}", response_model=ArtistResponse)
async def get_artist(artist_id: int, session: AsyncSession = Depends(get_session)):
    artist = await session.get(Artist, artist_id)
    if not artist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Artist not found."
        )
    return artist


@app.post(
    "/visitors", response_model=VisitorResponse, status_code=status.HTTP_201_CREATED
)
async def create_visitor(
    payload: VisitorCreate, session: AsyncSession = Depends(get_session)
):
    visitor = Visitor.model_validate(payload)
    session.add(visitor)
    await session.commit()
    await session.refresh(visitor)
    return visitor


@app.get("/visitors", response_model=List[VisitorResponse])
async def get_visitors(
    session: AsyncSession = Depends(get_session),
) -> List[VisitorResponse]:
    visitors = await session.exec(select(Visitor).order_by(Visitor.id))
    return visitors.all()


@app.get("/visitors/{visitor_id}", response_model=VisitorResponse)
async def get_visitor(visitor_id: int, session: AsyncSession = Depends(get_session)):
    visitor = await session.get(Visitor, visitor_id)
    if not visitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Visitor not found."
        )
    return visitor


@app.post("/register", status_code=status.HTTP_201_CREATED)
async def create_registration(
    payload: RegistrationCreate, session: AsyncSession = Depends(get_session)
):
    registration = Registration.model_validate(payload)
    session.add(registration)
    await session.commit()
    await session.refresh(registration)
    return {"message": "Registration created successfully."}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app, host="localhost", port=8000, log_level="info", reload=True, debug=True
    )
