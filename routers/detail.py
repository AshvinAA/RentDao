from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
import models
from database import get_db
from routers.auth import get_current_user
from datetime import date

router = APIRouter(prefix="/items")
templates = Jinja2Templates(directory="templates")


@router.get("/{item_id}")
def detail(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    
    item = (
        db.query(models.Item)
        .join(models.User, models.Item.owner_id == models.User.id)          
        .outerjoin(models.Item_Tags, models.Item_Tags.item_id == models.Item.id)     
        .outerjoin(models.Item_Images, models.Item_Images.item_id == models.Item.id) 
        .outerjoin(models.Reviews, models.Reviews.item_id == models.Item.id)         
        .outerjoin(models.Insurance, models.Insurance.item_id == models.Item.id)     
        .filter(models.Item.id == item_id)
        .options(
            joinedload(models.Item.owner),
            joinedload(models.Item.tags),
            joinedload(models.Item.images),
            joinedload(models.Item.reviews),
            joinedload(models.Item.insurance_records),
        )
        .first()
    )

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    today = date.today()

    active_booking_ids = (                          # ← inner / nested query
        db.query(models.Booking_details.id)
        .filter(models.Booking_details.end_date >= today)
        .subquery()
    )

    existing_booking = (                            # ← outer query uses subquery
        db.query(models.Booking_details)
        .filter(
            models.Booking_details.item_id == item_id,
            models.Booking_details.user_id == current_user.id,
            models.Booking_details.status.in_(["pending", "approved"]),
            models.Booking_details.id.in_(active_booking_ids),
        )
        .first()
    )

    stats = (
        db.query(
            func.count(models.Booking_details.id).label("total_bookings"),
            func.avg(models.Reviews.rating).label("avg_rating"),
        )
        .outerjoin(models.Reviews, models.Reviews.item_id == models.Booking_details.item_id)
        .filter(
            models.Booking_details.item_id == item_id,
            models.Booking_details.status == "completed",
        )
        .first()
    )

    is_owner = item.owner_id == current_user.id

    return templates.TemplateResponse("item_details.html", {
        "request": request,
        "item": item,
        "owner": item.owner,
        "tags": item.tags,
        "images": item.images,
        "reviews": item.reviews,
        "insurance_records": item.insurance_records,
        "existing_booking": existing_booking,   # None if no active booking
        "total_bookings": stats.total_bookings or 0,
        "avg_rating": round(float(stats.avg_rating), 1) if stats.avg_rating else 0.0,
        "user": current_user,
        "is_owner": is_owner,
        "today": today,
    })
