from datetime import datetime, timezone
from typing import Any, List, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator

app = FastAPI()

flights_db = [
    {
        "id": 1,
        "flight_number": "VN-213",
        "destination": "Da Nang",
        "available_seats": 45,
        "status": "scheduled",
        "created_at": "2026-07-01T06:00:00Z",
    },
    {
        "id": 2,
        "flight_number": "VJ-122",
        "destination": "Phu Quoc",
        "available_seats": 12,
        "status": "scheduled",
        "created_at": "2026-07-01T07:30:00Z",
    },
]


class FlightCreate(BaseModel):
    flight_number: str = Field(
        ...,
        title="Flight number",
        min_length=5,
        max_length=10,
        pattern=r"^[A-Z]{2}-\d{3}$",
        example="QH-244",
    )
    destination: str = Field(..., min_length=1, example="Ha Noi")
    available_seats: int = Field(..., gt=0, le=500, example=180)

    @field_validator("flight_number", "destination")
    def strip_and_not_empty(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Giá trị không được để trống")
        return normalized


class Flight(BaseModel):
    id: int
    flight_number: str
    destination: str
    available_seats: int
    status: str
    created_at: str


class ResponseEnvelope(BaseModel):
    statusCode: int
    message: str
    data: Optional[Any]
    error: Optional[str]
    timestamp: str
    path: str


def current_utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def build_response(
    status_code: int,
    message: str,
    data: Optional[Any],
    error: Optional[str],
    path: str,
) -> ResponseEnvelope:
    return ResponseEnvelope(
        statusCode=status_code,
        message=message,
        data=data,
        error=error,
        timestamp=current_utc_timestamp(),
        path=path,
    )


@app.get("/flights", response_model=ResponseEnvelope)
async def list_flights(request: Request, status: Optional[str] = Query(None)):
    if status is None:
        result = flights_db.copy()
    else:
        normalized_status = status.strip().lower()
        result = [
            flight
            for flight in flights_db
            if flight["status"].lower() == normalized_status
        ]
    return build_response(
        status_code=200,
        message="Lấy danh sách chuyến bay thành công!",
        data=result,
        error=None,
        path=request.url.path,
    )


@app.post("/flights", status_code=201, response_model=ResponseEnvelope)
async def create_flight(request: Request, payload: FlightCreate):
    flight_number = payload.flight_number
    if any(
        flight["flight_number"].lower() == flight_number.lower()
        for flight in flights_db
    ):
        raise HTTPException(
            status_code=400,
            detail=build_response(
                status_code=400,
                message="Lỗi: Số hiệu chuyến bay này đã tồn tại trên hệ thống điều hành!",
                data=None,
                error="ERR-AIR-01: Flight number conflict in current active schedule database.",
                path=request.url.path,
            ).model_dump(),
        )

    next_id = max((flight["id"] for flight in flights_db), default=0) + 1
    flight_record = Flight(
        id=next_id,
        flight_number=flight_number,
        destination=payload.destination,
        available_seats=payload.available_seats,
        status="scheduled",
        created_at=current_utc_timestamp(),
    ).model_dump()
    flights_db.append(flight_record)

    return build_response(
        status_code=201,
        message="Khởi tạo chuyến bay mới thành công!",
        data=flight_record,
        error=None,
        path=request.url.path,
    )


@app.delete("/flights/{flight_id}", response_model=ResponseEnvelope)
async def delete_flight(request: Request, flight_id: int):
    for index, flight in enumerate(flights_db):
        if flight["id"] == flight_id:
            flights_db.pop(index)
            return build_response(
                status_code=200,
                message="Hủy chuyến bay thành công!",
                data=None,
                error=None,
                path=request.url.path,
            )

    raise HTTPException(
        status_code=404,
        detail=build_response(
            status_code=404,
            message="Lỗi: Không tìm thấy mã chuyến bay yêu cầu để hủy!",
            data=None,
            error="ERR-AIR-02: Target flight ID is missing from system scope.",
            path=request.url.path,
        ).model_dump(),
    )

