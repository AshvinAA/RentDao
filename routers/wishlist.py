from fastapi import APIRouter, Request, Depends, Cookie
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import models
from database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/wishlist")
def get_wishlist(request: Request, user_email: str = Cookie(None), db: Session = Depends(get_db)):
    if not user_email:
        return RedirectResponse(url="/login?error=You aren't logged in.", status_code=303)
    user = db.query(models.User).filter(models.User.email == user_email).first()
    wishlist_entries = db.query(models.Wishlist).filter(models.Wishlist.user_id == user.id).all()
    return templates.TemplateResponse("wishlist.html", {
        "request": request,
        "wishlist_entries": wishlist_entries,
        "user": user
    })


@router.post("/wishlist/add/{item_id}")
def add_to_wishlist(item_id: int, user_email: str = Cookie(None), db: Session = Depends(get_db)):
    if not user_email:
        return RedirectResponse(url="/login?error=You aren't logged in.", status_code=303)

    user = db.query(models.User).filter(models.User.email == user_email).first()
    item = db.query(models.Item).filter(models.Item.id == item_id).first()

    if not item:
        return RedirectResponse(url="/items?error=Item not found.", status_code=303)

    if item.owner_id == user.id:
        return RedirectResponse(url="/items?error=You cannot wishlist your own item.", status_code=303)

    already_exists = db.query(models.Wishlist).filter(
        models.Wishlist.user_id == user.id,
        models.Wishlist.item_id == item_id
    ).first()

    if not already_exists:
        new_entry = models.Wishlist(user_id=user.id, item_id=item_id)
        db.add(new_entry)
        db.commit()

    return RedirectResponse(url="/wishlist", status_code=303)


@router.post("/wishlist/remove/{item_id}")
def remove_from_wishlist(item_id: int, user_email: str = Cookie(None), db: Session = Depends(get_db)):
    if not user_email:
        return RedirectResponse(url="/login?error=You aren't logged in.", status_code=303)

    user = db.query(models.User).filter(models.User.email == user_email).first()
    entry = db.query(models.Wishlist).filter(
        models.Wishlist.user_id == user.id,
        models.Wishlist.item_id == item_id
    ).first()

    if entry:
        db.delete(entry)
        db.commit()

    return RedirectResponse(url="/wishlist", status_code=303)


@router.post("/wishlist/clear")
def clear_wishlist(user_email: str = Cookie(None), db: Session = Depends(get_db)):
    if not user_email:
        return RedirectResponse(url="/login?error=You aren't logged in.", status_code=303)

    user = db.query(models.User).filter(models.User.email == user_email).first()
    db.query(models.Wishlist).filter(models.Wishlist.user_id == user.id).delete()
    db.commit()

    return RedirectResponse(url="/wishlist", status_code=303)