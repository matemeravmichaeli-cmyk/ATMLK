"""
Political Astrology Tracker – FastAPI entry point.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from engine.positions import all_positions, planet_position, julian_day, PLANETS
from engine.aspects import calculate_aspects

app = FastAPI(
    title="Political Astrology Tracker",
    version="0.1.0",
    description="Astrological engine for political event analysis",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class PlanetOut(BaseModel):
    body: str
    longitude: float
    latitude: float
    distance: float
    speed: float
    sign: str
    degree: float
    retrograde: bool
    label: str


class AspectOut(BaseModel):
    body1: str
    body2: str
    aspect_name: str
    symbol: str
    exact_angle: float
    actual_angle: float
    orb: float
    applying: Optional[bool]
    description: str


class ChartResponse(BaseModel):
    date: str
    julian_day: float
    planets: dict[str, PlanetOut]
    aspects: list[AspectOut]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_date(date_str: str) -> tuple[int, int, int]:
    """Parse YYYY-MM-DD string."""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        return d.year, d.month, d.day
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid date format: {date_str!r}. Use YYYY-MM-DD.")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", summary="Health check")
def root():
    return {"status": "ok", "service": "political-astrology-tracker"}


@app.get("/chart", response_model=ChartResponse, summary="Full chart for a date")
def chart(
    date_str: str = Query(..., alias="date", description="Date in YYYY-MM-DD format"),
    hour_ut: float = Query(12.0, description="Hour in UT (0–24)"),
):
    """
    Return all planet positions and aspects for the given date.
    """
    year, month, day = _parse_date(date_str)
    jd = julian_day(year, month, day, hour_ut)
    positions = all_positions(jd)
    aspects = calculate_aspects(positions)

    planets_out = {
        name: PlanetOut(
            body=p.body,
            longitude=round(p.longitude, 4),
            latitude=round(p.latitude, 4),
            distance=round(p.distance, 6),
            speed=round(p.speed, 6),
            sign=p.sign,
            degree=round(p.degree, 4),
            retrograde=p.retrograde,
            label=p.label(),
        )
        for name, p in positions.items()
    }

    aspects_out = [
        AspectOut(
            body1=a.body1,
            body2=a.body2,
            aspect_name=a.aspect_name,
            symbol=a.symbol,
            exact_angle=a.exact_angle,
            actual_angle=round(a.actual_angle, 4),
            orb=round(a.orb, 4),
            applying=a.applying,
            description=a.description(),
        )
        for a in aspects
    ]

    return ChartResponse(
        date=date_str,
        julian_day=round(jd, 4),
        planets=planets_out,
        aspects=aspects_out,
    )


@app.get("/planet/{body}", response_model=PlanetOut, summary="Single planet position")
def single_planet(
    body: str,
    date_str: str = Query(..., alias="date", description="Date in YYYY-MM-DD format"),
    hour_ut: float = Query(12.0, description="Hour in UT (0–24)"),
):
    """Return position for one planet on a given date."""
    if body.lower() not in PLANETS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown body: {body!r}. Valid: {list(PLANETS.keys())}",
        )
    year, month, day = _parse_date(date_str)
    jd = julian_day(year, month, day, hour_ut)
    p = planet_position(body.lower(), jd)
    return PlanetOut(
        body=p.body,
        longitude=round(p.longitude, 4),
        latitude=round(p.latitude, 4),
        distance=round(p.distance, 6),
        speed=round(p.speed, 6),
        sign=p.sign,
        degree=round(p.degree, 4),
        retrograde=p.retrograde,
        label=p.label(),
    )


@app.get("/aspects", response_model=list[AspectOut], summary="Aspects for a date")
def aspects_only(
    date_str: str = Query(..., alias="date", description="Date in YYYY-MM-DD format"),
    hour_ut: float = Query(12.0, description="Hour in UT (0–24)"),
    min_orb: float = Query(0.0, description="Minimum orb to include"),
    max_orb: float = Query(8.0, description="Maximum orb to include"),
):
    """Return all aspects within orb for the given date."""
    year, month, day = _parse_date(date_str)
    jd = julian_day(year, month, day, hour_ut)
    positions = all_positions(jd)
    aspects = calculate_aspects(positions)

    filtered = [a for a in aspects if min_orb <= a.orb <= max_orb]

    return [
        AspectOut(
            body1=a.body1,
            body2=a.body2,
            aspect_name=a.aspect_name,
            symbol=a.symbol,
            exact_angle=a.exact_angle,
            actual_angle=round(a.actual_angle, 4),
            orb=round(a.orb, 4),
            applying=a.applying,
            description=a.description(),
        )
        for a in filtered
    ]
