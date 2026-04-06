from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor

router = APIRouter()

# ---- DB CONFIG ----
DB_CONFIG = {
    "host": "localhost",
    "database": "postgres",
    "user": "postgres",
    "password": "postgres"
}


# ---- Request Model ----
class TableRequest(BaseModel):
    schema_name: str
    table_name: str


# ---- API Endpoint ----
@router.post("/get-columns")
def get_columns(payload: TableRequest):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        query = """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = %s
            AND table_name = %s
            ORDER BY ordinal_position
        """

        cursor.execute(query, (payload.schema_name, payload.table_name))
        result = cursor.fetchall()

        cursor.close()
        conn.close()

        if not result:
            raise HTTPException(status_code=404, detail="Table not found or no columns available")

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))