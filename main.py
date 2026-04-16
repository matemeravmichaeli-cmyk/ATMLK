"""
Aspect calculations for political astrology tracker.

Supported aspects with standard orbs:
    Conjunction  0°  (orb ±8°)
    Opposition  180° (orb ±8°)
    Trine       120° (orb ±6°)
    Square       90° (orb ±6°)
    Sextile      60° (orb ±4°)
    Quincunx    150° (orb ±2°)
    Semi-square  45° (orb ±2°)
    Sesquiquadrate 135° (orb ±2°)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .positions import PlanetPosition

# (exact_angle, name, symbol, orb)
ASPECT_DEFS: list[tuple[float, str, str, float]] = [
    (0.0,   "Conjunction",       "☌",  8.0),
    (180.0, "Opposition",        "☍",  8.0),
    (120.0, "Trine",             "△",  6.0),
    (90.0,  "Square",            "□",  6.0),
    (60.0,  "Sextile",           "⚹",  4.0),
    (150.0, "Quincunx",          "⚻",  2.0),
    (45.0,  "Semi-square",       "∠",  2.0),
    (135.0, "Sesquiquadrate",    "⚼",  2.0),
]


@dataclass
class Aspect:
    body1: str
    body2: str
    aspect_name: str
    symbol: str
    exact_angle: float
    actual_angle: float    # angular separation (always 0–180)
    orb: float             # deviation from exact, always positive
    applying: Optional[bool]  # True=applying, False=separating, None=unknown

    def description(self) -> str:
        direction = ""
        if self.applying is True:
            direction = " (applying)"
        elif self.applying is False:
            direction = " (separating)"
        return (
            f"{self.body1.title()} {self.symbol} {self.body2.title()} "
            f"[{self.aspect_name}] orb {self.orb:.2f}°{direction}"
        )


def angular_separation(lon1: float, lon2: float) -> float:
    """Shortest arc between two ecliptic longitudes, 0–180°."""
    diff = abs(lon1 - lon2) % 360
    return diff if diff <= 180 else 360 - diff


def find_aspect(lon1: float, lon2: float) -> Optional[tuple[str, str, float, float]]:
    """
    Return (name, symbol, exact_angle, orb) if the two longitudes form
    a recognised aspect, else None.
    """
    sep = angular_separation(lon1, lon2)
    for exact, name, symbol, max_orb in ASPECT_DEFS:
        orb = abs(sep - exact)
        if orb <= max_orb:
            return name, symbol, exact, orb
    return None


def _is_applying(p1: PlanetPosition, p2: PlanetPosition) -> Optional[bool]:
    """
    Determine if the aspect is applying (bodies moving towards exact).
    Works for direct/retrograde combinations.
    Returns None if speeds are unavailable.
    """
    if p1.speed == 0 and p2.speed == 0:
        return None
    # Relative motion of p1 with respect to p2
    relative_speed = p1.speed - p2.speed
    sep = (p1.longitude - p2.longitude) % 360
    # If sep < 180 and relative speed is negative → applying
    # If sep > 180 and relative speed is positive → applying
    if sep <= 180:
        return relative_speed < 0
    else:
        return relative_speed > 0


def calculate_aspects(positions: dict[str, PlanetPosition]) -> list[Aspect]:
    """
    Calculate all aspects among the provided planet positions.

    Parameters
    ----------
    positions : dict
        Mapping of body name → PlanetPosition (e.g. from engine.positions.all_positions).

    Returns
    -------
    list[Aspect]
        All active aspects, sorted by orb (tightest first).
    """
    bodies = list(positions.keys())
    aspects: list[Aspect] = []

    for i in range(len(bodies)):
        for j in range(i + 1, len(bodies)):
            b1, b2 = bodies[i], bodies[j]
            p1, p2 = positions[b1], positions[b2]
            result = find_aspect(p1.longitude, p2.longitude)
            if result is not None:
                name, symbol, exact, orb = result
                aspects.append(
                    Aspect(
                        body1=b1,
                        body2=b2,
                        aspect_name=name,
                        symbol=symbol,
                        exact_angle=exact,
                        actual_angle=angular_separation(p1.longitude, p2.longitude),
                        orb=orb,
                        applying=_is_applying(p1, p2),
                    )
                )

    aspects.sort(key=lambda a: a.orb)
    return aspects
