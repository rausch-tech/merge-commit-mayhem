"""
Raum-Layout für die Vertical Slice. Map: 900×400 px, zwei Reihen à drei Räumen
(300×200 px). Farben gemäß merge_conflict_mayhem_project/docs/07_visual_direction.md.

Wechsel auf rooms.json kommt in Sprint 4 (siehe Roadmap).
"""

from typing import Final, TypedDict


class RoomDef(TypedDict):
    id: str
    title: str
    x: int
    y: int
    width: int
    height: int
    color: str  # hex


ROOM_LAYOUT: Final[list[RoomDef]] = [
    {"id": "open_space", "title": "Open Space", "x": 0,   "y": 0,   "width": 300, "height": 200, "color": "#3a4560"},
    {"id": "meeting_room", "title": "Meeting Room", "x": 300, "y": 0,   "width": 300, "height": 200, "color": "#5a3a70"},
    {"id": "kitchen", "title": "Kitchen", "x": 600, "y": 0,   "width": 300, "height": 200, "color": "#7a5030"},
    {"id": "server_room", "title": "Server Room", "x": 0,   "y": 200, "width": 300, "height": 200, "color": "#2a4a70"},
    {"id": "war_room", "title": "War Room", "x": 300, "y": 200, "width": 300, "height": 200, "color": "#2a607a"},
    {"id": "legacy_basement", "title": "Legacy Basement", "x": 600, "y": 200, "width": 300, "height": 200, "color": "#3a6a3a"},
]

MAP_WIDTH: Final[int] = 900
MAP_HEIGHT: Final[int] = 400
