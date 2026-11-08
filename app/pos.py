"""Route and position helpers."""


def default_route():
    return [
        {"lat": 47.1500, "lon": 27.5900},
        {"lat": 47.1510, "lon": 27.5910},
        {"lat": 47.1520, "lon": 27.5920},
    ]


def load_route_from_data(data):
    if not data:
        return default_route()
    route = []
    for item in data:
        route.append({
            "lat": float(item.get("lat", 0.0)),
            "lon": float(item.get("lon", 0.0)),
        })
    return route


def load_route(path=None):
    if path is None:
        return default_route()
    import json
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return load_route_from_data(data)


def position_at_index(route, index):
    if not route:
        return {"lat": 0.0, "lon": 0.0}
    idx = index % len(route)
    return route[idx]
