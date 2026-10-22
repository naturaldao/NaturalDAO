from typing import Any, Literal

from pydantic import BaseModel, Field


Stage = Literal['requirement', 'plan', 'operation', 'output', 'clarification', 'knowledge_update']


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    owner_scope: str = Field(min_length=1, max_length=200)


class SessionBind(BaseModel):
    client_id: str
    account_scope: str
    session_id: str
    project_id: str


class MemoryCreate(BaseModel):
    account_scope: str
    kind: str
    content: str = Field(min_length=1, max_length=10000)


class GovernRequest(BaseModel):
    request_id: str = Field(min_length=1, max_length=200)
    client_id: str
    account_scope: str
    session_id: str
    stage: Stage
    request: str = Field(min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)
    project_id: str | None = None


class OperationRequest(BaseModel):
    request_id: str
    client_id: str
    account_scope: str
    session_id: str
    operation: str = Field(min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)
    project_id: str | None = None
    task_id: str | None = None
    run_id: str | None = None
    step_id: str | None = None


class OutputRequest(BaseModel):
    request_id: str
    client_id: str
    account_scope: str
    session_id: str
    output: str = Field(min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)
    project_id: str | None = None
    task_id: str | None = None
    run_id: str | None = None
    step_id: str | None = None


class AppealRequest(BaseModel):
    request_id: str
    reason: str = Field(min_length=1)
    evidence: dict[str, Any] = Field(default_factory=dict)


class TaskCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    goal: str = Field(min_length=1, max_length=20000)
    context: dict[str, Any] = Field(default_factory=dict)
    client_id: str
    account_scope: str
    session_id: str
    project_id: str | None = None


class TaskActivate(BaseModel):
    condition_evidence: dict[str, Any] = Field(default_factory=dict)


class StepCreate(BaseModel):
    run_id: str
    request: str = Field(min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)
    kind: str = 'model'
    risk_flags: list[str] = Field(default_factory=list)
    request_id: str | None = None
    client_id: str
    account_scope: str
    session_id: str


class DeliveryCreate(BaseModel):
    run_id: str
    output: str = Field(min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)
    request_id: str | None = None
    client_id: str
    account_scope: str
    session_id: str


class PermitConsume(BaseModel):
    token: str = Field(min_length=1)
    content: str = Field(min_length=1)
    stage: Stage
    request_id: str
    conditions_satisfied: bool = False
    condition_evidence: dict[str, Any] = Field(default_factory=dict)
