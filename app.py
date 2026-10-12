from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel, Field

app = FastAPI()

deliveries = {}
next_id = 1


class Delivery(BaseModel):
    recipient: str
    address: str = Field(min_length=1)


@app.get("/deliveries")
def list_deliveries(status: str | None = None):
    if status is not None:
        allowed_statuses = ["created", "in_transit", "delivered"]

        if status not in allowed_statuses:
            raise HTTPException(status_code=400, detail="Unknown status")

        return [
            delivery
            for delivery in deliveries.values()
            if delivery["status"] == status
        ]

    return list(deliveries.values())


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/deliveries", status_code=201)
def create_delivery(delivery: Delivery):
    global next_id

    new_delivery = {
        "id": next_id,
        "recipient": delivery.recipient,
        "address": delivery.address,
        "status": "created"
    }

    deliveries[next_id] = new_delivery
    next_id += 1

    return new_delivery


@app.get("/deliveries/{delivery_id}")
def get_delivery(delivery_id: int):
    if delivery_id not in deliveries:
        raise HTTPException(status_code=404, detail="Delivery not found")

    return deliveries[delivery_id]


class StatusUpdate(BaseModel):
    status: str


@app.patch("/deliveries/{delivery_id}/status")
def update_status(delivery_id: int, update: StatusUpdate):
    if delivery_id not in deliveries:
        raise HTTPException(status_code=404, detail="Delivery not found")

    delivery = deliveries[delivery_id]
    current_status = delivery["status"]
    new_status = update.status

    allowed_statuses = ["created", "in_transit", "delivered"]

    if new_status not in allowed_statuses:
        raise HTTPException(status_code=400, detail="Unknown status")

    if new_status == current_status:
        raise HTTPException(status_code=409, detail="Status is already set")

    allowed_transitions = {
        "created": ["in_transit"],
        "in_transit": ["delivered"],
        "delivered": []
    }

    if new_status not in allowed_transitions[current_status]:
        raise HTTPException(status_code=409, detail="Invalid status transition")

    delivery["status"] = new_status

    return delivery


@app.delete("/deliveries/{delivery_id}")
def delete_delivery(delivery_id: int):
    if delivery_id not in deliveries:
        raise HTTPException(status_code=404, detail="Delivery not found")

    if deliveries[delivery_id]["status"] == "delivered":
        raise HTTPException(status_code=409, detail="Cannot delete delivered delivery")

    del deliveries[delivery_id]

    return Response(status_code=204)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        {"error": exc.detail},
        status_code=exc.status_code
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        {"error": "Invalid request"},
        status_code=400
    )