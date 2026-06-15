from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.enums import TaskPriority, TaskType


class TaskListFilters(BaseModel):
    type: TaskType | None = None
    rm_id: UUID | None = None
    family_id: UUID | None = None
    q: str | None = None
    priority: TaskPriority | None = None
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class TaskRead(BaseModel):
    type: TaskType
    priority: TaskPriority
    member_id: UUID
    member_name: str
    family_id: UUID
    family_head_name: str
    family_code: str
    rm_id: UUID
    rm_name: str
    can_number_masked: str
    description: str
    label: str


class TaskListResponse(BaseModel):
    items: list[TaskRead]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)


class TaskSummaryRead(BaseModel):
    total_tasks: int = Field(ge=0)
    kyc: int = Field(ge=0)
    payeezz: int = Field(ge=0)
    mobile: int = Field(ge=0)
    email: int = Field(ge=0)
    nominee: int = Field(ge=0)
