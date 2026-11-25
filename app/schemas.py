from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator, AwareDatetime, model_validator

class ActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    strava_activity_id: int | None = None
    start_time: datetime
    activity_type: str
    distance_m: float = Field(validation_alias="distance", serialization_alias="distance_m")
    elapsed_time_s: int = Field(validation_alias="elapsed_time", serialization_alias="elapsed_time_s")
    moving_time_s: int = Field(validation_alias="moving_time", serialization_alias="moving_time_s")
    elevation_gain_m: float | None = Field(None, validation_alias="elevation_gain", serialization_alias="elevation_gain_m")
    elevation_loss_m: float | None = Field(None, validation_alias="elevation_loss", serialization_alias="elevation_loss_m")
    avg_heartrate: int | None = None
    max_heartrate: int | None = None
    calories: int | None = None
    steps: int | None = None
    
class ActivityCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_time: AwareDatetime
    activity_type: str = Field(min_length=1)
    distance_m: float = Field(gt=0)
    elapsed_time_s: int = Field(gt=0)
    moving_time_s: int = Field(gt=0)
    elevation_gain_m: float | None  = Field(None, ge=0)
    avg_heartrate: int | None = Field(None, gt=0)
    max_heartrate: int | None = Field(None, gt=0)
    strava_activity_id: int | None = Field(None, gt=0)
    elevation_loss_m: float | None = Field(None, ge=0)
    calories: int | None = Field(None, gt=0)
    steps: int | None = Field(None, gt=0)

    @model_validator(mode="after")
    def check_times(self):        
        if self.moving_time_s > self.elapsed_time_s:
            raise ValueError("Moving Time Cannot Exceed Elapsed Time")
        return self

class ActivityUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Non-nullable on Activity (can be omitted in PATCH, cannot be set to NULL)
    start_time: AwareDatetime | None = None
    activity_type: str | None = Field(None, min_length=1)
    distance_m: float | None = Field(None, gt=0)  
    elapsed_time_s: int | None = Field(None, gt=0)
    moving_time_s: int | None = Field(None, gt=0)

    # Nullable on Activity (can be omitted in PATCH, can be set to NULL)
    elevation_gain_m: float | None = Field(None, ge=0)
    avg_heartrate: int | None = Field(None, gt=0)
    max_heartrate: int | None = Field(None, gt=0)
    elevation_loss_m: float | None = Field(None, ge=0)
    calories: int | None = Field(None, gt=0)
    steps: int | None = Field(None, gt=0)

    @field_validator(
        "start_time",
        "activity_type",
        "distance_m",
        "elapsed_time_s",
        "moving_time_s"
    )
    @classmethod
    def reject_null_on_required_fields(cls, value):
        if value is None:
            raise ValueError("Field Cannot Be Null")
        return value
