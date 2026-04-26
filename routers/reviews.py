from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import text, func
import models
from database import get_db
from routers.auth import get_current_user

router = APIRouter(prefix="/reviews")
templates = Jinja2Templates(directory="templates")


@router.get("")  # matches /reviews exactly
def all_reviews(
    request: Request,
    db: Session = Depends(get_db),
):
    # reviews = (
    #     db.query(models.Reviews)
    #     .order_by(models.Reviews.review_id.desc())
    #     .all()
    # )
    reviews = db.execute(
        text("SELECT * FROM reviews ORDER BY review_id DESC")
    ).fetchall()

    return templates.TemplateResponse("reviews.html", {
        "request": request,
        "reviews": reviews,
    })


@router.get("/booking/{booking_id}")  # view/manage the review for a specific booking
def booking_review(
    booking_id: int,
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # booking = db.query(models.Booking_details).filter(
    #     models.Booking_details.id == booking_id
    # ).first()
    booking = db.execute(
        text("SELECT * FROM booking_details WHERE id = :bid"),
        {"bid": booking_id}
    ).fetchone()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # review = (
    #     db.query(models.Reviews)
    #     .filter(
    #         models.Reviews.booking_id == booking_id,
    #         models.Reviews.reviewer_id == current_user.id,
    #     )
    #     .first()
    # )
    review = db.execute(
        text("""
            SELECT * FROM reviews
            WHERE booking_id = :bid AND reviewer_id = :uid
        """),
        {"bid": booking_id, "uid": current_user.id}
    ).fetchone()

    # if no review exists yet, redirect straight to the create page
    if not review:
        return RedirectResponse(url=f"/reviews/create?booking_id={booking_id}", status_code=302)

    return templates.TemplateResponse("booking_review.html", {
        "request": request,
        "booking": booking,
        "review": review,
        "user": current_user,
    })


@router.get("/create")  # /reviews/create?booking_id=1
def create_review_page(
    request: Request,
    booking_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # booking = db.query(models.Booking_details).filter(
    #     models.Booking_details.id == booking_id
    # ).first()
    booking = db.execute(
        text("SELECT * FROM booking_details WHERE id = :bid"),
        {"bid": booking_id}
    ).fetchone()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # if already reviewed, send them to the review management page instead
    # existing = (
    #     db.query(models.Reviews)
    #     .filter(
    #         models.Reviews.booking_id == booking_id,
    #         models.Reviews.reviewer_id == current_user.id,
    #     )
    #     .first()
    # )
    existing = db.execute(
        text("""
            SELECT review_id FROM reviews
            WHERE booking_id = :bid AND reviewer_id = :uid
        """),
        {"bid": booking_id, "uid": current_user.id}
    ).fetchone()

    if existing:
        return RedirectResponse(url=f"/reviews/booking/{booking_id}", status_code=302)

    return templates.TemplateResponse("create_review.html", {
        "request": request,
        "booking": booking,
        "user": current_user,
    })


@router.post("/create")
def create_review(
    booking_id: int = Form(...),
    rating: int = Form(...),
    comment: str = Form(""),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    # booking = (
    #     db.query(models.Booking_details)
    #     .filter(models.Booking_details.id == booking_id)
    #     .first()
    # )
    booking = db.execute(
        text("SELECT * FROM booking_details WHERE id = :bid"),
        {"bid": booking_id}
    ).fetchone()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.status != "completed":
        raise HTTPException(status_code=400, detail="Can only review completed bookings")

    if booking.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # existing = (
    #     db.query(models.Reviews)
    #     .filter(
    #         models.Reviews.booking_id == booking_id,
    #         models.Reviews.reviewer_id == current_user.id,
    #     )
    #     .first()
    # )
    existing = db.execute(
        text("""
            SELECT review_id FROM reviews
            WHERE booking_id = :bid AND reviewer_id = :uid
        """),
        {"bid": booking_id, "uid": current_user.id}
    ).fetchone()
    if existing:
        raise HTTPException(status_code=400, detail="You already reviewed this booking")

    # new_review = models.Reviews(
    #     item_id=booking.item_id,
    #     booking_id=booking_id,
    #     reviewer_id=current_user.id,
    #     reviewee_id=booking.rentor_id,
    #     rating=rating,
    #     comment=comment,
    # )
    # db.add(new_review)
    db.execute(
        text("""
            INSERT INTO reviews (item_id, booking_id, reviewer_id, reviewee_id, rating, comment)
            VALUES (:item_id, :booking_id, :reviewer_id, :reviewee_id, :rating, :comment)
        """),
        {
            "item_id": booking.item_id,
            "booking_id": booking_id,
            "reviewer_id": current_user.id,
            "reviewee_id": booking.rentor_id,
            "rating": rating,
            "comment": comment,
        }
    )

    _update_item_rating(db, booking.item_id)
    _update_user_rating(db, booking.rentor_id)

    db.commit()

    # redirect to the review management page after submitting
    return RedirectResponse(url=f"/reviews/booking/{booking_id}", status_code=303)


@router.post("/{review_id}/edit")
def edit_review(
    review_id: int,
    rating: int = Form(...),
    comment: str = Form(""),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # review = db.query(models.Reviews).filter(models.Reviews.review_id == review_id).first()
    review = db.execute(
        text("SELECT * FROM reviews WHERE review_id = :rid"),
        {"rid": review_id}
    ).fetchone()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    if review.reviewer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    # review.rating = rating
    # review.comment = comment
    db.execute(
        text("UPDATE reviews SET rating = :rating, comment = :comment WHERE review_id = :rid"),
        {"rating": rating, "comment": comment, "rid": review_id}
    )

    # recalculate averages since rating may have changed
    _update_item_rating(db, review.item_id)
    _update_user_rating(db, review.reviewee_id)

    db.commit()

    return RedirectResponse(url=f"/reviews/booking/{review.booking_id}", status_code=303)


@router.post("/{review_id}/delete")
def delete_review(
    review_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # review = db.query(models.Reviews).filter(models.Reviews.review_id == review_id).first()
    review = db.execute(
        text("SELECT * FROM reviews WHERE review_id = :rid"),
        {"rid": review_id}
    ).fetchone()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    if review.reviewer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # store these before deleting so we can update averages after
    item_id = review.item_id
    reviewee_id = review.reviewee_id

    # db.delete(review)
    db.execute(
        text("DELETE FROM reviews WHERE review_id = :rid"),
        {"rid": review_id}
    )
    db.commit()

    _update_item_rating(db, item_id)
    _update_user_rating(db, reviewee_id)

    return RedirectResponse(url="/profile", status_code=303)


@router.get("/item/{item_id}")
def item_reviews(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    # item = db.query(models.Item).filter(models.Item.id == item_id).first()
    item = db.execute(
        text("SELECT * FROM items WHERE id = :iid"),
        {"iid": item_id}
    ).fetchone()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # reviews = (
    #     db.query(models.Reviews)
    #     .filter(models.Reviews.item_id == item_id)
    #     .order_by(models.Reviews.review_id.desc())
    #     .all()
    # )
    reviews = db.execute(
        text("SELECT * FROM reviews WHERE item_id = :iid ORDER BY review_id DESC"),
        {"iid": item_id}
    ).fetchall()

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
    # user = db.query(models.User).filter(models.User.id == user_id).first()
    user = db.execute(
        text("SELECT * FROM users WHERE id = :uid"),
        {"uid": user_id}
    ).fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # reviews = (
    #     db.query(models.Reviews)
    #     .filter(models.Reviews.reviewee_id == user_id)
    #     .order_by(models.Reviews.review_id.desc())
    #     .all()
    # )
    reviews = db.execute(
        text("SELECT * FROM reviews WHERE reviewee_id = :uid ORDER BY review_id DESC"),
        {"uid": user_id}
    ).fetchall()

    return templates.TemplateResponse("user_reviews.html", {
        "request": request,
        "reviewed_user": user,
        "reviews": reviews,
    })


# --- Rating helpers ---

def _update_item_rating(db: Session, item_id: int):
    # avg = (
    #     db.query(func.avg(models.Reviews.rating))
    #     .filter(models.Reviews.item_id == item_id)
    #     .scalar()
    # )
    # item = db.query(models.Item).filter(models.Item.id == item_id).first()
    # if item:
    #     item.rating = round(float(avg), 1) if avg else 0.0
    result = db.execute(
        text("SELECT AVG(rating) AS avg_rating FROM reviews WHERE item_id = :iid"),
        {"iid": item_id}
    ).fetchone()
    avg = result.avg_rating if result else None
    db.execute(
        text("UPDATE items SET rating = :rating WHERE id = :iid"),
        {"rating": round(float(avg), 1) if avg else 0.0, "iid": item_id}
    )


def _update_user_rating(db: Session, user_id: int):
    # avg = (
    #     db.query(func.avg(models.Reviews.rating))
    #     .filter(models.Reviews.reviewee_id == user_id)
    #     .scalar()
    # )
    # user = db.query(models.User).filter(models.User.id == user_id).first()
    # if user:
    #     user.user_rating = round(float(avg), 1) if avg else 0.0
    result = db.execute(
        text("SELECT AVG(rating) AS avg_rating FROM reviews WHERE reviewee_id = :uid"),
        {"uid": user_id}
    ).fetchone()
    avg = result.avg_rating if result else None
    db.execute(
        text("UPDATE users SET user_rating = :rating WHERE id = :uid"),
        {"rating": round(float(avg), 1) if avg else 0.0, "uid": user_id}
    )