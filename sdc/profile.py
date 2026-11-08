"""Project profile helpers used for device compatibility checks."""

from __future__ import annotations


class ProjectProfile:
    """Static profile definition for Meshtastic/Zigbee devices."""

    def __init__(
        self,
        region: str = "EU_868",
        preset: str = "LONG_FAST",
        channel_name: str = "VEH",
    ):
        self.region = region
        self.preset = preset
        self.channel_name = channel_name

    def as_dict(self) -> dict:
        return {
            "region": self.region,
            "preset": self.preset,
            "channel_name": self.channel_name,
        }

    def diff(self, target: dict) -> dict:
        result = {}
        for field in ("region", "preset", "channel_name"):
            current = getattr(self, field)
            other = target.get(field)
            if current != other:
                result[field] = {"current": current, "target": other}
        return result
