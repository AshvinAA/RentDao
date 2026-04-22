from fastapi import APIRouter, Request, Depends, Cookie, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import models
from database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/payments")
def get_payments(request: Request, user_email: str = Cookie(None), db: Session = Depends(get_db)):
    if not user_email:
        return RedirectResponse(url="/login?error=You aren't logged in.", status_code=303)

    user = db.query(models.User).filter(models.User.email == user_email).first()

    payments_received = db.query(models.Payment).filter(models.Payment.owner_id == user.id).all()

    payments_made = (
        db.query(models.Payment)
        .join(models.Booking_details, models.Payment.booking_id == models.Booking_details.id)
        .filter(models.Booking_details.user_id == user.id)
        .all()
    )

    return templates.TemplateResponse("payments.html", {
        "request": request,
        "payments_received": payments_received,
        "payments_made": payments_made,
        "user": user
    })


@router.post("/payments/create/{booking_id}")
def create_payment(
    booking_id: int,
    payment_method: str = Form(...),
    payment_details: str = Form(default=""),
    user_email: str = Cookie(None),
    db: Session = Depends(get_db)
):
    if not user_email:
        return RedirectResponse(url="/login?error=You aren't logged in.", status_code=303)

    user = db.query(models.User).filter(models.User.email == user_email).first()
    booking = db.query(models.Booking_details).filter(models.Booking_details.id == booking_id).first()

    if not booking:
        return RedirectResponse(url="/payments?error=Booking not found.", status_code=303)

    if booking.user_id != user.id:
        return RedirectResponse(url="/payments?error=You are not the renter for this booking.", status_code=303)

    if booking.status != "approved":
        return RedirectResponse(url="/payments?error=Booking must be approved before payment.", status_code=303)

    already_paid = db.query(models.Payment).filter(
        models.Payment.booking_id == booking_id,
        models.Payment.payment_status == "completed"
    ).first()
    if already_paid:
        return RedirectResponse(url="/payments?error=This booking has already been paid for.", status_code=303)

    new_payment = models.Payment(
        booking_id=booking_id,
        owner_id=booking.item.owner_id,
        amount=booking.total_price,
        payment_method=payment_method,
        payment_details=payment_details,
        payment_status="pending"
    )
    db.add(new_payment)
    db.commit()

    return RedirectResponse(url="/payments", status_code=303)


@router.post("/payments/complete/{payment_id}")
def complete_payment(payment_id: int, user_email: str = Cookie(None), db: Session = Depends(get_db)):
    if not user_email:
        return RedirectResponse(url="/login?error=You aren't logged in.", status_code=303)

    user = db.query(models.User).filter(models.User.email == user_email).first()
    payment = db.query(models.Payment).filter(models.Payment.id == payment_id).first()

    if not payment:
        return RedirectResponse(url="/payments?error=Payment not found.", status_code=303)

    if payment.booking.user_id != user.id:
        return RedirectResponse(url="/payments?error=You are not authorized to complete this payment.", status_code=303)

    if payment.payment_status == "completed":
        return RedirectResponse(url="/payments?error=Payment is already completed.", status_code=303)

    payment.payment_status = "completed"
    db.commit()

    return RedirectResponse(url="/payments", status_code=303)


@router.post("/payments/fail/{payment_id}")
def fail_payment(payment_id: int, user_email: str = Cookie(None), db: Session = Depends(get_db)):
    if not user_email:
        return RedirectResponse(url="/login?error=You aren't logged in.", status_code=303)

    user = db.query(models.User).filter(models.User.email == user_email).first()
    payment = db.query(models.Payment).filter(models.Payment.id == payment_id).first()

    if not payment:
        return RedirectResponse(url="/payments?error=Payment not found.", status_code=303)

    if payment.booking.user_id != user.id:
        return RedirectResponse(url="/payments?error=You are not authorized to update this payment.", status_code=303)

    if payment.payment_status == "completed":
        return RedirectResponse(url="/payments?error=Cannot mark a completed payment as failed.", status_code=303)

    payment.payment_status = "failed"
    db.commit()

    return RedirectResponse(url="/payments", status_code=303)