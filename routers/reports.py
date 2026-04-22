from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import models
from database import get_db
from routers.auth import get_current_user

router = APIRouter(prefix="/reports")
templates = Jinja2Templates(directory="templates")


@router.get("/create")
def show_report_form(
    request: Request,
    reported_user_id: int = None,
    item_id: int = None,
    current_user: models.User = Depends(get_current_user),
):
    return templates.TemplateResponse("report_form.html", {
        "request": request,
        "user": current_user,
        "reported_user_id": reported_user_id,
        "item_id": item_id,
    })


@router.post("/create")
def submit_report(
    reported_user_id: int = Form(...),
    reason: str = Form(...),
    details: str = Form(""),
    item_id: int = Form(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Can't report yourself
    if reported_user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot report yourself")

    # Make sure the reported user exists
    reported_user = db.query(models.User).filter(models.User.id == reported_user_id).first()
    if not reported_user:
        raise HTTPException(status_code=404, detail="User not found")

    # If an item_id was provided, make sure it exists
    if item_id:
        item = db.query(models.Item).filter(models.Item.id == item_id).first()
        if not item:
            item_id = None  # silently drop invalid item reference

    new_report = models.Reports(
        reporter_id=current_user.id,
        reported_user_id=reported_user_id,
        item_id=item_id,
        reason=reason,
        details=details,
    )
    db.add(new_report)
    db.commit()

    return RedirectResponse(url="/items", status_code=303)



@router.get("/mine")
def my_reports(
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reports = (
        db.query(models.Reports)
        .filter(models.Reports.reporter_id == current_user.id)
        .all()
    )
    return templates.TemplateResponse("my_reports.html", {
        "request": request,
        "user": current_user,
        "reports": reports,
    })