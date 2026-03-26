from pydantic import BaseModel, Field, ConfigDict
from typing import Literal, Dict, Any, List, Optional
from uuid import uuid4
from datetime import datetime

class MessageHeader(BaseModel):
    message_id: str = Field(default_factory=lambda: str(uuid4()))
    version: Literal["1.0"] = "1.0"
    correlation_id: Optional[str] = None

class Position(BaseModel):
    x: float
    y: float
    z: Optional[float] = None
    theta: Optional[float] = None
    map_id: Optional[str] = None

class CurrentTask(BaseModel):
    task_id: str
    task_type: str
    progress: Optional[float] = Field(0.0, ge=0.0, le=100.0)

class ErrorDetail(BaseModel):
    code: str
    message: str

class MosoroPayload(BaseModel):
    position: Optional[Position] = None
    battery: Optional[float] = Field(None, ge=0.0, le=100.0)
    status: Optional[Literal["idle", "moving", "working", "charging", "error", "offline"]] = None
    current_task: Optional[CurrentTask] = None
    health: Optional[str] = None
    errors: Optional[List[ErrorDetail]] = None
    vendor_specific: Optional[Dict[str, Any]] = Field(default_factory=dict)

class MosoroMessage(BaseModel):
    model_config = ConfigDict(extra='forbid')

    header: MessageHeader = Field(default_factory=MessageHeader)
    robot_id: str
    vendor: Literal["locus", "stretch", "seer", "geekplus", "mir", "ur", "fetch", "other"]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    type: Literal["status", "event", "command", "traffic_update", "birth", "error"]
    payload: MosoroPayload = Field(default_factory=MosoroPayload)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
