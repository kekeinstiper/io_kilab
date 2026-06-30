from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import psycopg2, os
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

load_dotenv()
app = FastAPI(title="IoT Server API", version="1.0")

app.add_middleware(
CORSMiddleware,
allow_origins=["*"], # untuk development; nanti bisa dibatasi
allow_credentials=True,
allow_methods=["*"],
allow_headers=["*"],
)


# Database connection
def get_db():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise HTTPException(status_code=500, detail="DATABASE_URL tidak ditemukan")
    return psycopg2.connect(database_url)

# Model Data
class SensorData(BaseModel):
    device_id: str = "esp32-001"
    sensor1: float
    sensor2: float
    sensor3: float

# Endpoint 1 : Terima data sensor dari ESP32
@app.post("/sensor")
def post_sensor(data: SensorData):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO sensor_data (device_id, sensor1, sensor2, sensor3) "
            "VALUES (%s, %s, %s, %s)",
            (data.device_id, data.sensor1, data.sensor2, data.sensor3)
        )
        conn.commit()
        cur.close()
        conn.close()
        return {"status": "ok", "message": "Data sensor tersimpan"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint 2 : Kirim status relay ke ESP32
@app.get("/relay/{relay_name}")
def get_relay(relay_name: str):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "SELECT status FROM relay_control WHERE relay_name = %s",
            (relay_name,)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row is None:
            raise HTTPException(status_code=404, detail="Relay tidak ditemukan")
        return {"relay_name": relay_name, "status": row[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# Endpoint 3 : ubah status relay dari dashboard
@app.put("/relay/{relay_name}")
def set_relay(relay_name: str, status: bool, updated_by: str = "manual"):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "UPDATE relay_control SET status=%s, updated_at=NOW(), updated_by=%s "
            "WHERE relay_name=%s",
            (status, updated_by, relay_name)
        )
        conn.commit()
        cur.close()
        conn.close()
        return {"status": "ok", "relay": relay_name, "new_status": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# Endpoint 4 : Lihat data sensor terbaru dari database    
@app.get("/sensor/latest")
def get_latest(limit: int = 10):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "SELECT id,device_id,sensor1,sensor2,sensor3,timestamp "
            "FROM sensor_data ORDER BY timestamp DESC LIMIT %s", (limit,)
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        cols = ["id","device_id","sensor1","sensor2","sensor3","timestamp"]
        return [dict(zip(cols, r)) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# Endpoint 5 : Lihat data sensor untuk chart (hanya sensor1, sensor2, sensor3, timestamp)
@app.get("/sensor/chart")
def get_sensor_for_chart(limit: int = 50):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "SELECT sensor1, sensor2, sensor3, timestamp "
            "FROM sensor_data ORDER BY timestamp DESC LIMIT %s", (limit,)
        )
        rows = cur.fetchall()
        cur.close(); conn.close()
        # Balik urutan agar yang lama duluan (untuk grafik kiri ke kanan)
        rows.reverse()
        return [
            {
                "sensor1": r[0], "sensor2": r[1], "sensor3": r[2],
                "timestamp": r[3].strftime("%H:%M:%S")
            }
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))    