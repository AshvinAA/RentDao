from fastapi import APIRouter, Request, Depends, Cookie
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import text
import models
from database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/wishlist")
def get_wishlist(request: Request, user_email: str = Cookie(None), db: Session = Depends(get_db)):
    if not user_email:
        return RedirectResponse(url="/login?error=You aren't logged in.", status_code=303)

    user = db.query(models.User).filter(models.User.email == user_email).first()
    if not user:
        return RedirectResponse(url="/login?error=You aren't logged in.", status_code=303)

    # Use raw SQL to get wishlist entries with item + owner + image + avg_rating in one go
    wishlist_entries = db.execute(
        text("""
            SELECT w.id, w.item_id,
                   i.name        AS item_name,
                   i.description AS item_description,
                   i.price_per_day,
                   i.owner_id,
                   u.name        AS owner_name,
                   (SELECT AVG(r.rating) FROM reviews r WHERE r.item_id = i.id) AS avg_rating,
                   (SELECT ii.image_url FROM item_images ii
                    WHERE ii.item_id = i.id ORDER BY ii.id ASC LIMIT 1)         AS image_url
            FROM wishlist w
            JOIN items i ON w.item_id = i.id
            JOIN users u ON i.owner_id = u.id
            WHERE w.user_id = :uid
        """),
        {"uid": user.id}
    ).fetchall()

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
    if not user:
        return RedirectResponse(url="/login?error=You aren't logged in.", status_code=303)

    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not item:
        return RedirectResponse(url=f"/items/{item_id}", status_code=303)
    if item.owner_id == user.id:
        return RedirectResponse(url=f"/items/{item_id}", status_code=303)

    already_exists = db.query(models.Wishlist).filter(
        models.Wishlist.user_id == user.id,
        models.Wishlist.item_id == item_id
    ).first()

    if not already_exists:
        new_entry = models.Wishlist(user_id=user.id, item_id=item_id)
        db.add(new_entry)
        db.commit()

    return RedirectResponse(url=f"/items/{item_id}", status_code=303)


@router.post("/wishlist/remove/{item_id}")
def remove_from_wishlist(item_id: int, user_email: str = Cookie(None), db: Session = Depends(get_db)):
    if not user_email:
        return RedirectResponse(url="/login?error=You aren't logged in.", status_code=303)

    user = db.query(models.User).filter(models.User.email == user_email).first()
    if not user:
        return RedirectResponse(url="/login?error=You aren't logged in.", status_code=303)

    entry = db.query(models.Wishlist).filter(
        models.Wishlist.user_id == user.id,
        models.Wishlist.item_id == item_id
    ).first()
    if entry:
        db.delete(entry)
        db.commit()

    return RedirectResponse(url="/wishlist", status_code=303)


@router.post("/wishlist/remove-from-detail/{item_id}")
def remove_from_wishlist_detail(item_id: int, user_email: str = Cookie(None), db: Session = Depends(get_db)):
    """Removes from wishlist and redirects back to the item detail page."""
    if not user_email:
        return RedirectResponse(url="/login?error=You aren't logged in.", status_code=303)

    user = db.query(models.User).filter(models.User.email == user_email).first()
    if not user:
        return RedirectResponse(url="/login?error=You aren't logged in.", status_code=303)

    entry = db.query(models.Wishlist).filter(
        models.Wishlist.user_id == user.id,
        models.Wishlist.item_id == item_id
    ).first()
    if entry:
        db.delete(entry)
        db.commit()

    return RedirectResponse(url=f"/items/{item_id}", status_code=303)


@router.post("/wishlist/clear")
def clear_wishlist(user_email: str = Cookie(None), db: Session = Depends(get_db)):
    if not user_email:
        return RedirectResponse(url="/login?error=You aren't logged in.", status_code=303)

    user = db.query(models.User).filter(models.User.email == user_email).first()
    if not user:
        return RedirectResponse(url="/login?error=You aren't logged in.", status_code=303)

    db.query(models.Wishlist).filter(models.Wishlist.user_id == user.id).delete()
    db.commit()

    return RedirectResponse(url="/wishlist", status_code=303)