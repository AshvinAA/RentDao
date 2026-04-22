from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import models
from database import get_db
from forms import TagForm

router = APIRouter(prefix="/items")
templates = Jinja2Templates(directory="templates")


# --- Dependency: check that the logged-in user owns the item ---
def require_owner(item_id: int, request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if item.owner_id != user_id:
        raise HTTPException(status_code=403, detail="You do not own this item")
    return item  # reused by the route so no second DB hit needed


# --- View all tags for an item ---
@router.get("/{item_id}/tags")
def get_tags(item_id: int, request: Request, db: Session = Depends(get_db)):
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    tags = db.query(models.Item_Tags).filter(models.Item_Tags.item_id == item_id).all()
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
    existing = db.query(models.Item_Tags).filter(
        models.Item_Tags.item_id == item_id,
        models.Item_Tags.tag == form.tag.strip().lower()
    ).first()
    if existing:
        return RedirectResponse(url=f"/items/{item_id}/tags", status_code=303)

    new_tag = models.Item_Tags(item_id=item_id, tag=form.tag.strip().lower())
    db.add(new_tag)
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
    tag = db.query(models.Item_Tags).filter(
        models.Item_Tags.id == tag_id,
        models.Item_Tags.item_id == item_id  # ensures tag belongs to this item
    ).first()
    if tag:
        db.delete(tag)
        db.commit()
    return RedirectResponse(url=f"/items/{item_id}/tags", status_code=303)