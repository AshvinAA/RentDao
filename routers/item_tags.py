from fastapi import APIRouter, Request, Depends, HTTPException, Cookie
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import text
import models
from database import get_db
from forms import TagForm

router = APIRouter(prefix="/items")
templates = Jinja2Templates(directory="templates")


# --- Dependency: check that the logged-in user owns the item ---
def require_owner(item_id: int, request: Request, db: Session = Depends(get_db), user_email: str = Cookie(None)):
    if not user_email:
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    # user = db.query(models.User).filter(models.User.email == user_email).first()
    user = db.execute(
        text("SELECT * FROM users WHERE email = :email"),
        {"email": user_email}
    ).fetchone()
    if not user:
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    # item = db.query(models.Item).filter(models.Item.id == item_id).first()
    item = db.execute(
        text("SELECT * FROM items WHERE id = :iid"),
        {"iid": item_id}
    ).fetchone()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if item.owner_id != user.id:
        raise HTTPException(status_code=403, detail="You do not own this item")
    return item  # reused by the route so no second DB hit needed


# --- View all tags for an item ---
@router.get("/{item_id}/tags")
def get_tags(item_id: int, request: Request, db: Session = Depends(get_db)):
    # item = db.query(models.Item).filter(models.Item.id == item_id).first()
    item = db.execute(
        text("SELECT * FROM items WHERE id = :iid"),
        {"iid": item_id}
    ).fetchone()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    # tags = db.query(models.Item_Tags).filter(models.Item_Tags.item_id == item_id).all()
    tags = db.execute(
        text("SELECT * FROM item_tags WHERE item_id = :iid"),
        {"iid": item_id}
    ).fetchall()
    return templates.TemplateResponse("item_tags.html", {
        "request": request,
        "item": item,
        "tags": tags
    })


# --- Add a tag to an item (owner only) ---
@router.post("/{item_id}/tags/add")
def add_tag(
    item_id: int,
    request: Request,
    form: TagForm = Depends(),   # matches the pattern from your other forms
    db: Session = Depends(get_db),
    item: models.Item = Depends(require_owner)
):
    # prevent duplicate tags on the same item
    # existing = db.query(models.Item_Tags).filter(
    #     models.Item_Tags.item_id == item_id,
    #     models.Item_Tags.tag == form.tag.strip().lower()
    # ).first()
    existing = db.execute(
        text("SELECT id FROM item_tags WHERE item_id = :iid AND tag = :tag"),
        {"iid": item_id, "tag": form.tag.strip().lower()}
    ).fetchone()
    if existing:
        return RedirectResponse(url=f"/items/{item_id}/tags", status_code=303)

    # new_tag = models.Item_Tags(item_id=item_id, tag=form.tag.strip().lower())
    # db.add(new_tag)
    # db.commit()
    db.execute(
        text("INSERT INTO item_tags (item_id, tag) VALUES (:iid, :tag)"),
        {"iid": item_id, "tag": form.tag.strip().lower()}
    )
    db.commit()
    return RedirectResponse(url=f"/items/{item_id}/tags", status_code=303)


# --- Remove a tag from an item (owner only) ---
@router.post("/{item_id}/tags/{tag_id}/remove")
def remove_tag(
    item_id: int,
    tag_id: int,
    request: Request,
    db: Session = Depends(get_db),
    item: models.Item = Depends(require_owner)
):
    # tag = db.query(models.Item_Tags).filter(
    #     models.Item_Tags.id == tag_id,
    #     models.Item_Tags.item_id == item_id  # ensures tag belongs to this item
    # ).first()
    tag = db.execute(
        text("SELECT id FROM item_tags WHERE id = :tid AND item_id = :iid"),
        {"tid": tag_id, "iid": item_id}
    ).fetchone()
    if tag:
        # db.delete(tag)
        # db.commit()
        db.execute(
            text("DELETE FROM item_tags WHERE id = :tid"),
            {"tid": tag_id}
        )
        db.commit()
    return RedirectResponse(url=f"/items/{item_id}/tags", status_code=303)
