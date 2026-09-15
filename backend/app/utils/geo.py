"""
utils/geo.py
-------------
A single small helper: calculating the straight-line distance between
two lat/lng points on Earth, using the Haversine formula.

This isn't in the original folder structure, but it's a genuinely
reusable, self-contained piece of math (recycler matching needs it now;
pickup ETA/distance features later probably will too) — putting it in
its own tiny utils file avoids duplicating this formula in multiple
services.
"""

import math


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Returns the distance in kilometers between two (latitude, longitude)
    points, "as the crow flies" (straight-line distance, not driving
    distance -- good enough for matching/estimates in this prototype).
    """
    R = 6371.0  # Earth's radius in kilometers

    lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
    lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    return R * c
