from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
import models
from database import get_db
from routers.auth import get_current_user

router = APIRouter(prefix="/reviews")
templates = Jinja2Templates(directory="templates")

@router.get("")  # matches /reviews exactly (because prefix is already "/reviews")
def all_reviews(
    request: Request,
    db: Session = Depends(get_db),
):
    reviews = (
        db.query(models.Reviews)
        .order_by(models.Reviews.review_id.desc())
        .all()
    )
    return templates.TemplateResponse("reviews.html", {
        "request": request,
        "reviews": reviews,
    })

@router.post("/create")
def create_review(
    booking_id: int = Form(...),
    rating: int = Form(...),
    comment: str = Form(""),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Validate rating
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    # Find the booking
    booking = (
        db.query(models.Booking_details)
        .filter(models.Booking_details.id == booking_id)
        .first()
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # Only completed bookings can be reviewed
    if booking.status != "completed":
        raise HTTPException(status_code=400, detail="Can only review completed bookings")

    # Only the renter can leave a review
    if booking.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Check if this booking was already reviewed by this user
    existing = (
        db.query(models.Reviews)
        .filter(
            models.Reviews.booking_id == booking_id,
            models.Reviews.reviewer_id == current_user.id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="You already reviewed this booking")

    new_review = models.Reviews(
        item_id=booking.item_id,
        booking_id=booking_id,
        reviewer_id=current_user.id,
        reviewee_id=booking.rentor_id,  # the item owner gets reviewed
        rating=rating,
        comment=comment,
    )
    db.add(new_review)

    # Update item's average rating
    _update_item_rating(db, booking.item_id)

    # Update owner's average rating
    _update_user_rating(db, booking.rentor_id)

    db.commit()

    return RedirectResponse(url="/bookings", status_code=303)

@router.get("/create")
def create_review_page(
    request: Request,
    booking_id: None,  # pass as query param e.g. /reviews/create?booking_id=1
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not booking_id:
        return RedirectResponse(url="/bookings", status_code=303)  # redirect if no booking specified

    booking = db.query(models.Booking_details).filter(
        models.Booking_details.id == booking_id
    ).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    return templates.TemplateResponse("create_review.html", {
        "request": request,
        "booking": booking,
        "user": current_user,
    })


@router.get("/item/{item_id}")
def item_reviews(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    reviews = (
        db.query(models.Reviews)
        .filter(models.Reviews.item_id == item_id)
        .order_by(models.Reviews.review_id.desc())
        .all()
    )
    return templates.TemplateResponse("item_reviews.html", {
        "request": request,
        "item": item,
        "reviews": reviews,
    })


@router.get("/user/{user_id}")
def user_reviews(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    reviews = (
        db.query(models.Reviews)
        .filter(models.Reviews.reviewee_id == user_id)
        .order_by(models.Reviews.review_id.desc())
        .all()
    )
    return templates.TemplateResponse("user_reviews.html", {
        "request": request,
        "reviewed_user": user,
        "reviews": reviews,
    })



def _update_item_rating(db: Session, item_id: int):
    avg = (
        db.query(func.avg(models.Reviews.rating))
        .filter(models.Reviews.item_id == item_id)
        .scalar()
    )
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if item:
        item.rating = round(float(avg), 1) if avg else 0.0



def _update_user_rating(db: Session, user_id: int):
    avg = (
        db.query(func.avg(models.Reviews.rating))
        .filter(models.Reviews.reviewee_id == user_id)
        .scalar()
    )
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        user.user_rating = round(float(avg), 1) if avg else 0.0