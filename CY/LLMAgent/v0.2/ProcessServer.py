from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class ProcessLog(BaseModel):
    timestamp: str
    event_type: str
    event_status: str
    available: bool
    
@app.post("/log")
def log_process(data: ProcessLog):
    print(f"[{data.timestamp}] {data.event_type} - {data.event_status}: {data.available}")