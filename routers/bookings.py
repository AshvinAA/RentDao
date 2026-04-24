from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import date
import models
from database import get_db
from routers.auth import get_current_user
 
router = APIRouter(prefix="/bookings")
templates = Jinja2Templates(directory="templates")

@router.get("/")
def bookings(request: Request, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    #items i am booking from other users
    my_rentals = (db.query(models.Booking_details).filter(models.Booking_details.user_id == current_user.id).order_by(models.Booking_details.start_date.desc()).all())
    #bookings on my items
    incoming_requests = (db.query(models.Booking_details).join(models.Item, models.Booking_details.item_id == models.Item.id).filter(models.Item.owner_id == current_user.id).order_by(models.Booking_details.start_date.desc()).all())
    return templates.TemplateResponse("bookings.html", {
        "request": request,
        "user": current_user,
        "my_rentals": my_rentals,
        "incoming_requests": incoming_requests,
    })
    
@router.post("/create/{item_id}")
def create_booking(
    item_id: int,
    start_date: str = Form(...),
    end_date: str = Form(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # searches db for the item
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if item.owner_id == current_user.id:
        return RedirectResponse(url=f"/items", status_code=303)
 
    try:
        s_date = date.fromisoformat(start_date)
        e_date = date.fromisoformat(end_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
 
    if e_date <= s_date:
        raise HTTPException(status_code=400, detail="End date must be after start date")
#overlap check just in case double booking occurs, but the item gets removed from the marketplace 
#when the item is initially booked so its only for edge cases and stuff
    overlap = (
        db.query(models.Booking_details)
        .filter(
            models.Booking_details.item_id == item_id,
            models.Booking_details.status.in_(["pending", "approved"]),
            models.Booking_details.start_date < e_date,
            models.Booking_details.end_date > s_date,
        )
        .first()
    )
    if overlap:
        raise HTTPException(status_code=400, detail="Item is already booked for those dates")

    num_days = (e_date - s_date).days
    price = item.price_per_day or 0
    discount = item.discount or 0
    total = int(num_days * price * (1 - discount / 100))
    new_booking = models.Booking_details(
        item_id=item_id,
        user_id=current_user.id,
        rentor_id=item.owner_id,
        start_date=s_date,
        end_date=e_date,
        total_price=total,
        status="pending",
    )
    db.add(new_booking)
    db.commit()
    return RedirectResponse(url="/bookings", status_code=303)
 
@router.post("/{booking_id}/approve")
def approve_booking(booking_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    booking = db.query(models.Booking_details).filter(models.Booking_details.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.item.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if booking.status != "pending":
        return RedirectResponse(url="/bookings", status_code=303)

    booking.status = "approved"
    
    #Creating the delivery history entry when the booking is approved
    new_delivery = models.Delivery_history(
        booking_id=booking.id,
        delivery_status="awaiting_admin", 
        pickup_location=booking.item.owner.location, # Where the owner lives
        dropoff_location=booking.user.location,      # Where the renter lives
        delivery_date=booking.start_date
    )
    db.add(new_delivery)
    
    db.commit()

    return RedirectResponse(url="/bookings", status_code=303)

@router.post("/{booking_id}/reject")
def reject_booking(booking_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    booking = db.query(models.Booking_details).filter(models.Booking_details.id == booking_id).first() #looking for the booking
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
 
    if booking.item.owner_id != current_user.id: #owner is the only one who can approve a booking
        raise HTTPException(status_code=403, detail="Not authorized")
 
    if booking.status != "pending":
        return RedirectResponse(url="/bookings", status_code=303)
 
    booking.status = "rejected"
    db.commit()
 
    return RedirectResponse(url="/bookings", status_code=303)

@router.post("/{booking_id}/cancel")
def cancel_booking(booking_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    booking = db.query(models.Booking_details).filter(models.Booking_details.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
 
    # Only the renter can cancel, and only if it's still pending or approved
    if booking.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
 
    if booking.status not in ["pending", "approved"]:
        return RedirectResponse(url="/bookings", status_code=303)
 
    booking.status = "cancelled"
    db.commit()
 
    return RedirectResponse(url="/bookings", status_code=303)

@router.post("/{booking_id}/complete")
def complete_booking(booking_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    booking = db.query(models.Booking_details).filter(models.Booking_details.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
 
    if booking.item.owner_id != current_user.id: #only the owener can mark a booking as complete after they are returned their item
        raise HTTPException(status_code=403, detail="Not authorized")
 
    if booking.status != "approved":
        return RedirectResponse(url="/bookings", status_code=303)
 
    booking.status = "completed"
    db.commit()
 
    return RedirectResponse(url="/bookings", status_code=303)