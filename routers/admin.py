from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import bcrypt
import models
from database import get_db
from sqlalchemy import text

router=APIRouter(prefix="/admin")
templates=Jinja2Templates(directory="templates")

ADMIN_PASSWORD_HASH=b'$2b$12$/5cHFrUorCznmA72MTPEkeck3zjrhrQHXRniS/eU2WQLeyt4sNf6y' #password12345

def require_admin(request: Request):
    if not request.session.get("admin_logged_in"):
        raise HTTPException(status_code=302, headers={"Location":"/admin/login"})

@router.get("/login")
def loginPage(request:Request):
    return templates.TemplateResponse("admin_login.html", {"request": request})

ADMIN_EMAILS = {"admin@rentdao.com", "saiberry@gmail.com", "a5hv1n@gmail.com"}

@router.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    if email in ADMIN_EMAILS:
        if not bcrypt.checkpw(password.encode(), ADMIN_PASSWORD_HASH):
            return templates.TemplateResponse("admin_login.html", {"request": request, "error": "Invalid credentials"})
        request.session["admin_logged_in"] = True
        return RedirectResponse(url="/admin", status_code=303)

    user=db.query(models.User).filter(models.User.email==email).first()

    if not user or not bcrypt.checkpw(password.encode(), user.hashed_password.encode()):
        return templates.TemplateResponse("admin_login.html", {"request": request, "error": "Invalid credentials"})
    if email not in ADMIN_EMAILS:
        return templates.TemplateResponse("admin_login.html", {"request": request, "error": "You are not an admin"})
    if not user.is_admin:
        user.is_admin=True
        db.commit()

    request.session["admin_logged_in"] = True
    return RedirectResponse(url="/admin", status_code=303)

@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/admin/login", status_code=302)


@router.get("/", dependencies=[Depends(require_admin)])
def adminDash(request: Request, db: Session = Depends(get_db)):
    ADMIN_EMAILS = {"admin@rentdao.com", "saiberry@gmail.com", "a5hv1n@gmail.com"}
    all_users = db.query(models.User).all()
    non_admin_users = [u for u in all_users if u.email not in ADMIN_EMAILS]

    users_with_items = db.query(models.Item.owner_id).distinct().subquery()
    inactive_users = db.query(models.User).filter(~models.User.id.in_(users_with_items)).all()

    pending_deliveries = db.query(models.Delivery_history).filter(
        models.Delivery_history.delivery_status == "awaiting_admin"
    ).all()

    # fetch all reports with reporter and reported user loaded
    all_reports = (
        db.query(models.Reports)
        .order_by(models.Reports.id.desc())
        .all()
    )

    return templates.TemplateResponse("admin.html", {
        "request": request,
        "items": db.query(models.Item).all(),
        "users": non_admin_users,
        "inactive_users": inactive_users,
        "pending_deliveries": pending_deliveries,
        "all_reports": all_reports,
    })


@router.post("/items/{item_id}/approve", dependencies=[Depends(require_admin)])
def approve(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.Item).filter(models.Item.id==item_id).first()
    if item:
        item.is_approved=True
        db.commit()
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/items/{item_id}/remove", dependencies=[Depends(require_admin)])
def delete(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.Item).filter(models.Item.id==item_id).first()
    if item:
        db.delete(item)
        db.commit()
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/users/{user_id}/suspend", dependencies=[Depends(require_admin)])
def suspend(user_id: int, db: Session=Depends(get_db)):
    user = db.query(models.User).filter(models.User.id==user_id).first()
    if user:
        user.is_suspended=True
        db.commit()
    return RedirectResponse(url="/admin", status_code=303)


@router.get("/users/search", dependencies=[Depends(require_admin)])
def search_user(request: Request, user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    all_reports = db.query(models.Reports).order_by(models.Reports.id.desc()).all()
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "items": db.query(models.Item).all(),
        "users": db.query(models.User).all(),
        "searched_user": user,
        "search_id": user_id,
        "inactive_users": [],
        "pending_deliveries": [],
        "all_reports": all_reports,
    })


@router.post("/deliveries/{delivery_id}/approve", dependencies=[Depends(require_admin)])
def approve_delivery(delivery_id: int, db: Session = Depends(get_db)):
    delivery = db.query(models.Delivery_history).filter(models.Delivery_history.id == delivery_id).first()
    if delivery and delivery.delivery_status == "awaiting_admin":
        delivery.delivery_status = "pending"
        db.commit()
    return RedirectResponse(url="/admin", status_code=303)


# dismiss a report (admin only delete)
@router.post("/reports/{report_id}/dismiss", dependencies=[Depends(require_admin)])
def dismiss_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(models.Reports).filter(models.Reports.id == report_id).first()
    if report:
        db.delete(report)
        db.commit()
    return RedirectResponse(url="/admin", status_code=303)