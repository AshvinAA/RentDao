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
    # joinedload is used here because we want the full item object and all its
    # related collections (tags, images, reviews, insurance) in one DB trip.
    # owner uses an INNER JOIN equivalent (every item has an owner).
    # everything else uses a LEFT JOIN equivalent (may have none of these).
    item = (
        db.query(models.Item)
        .options(
            joinedload(models.Item.owner),
            joinedload(models.Item.tags),
            joinedload(models.Item.images),
            joinedload(models.Item.reviews),
            joinedload(models.Item.insurance_records),
        )
        .filter(models.Item.id == item_id)
        .first()
    )

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    today = date.today()

    # INNER JOIN: only care about bookings that actually have a matching item.
    # the subquery from the original is simplified into a direct end_date filter —
    # both do the same thing but this is easier to read.
    existing_booking = (
        db.query(models.Booking_details)
        .join(models.Item, models.Booking_details.item_id == models.Item.id)  # INNER JOIN
        .filter(
            models.Booking_details.item_id == item_id,
            models.Booking_details.user_id == current_user.id,
            models.Booking_details.status.in_(["pending", "approved"]),
            models.Booking_details.end_date >= today,
        )
        .first()
    )

    # LEFT JOIN (outerjoin): items with no reviews should still return a booking count,
    # so we can't use an inner join here — that would drop items with 0 reviews.
    stats = (
        db.query(
            func.count(models.Booking_details.id).label("total_bookings"),
            func.avg(models.Reviews.rating).label("avg_rating"),
        )
        .outerjoin(models.Reviews, models.Reviews.item_id == models.Booking_details.item_id)  # LEFT JOIN
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
        "existing_booking": existing_booking,
        "total_bookings": stats.total_bookings or 0,
        "avg_rating": round(float(stats.avg_rating), 1) if stats.avg_rating else 0.0,
        "user": current_user,
        "is_owner": is_owner,
        "today": today,
    })