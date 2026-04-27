from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, text
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
    
    # item = (
    #     db.query(models.Item) #in the items table
    #     .join(models.User, models.Item.owner_id == models.User.id)     #inner join the items to the users, ie the owners must exist for the item to be valid     
    #     .outerjoin(models.Item_Tags, models.Item_Tags.item_id == models.Item.id)     #left join to get all the tags for the item, this currently doesnt work
    #     .outerjoin(models.Item_Images, models.Item_Images.item_id == models.Item.id) #left join to get all the images of the item same logic as tags but this works 
    #     .outerjoin(models.Reviews, models.Reviews.item_id == models.Item.id) #left join to get all the reviews of the item, same as above but also doesnt work(?)         
    #     .outerjoin(models.Insurance, models.Insurance.item_id == models.Item.id) #last left join to get the insurance info, works  
    #     #we do left join to ensure that an item is always returned regardless of if it has tags, images, insurance, reviews. although it should be changed so that it wont be displayed if it doesnt have an image  
    #     .filter(models.Item.id == item_id).first()
    # )
    item = db.execute(
        text("""
            SELECT i.*, u.email AS owner_email, u.location AS owner_location
            FROM items i
            JOIN users u ON i.owner_id = u.id
            WHERE i.id = :iid
        """),
        {"iid": item_id}
    ).fetchone()

    #btw this may cause issues if the database is hella populated or sth. idk the fix but it exists. have to implement this later maybe(?)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # fetch tags separately (outerjoin on tags didnt work in the ORM either)
    tags = db.execute(
        text("SELECT * FROM item_tags WHERE item_id = :iid"),
        {"iid": item_id}
    ).fetchall()

    # fetch images separately
    images = db.execute(
        text("SELECT * FROM item_images WHERE item_id = :iid"),
        {"iid": item_id}
    ).fetchall()

    # fetch reviews separately, JOIN users to get reviewer email for the template (review.reviewer.email)
    reviews = db.execute(
        text("""
            SELECT r.*, u.email AS reviewer_email
            FROM reviews r
            JOIN users u ON r.reviewer_id = u.id
            WHERE r.item_id = :iid
        """),
        {"iid": item_id}
    ).fetchall()

    # fetch insurance records separately
    insurance_records = db.execute(
        text("SELECT * FROM insurance WHERE item_id = :iid"),
        {"iid": item_id}
    ).fetchall()

    today = date.today()

    #subquery to find all the active bookings in the db
    # active_booking_ids = (
    #     db.query(models.Booking_details.id)
    #     .filter(models.Booking_details.end_date >= today)  # Only bookings ending today or later
    #     .subquery()
    # )

    #query using the subquery to check if the specific user has a booking open for a specific item
    # existing_booking = (
    #     db.query(models.Booking_details)
    #     .join(models.Item, models.Booking_details.item_id == models.Item.id)  # INNER JOIN
    #     .filter(
    #         models.Booking_details.item_id == item_id,  # Booking must be for this item
    #         models.Booking_details.user_id == current_user.id,  # Booking must be by current user
    #         models.Booking_details.status.in_(["pending", "approved"]),  # Status must be pending or approved (not declined/cancelled)
    #         models.Booking_details.id.in_(active_booking_ids),  # Booking must not be expired (use the subquery)
    #     )
    #     .first() 
    # )
    existing_booking = db.execute(
        text("""
            SELECT bd.*
            FROM booking_details bd
            JOIN items i ON bd.item_id = i.id
            WHERE bd.item_id = :iid
            AND bd.user_id = :uid
            AND bd.status IN ('pending', 'approved')
            AND bd.end_date >= :today
        """),
        {"iid": item_id, "uid": current_user.id, "today": today}
    ).fetchone()

    # LEFT JOIN (outerjoin): items with no reviews should still return a booking count,
    # so we can't use an inner join here — that would drop items with 0 reviews.
    # stats = (
    #     db.query(
    #         func.count(models.Booking_details.id).label("total_bookings"),
    #         func.avg(models.Reviews.rating).label("avg_rating"),
    #     )
    #     .outerjoin(models.Reviews, models.Reviews.item_id == models.Booking_details.item_id)  # LEFT JOIN
    #     .filter(
    #         models.Booking_details.item_id == item_id,
    #         models.Booking_details.status == "completed",
    #     )
    #     .first()
    # )
    stats = db.execute(
        text("""
            SELECT COUNT(bd.id) AS total_bookings, AVG(r.rating) AS avg_rating
            FROM booking_details bd
            LEFT JOIN reviews r ON r.item_id = bd.item_id
            WHERE bd.item_id = :iid
            AND bd.status = 'completed'
        """),
        {"iid": item_id}
    ).fetchone()

    is_owner = item.owner_id == current_user.id

    return templates.TemplateResponse("item_details.html", {
        "request": request,
        "item": item,
        "owner": item,           # item row already has owner_email, owner_location from the JOIN above
        "tags": tags,
        "images": images,
        "reviews": reviews,
        "insurance_records": insurance_records,
        "existing_booking": existing_booking,
        "total_bookings": stats.total_bookings or 0,
        "avg_rating": round(float(stats.avg_rating), 1) if stats.avg_rating else 0.0,
        "user": current_user,
        "is_owner": is_owner,
        "today": today,
    })