from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, conint, confloat
from typing import Optional
from servo import ServoS90
from distance_monitor import DistanceMonitor

s = ServoS90(18)
dm = DistanceMonitor(echo_pin=24, trigger_pin=23)


# --- FastAPI app ---
app = FastAPI(title="TdA SFX test server")


# --- CORS (helps if you open the HTML from another origin/port or file://) ---
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
CORSMiddleware,
allow_origins=["*"], # lock this down later if you serve from a fixed origin
allow_credentials=False,
allow_methods=["POST", "GET", "OPTIONS"],
allow_headers=["*"]
)


# Serve ./static at /static and use it for the homepage
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=FileResponse)
def home():
    return FileResponse("static/index.html")


# --- Pydantic schema with validation ---
class ServoCommand(BaseModel):
    angle: conint(ge=0, le=180)
    sweep_time: confloat(ge=0.5, le=60)


@app.post("/api/servo")
async def set_servo(cmd: ServoCommand):
    global last_command
    last_command = cmd
    s.set_angle_sweep(cmd.angle, cmd.sweep_time)
    return cmd

@app.get("/api/distance")
async def get_distance():
    distance = dm.get_distance_cm()
    return {"distance": distance}

# Run with: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
