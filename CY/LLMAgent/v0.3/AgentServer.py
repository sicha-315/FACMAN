from fastapi import FastAPI
from pydantic import BaseModel
import datetime

app = FastAPI()

class IsMaintain(BaseModel):
    runtime: float
    failure_rate: float
    
@app.post("/IsMaintain")
def IsMaintain(data: IsMaintain):
    result = {
        "need_maintenance": data.failure_rate > 0.15
    }
    print(f"[{datetime.datetime.now()}] Agent decision:", result["need_maintenance"])
    return {"need_maintenance": result["need_maintenance"]}