from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import models
from database import get_db
from routers.auth import get_current_user

router = APIRouter(prefix="/insurance")
templates = Jinja2Templates(directory="templates")

@router.get("/{item_id}")
def insurance_redirect(item_id: int):
    return RedirectResponse(url=f"/insurance/item/{item_id}", status_code=301)

@router.get("/item/{item_id}")
def view_insurance(
    item_id: int,
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(models.Item).filter(models.Item.id == item_id).first() #finding item in db as per usual
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Only the item owner can view insurance details
    if item.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
#finds the insurance of the specific item
    records = (
        db.query(models.Insurance)
        .filter(models.Insurance.item_id == item_id)
        .all()
    )
    return templates.TemplateResponse("insurance.html", {
        "request": request,
        "user": current_user,
        "item": item,
        "records": records,
    })


@router.post("/add/{item_id}")
def add_insurance(
    item_id: int,
    insurance_provider: str = Form(...),
    policy_number: str = Form(...),
    coverage_details: str = Form(""),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if item.owner_id != current_user.id: #only owner can add insurance details of the item
        raise HTTPException(status_code=403, detail="Not authorized")

    new_record = models.Insurance(
        item_id=item_id,
        insurance_provider=insurance_provider,
        policy_number=policy_number,
        coverage_details=coverage_details,
    )
    db.add(new_record)
    db.commit()

    return RedirectResponse(url=f"/insurance/item/{item_id}", status_code=303)


@router.post("/remove/{record_id}")
def remove_insurance(
    record_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.query(models.Insurance).filter(models.Insurance.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    # Only the item owner can remove
    item = db.query(models.Item).filter(models.Item.id == record.item_id).first()
    if not item or item.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    item_id = record.item_id
    db.delete(record)
    db.commit()

    return RedirectResponse(url=f"/insurance/item/{item_id}", status_code=303)