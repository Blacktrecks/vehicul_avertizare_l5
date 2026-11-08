"""Neighbour relevance filters."""


def filter_neighbours(neighbours, heading_deg=0, radius_m=100):
    """Keep only relevant neighbours by distance and heading direction."""
    filtered = []
    for item in neighbours or []:
        try:
            distance_m = float(item.get("distance_m", 0))
            bearing_deg = abs(float(item.get("bearing_deg", 0)))
        except AttributeError:
            continue
        if distance_m <= radius_m and bearing_deg <= 90:
            filtered.append(item)
    return filtered
