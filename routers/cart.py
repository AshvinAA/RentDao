from fastapi import APIRouter, Request, Depends, Cookie
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import models
from database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/cart")
def get_cart(request: Request, user_email: str = Cookie(None), db: Session = Depends(get_db)):
    if not user_email:
        return RedirectResponse(url="/login?error=You aren't logged in.", status_code=303)

    user = db.query(models.User).filter(models.User.email == user_email).first()
    cart_entries = db.query(models.Cart).filter(models.Cart.user_id == user.id).all()

    total_price_per_day = sum(
        entry.item.price_per_day for entry in cart_entries if entry.item and entry.item.price_per_day
    )

    return templates.TemplateResponse("cart.html", {
        "request": request,
        "cart_entries": cart_entries,
        "total_price_per_day": total_price_per_day,
        "user": user
    })


@router.post("/cart/add/{item_id}")
def add_to_cart(item_id: int, user_email: str = Cookie(None), db: Session = Depends(get_db)):
    if not user_email:
        return RedirectResponse(url="/login?error=You aren't logged in.", status_code=303)

    user = db.query(models.User).filter(models.User.email == user_email).first()
    item = db.query(models.Item).filter(models.Item.id == item_id).first()

    if not item:
        return RedirectResponse(url="/items?error=Item not found.", status_code=303)

    if item.owner_id == user.id:
        return RedirectResponse(url="/items?error=You cannot add your own item to your cart.", status_code=303)

    if not item.is_available:
        return RedirectResponse(url="/items?error=This item is currently unavailable.", status_code=303)

    if not item.is_approved:
        return RedirectResponse(url="/items?error=This item has not been approved yet.", status_code=303)

    already_exists = db.query(models.Cart).filter(
        models.Cart.user_id == user.id,
        models.Cart.item_id == item_id
    ).first()

    if not already_exists:
        new_entry = models.Cart(user_id=user.id, item_id=item_id)
        db.add(new_entry)
        db.commit()

    return RedirectResponse(url="/cart", status_code=303)


@router.post("/cart/remove/{item_id}")
def remove_from_cart(item_id: int, user_email: str = Cookie(None), db: Session = Depends(get_db)):
    if not user_email:
        return RedirectResponse(url="/login?error=You aren't logged in.", status_code=303)

    user = db.query(models.User).filter(models.User.email == user_email).first()
    entry = db.query(models.Cart).filter(
        models.Cart.user_id == user.id,
        models.Cart.item_id == item_id
    ).first()

    if entry:
        db.delete(entry)
        db.commit()

    return RedirectResponse(url="/cart", status_code=303)


@router.post("/cart/clear")
def clear_cart(user_email: str = Cookie(None), db: Session = Depends(get_db)):
    if not user_email:
        return RedirectResponse(url="/login?error=You aren't logged in.", status_code=303)

    user = db.query(models.User).filter(models.User.email == user_email).first()
    db.query(models.Cart).filter(models.Cart.user_id == user.id).delete()
    db.commit()

    return RedirectResponse(url="/cart", status_code=303)