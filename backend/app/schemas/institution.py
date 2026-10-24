from typing import Optional
from pydantic import BaseModel, ConfigDict

class InstitutionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    code: str
    state: str
    status: str

class ProgrammeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    institution_id: str
    name: str
    degree_level: str
    duration_years: int

class ApprovedIntakeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    institution_id: str
    programme_id: str
    programme_name: Optional[str] = None
    academic_year: str
    regular_intake: int
    supernumerary_intake: int
    total_approved_intake: int
    supernumerary_policy: Optional[str] = None
