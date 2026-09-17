from pydantic import BaseModel
from typing import List, Optional
from app.models.user import UserRole

class BulkUserImportRequest(BaseModel):
    users: List[dict]
    password_prefix: Optional[str] = "Exam@"
    
class BulkUserImportResponse(BaseModel):
    status: str
    count: int
