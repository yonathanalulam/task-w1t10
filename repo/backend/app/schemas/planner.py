from datetime import datetime

from pydantic import BaseModel, Field


class PlannerProjectOut(BaseModel):
    id: str
    name: str
    code: str
    can_edit: bool


class PlannerUserOut(BaseModel):
    id: str
    username: str


class PlannerCatalogAttractionOut(BaseModel):
    id: str
    dataset_id: str
    dataset_name: str
    name: str
    city: str
    state: str
    latitude: float
    longitude: float
    duration_minutes: int


class ItineraryCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    description: str | None = Field(default=None, max_length=5000)
    status: str = Field(default="draft", min_length=1, max_length=30)
    assigned_planner_user_id: str | None = None
    urban_speed_mph_override: float | None = Field(default=None, gt=0)
    highway_speed_mph_override: float | None = Field(default=None, gt=0)


class ItineraryUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = Field(default=None, max_length=5000)
    status: str | None = Field(default=None, min_length=1, max_length=30)
    assigned_planner_user_id: str | None = None
    urban_speed_mph_override: float | None = Field(default=None, gt=0)
    highway_speed_mph_override: float | None = Field(default=None, gt=0)


class ItineraryDayCreateRequest(BaseModel):
    day_number: int = Field(ge=1, le=365)
    title: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=5000)
    urban_speed_mph_override: float | None = Field(default=None, gt=0)
    highway_speed_mph_override: float | None = Field(default=None, gt=0)


class ItineraryDayUpdateRequest(BaseModel):
    day_number: int | None = Field(default=None, ge=1, le=365)
    title: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=5000)
    urban_speed_mph_override: float | None = Field(default=None, gt=0)
    highway_speed_mph_override: float | None = Field(default=None, gt=0)


class ItineraryStopCreateRequest(BaseModel):
    attraction_id: str
    start_minute_of_day: int = Field(ge=0, le=1439)
    duration_minutes: int = Field(ge=5, le=720)
    notes: str | None = Field(default=None, max_length=5000)


class ItineraryStopUpdateRequest(BaseModel):
    start_minute_of_day: int | None = Field(default=None, ge=0, le=1439)
    duration_minutes: int | None = Field(default=None, ge=5, le=720)
    notes: str | None = Field(default=None, max_length=5000)


class ItineraryStopReorderRequest(BaseModel):
    ordered_stop_ids: list[str] = Field(min_length=1)


class ItineraryStopOut(BaseModel):
    id: str
    itinerary_day_id: str
    attraction_id: str
    attraction_name: str
    attraction_city: str
    attraction_state: str
    latitude: float
    longitude: float
    order_index: int
    start_minute_of_day: int
    duration_minutes: int
    notes: str | None


class ItineraryWarningOut(BaseModel):
    code: str
    message: str


class ItineraryDayOut(BaseModel):
    id: str
    itinerary_id: str
    day_number: int
    title: str | None
    notes: str | None
    effective_urban_speed_mph: float
    effective_highway_speed_mph: float
    travel_distance_miles: float
    travel_time_minutes: int
    activity_minutes: int
    warnings: list[ItineraryWarningOut]
    stops: list[ItineraryStopOut]


class ItineraryOut(BaseModel):
    id: str
    org_id: str
    project_id: str
    name: str
    description: str | None
    status: str
    assigned_planner_user_id: str | None
    assigned_planner_username: str | None
    urban_speed_mph_override: float | None
    highway_speed_mph_override: float | None
    org_default_urban_speed_mph: float
    org_default_highway_speed_mph: float
    created_at: datetime
    updated_at: datetime
    version_counter: int
    days: list[ItineraryDayOut]


class ItineraryListOut(BaseModel):
    id: str
    project_id: str
    name: str
    status: str
    assigned_planner_user_id: str | None
    assigned_planner_username: str | None
    updated_at: datetime
    day_count: int


class ItineraryVersionOut(BaseModel):
    id: str
    itinerary_id: str
    version_number: int
    change_summary: str
    created_by_user_id: str
    created_by_username: str
    created_at: datetime
    snapshot: dict


class ItineraryImportAcceptedRowOut(BaseModel):
    row_number: int
    day_number: int
    stop_order: int
    attraction_id: str
    attraction_name: str
    start_time: str
    duration_minutes: int


class ItineraryImportRejectedRowOut(BaseModel):
    row_number: int
    raw_row: dict[str, str]
    errors: list[str]
    correction_hints: list[str]


class ItineraryImportReceiptOut(BaseModel):
    itinerary_id: str
    project_id: str
    file_name: str
    file_format: str
    imported_at: datetime
    applied: bool
    total_rows: int
    accepted_row_count: int
    rejected_row_count: int
    applied_day_count: int
    applied_stop_count: int
    file_errors: list[str]
    accepted_rows: list[ItineraryImportAcceptedRowOut]
    rejected_rows: list[ItineraryImportRejectedRowOut]


class SyncPackageRecordResultOut(BaseModel):
    record_type: str
    entity_id: str
    entity_name: str
    action: str
    base_version: int
    target_version: int
    destination_version: int | None
    message: str


class SyncPackageImportReceiptOut(BaseModel):
    project_id: str
    file_name: str
    imported_at: datetime
    format_version: str | None
    integrity_validated: bool
    total_record_count: int
    inserted_record_count: int
    updated_record_count: int
    conflict_count: int
    rejected_record_count: int
    applied_record_count: int
    file_errors: list[str]
    correction_hints: list[str]
    record_results: list[SyncPackageRecordResultOut]
