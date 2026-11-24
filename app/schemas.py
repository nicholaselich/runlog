from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class ActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    start_time: datetime
    activity_type: str
    distance_m: float = Field(validation_alias="distance", serialization_alias="distance_m")
    elapsed_time_s: int = Field(validation_alias="elapsed_time", serialization_alias="elapsed_time_s")
    moving_time_s: int = Field(validation_alias="moving_time", serialization_alias="moving_time_s")
    elevation_gain_m: float | None = Field(validation_alias="elevation_gain", serialization_alias="elevation_gain_m")
    avg_heartrate: int | None = None
    max_heartrate: int | None = None
    
