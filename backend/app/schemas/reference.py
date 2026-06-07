from pydantic import BaseModel

from app.schemas.common import OrmModel


class EdgeTypeResponse(OrmModel):
    edge_type: str
    display_name: str
    description: str | None = None


class IndoorNodeTypeResponse(OrmModel):
    node_type: str
    display_name: str
    description: str | None = None


class RoomCategoryResponse(OrmModel):
    room_type: str
    display_name: str
    description: str | None = None


class EntranceMasterResponse(OrmModel):
    entrance_id: str
    building_id: str
    floor_number: int
    entrance_name: str
    entrance_type: str
    description: str | None = None


class ReferenceDataResponse(BaseModel):
    edgeTypes: list[EdgeTypeResponse]
    indoorNodeTypes: list[IndoorNodeTypeResponse]
    roomCategories: list[RoomCategoryResponse]
    entrances: list[EntranceMasterResponse]
