from datetime import datetime

from pydantic import BaseModel, Field


class DatasetCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=5000)
    status: str = Field(default="active", min_length=1, max_length=30)


class DatasetUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=5000)
    status: str | None = Field(default=None, min_length=1, max_length=30)


class DatasetOut(BaseModel):
    id: str
    name: str
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    code: str = Field(min_length=1, max_length=60)
    description: str | None = Field(default=None, max_length=5000)
    status: str = Field(default="active", min_length=1, max_length=30)


class ProjectUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    code: str | None = Field(default=None, min_length=1, max_length=60)
    description: str | None = Field(default=None, max_length=5000)
    status: str | None = Field(default=None, min_length=1, max_length=30)


class ProjectOut(BaseModel):
    id: str
    name: str
    code: str
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class ProjectMemberCreateRequest(BaseModel):
    user_id: str
    role_in_project: str = Field(min_length=1, max_length=60)
    can_edit: bool = True


class ProjectMemberUpdateRequest(BaseModel):
    role_in_project: str | None = Field(default=None, min_length=1, max_length=60)
    can_edit: bool | None = None


class ProjectMemberOut(BaseModel):
    id: str
    user_id: str
    username: str
    role_in_project: str
    can_edit: bool
    created_at: datetime
    updated_at: datetime


class ProjectDatasetOut(BaseModel):
    id: str
    dataset_id: str
    dataset_name: str
    created_at: datetime


class OrgUserOut(BaseModel):
    id: str
    username: str
    active: bool
    roles: list[str]


class AttractionCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    city: str = Field(min_length=1, max_length=120)
    state: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=5000)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    duration_minutes: int = Field(ge=5, le=720)
    status: str = Field(default="active", min_length=1, max_length=30)


class AttractionUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    city: str | None = Field(default=None, min_length=1, max_length=120)
    state: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=5000)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    duration_minutes: int | None = Field(default=None, ge=5, le=720)
    status: str | None = Field(default=None, min_length=1, max_length=30)


class AttractionOut(BaseModel):
    id: str
    dataset_id: str
    name: str
    city: str
    state: str
    description: str | None
    latitude: float
    longitude: float
    duration_minutes: int
    status: str
    normalized_dedupe_key: str
    merged_into_attraction_id: str | None
    merged_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AttractionDuplicateGroupOut(BaseModel):
    duplicate_key: str
    duplicate_label: str
    candidate_count: int
    candidates: list[AttractionOut]


class AttractionMergeRequest(BaseModel):
    source_attraction_id: str
    target_attraction_id: str
    merge_reason: str | None = Field(default=None, max_length=5000)


class AttractionMergeOut(BaseModel):
    merge_event_id: str
    source_attraction_id: str
    target_attraction_id: str
    merged_at: datetime
