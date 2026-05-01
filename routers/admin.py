from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import text
import bcrypt
import models
from database import get_db

router=APIRouter(prefix="/admin") #every route in the file starts with /admin
templates=Jinja2Templates(directory="templates")

ADMIN_PASSWORD_HASH=b'$2b$12$/5cHFrUorCznmA72MTPEkeck3zjrhrQHXRniS/eU2WQLeyt4sNf6y' #password12345

#dependency function 
#anywhere that u see dependencies=[Depends(require_admin)] runs ts first
def require_admin(request: Request):
    if not request.session.get("admin_logged_in"):
        raise HTTPException(status_code=302, headers={"Location":"/admin/login"})

@router.get("/login") #admin login form
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

    # user=db.query(models.User).filter(models.User.email==email).first()
    user = db.execute(
        text("SELECT * FROM users WHERE email = :email"),
        {"email": email}
    ).fetchone()

    if not user or not bcrypt.checkpw(password.encode(), user.hashed_password.encode()):
        return templates.TemplateResponse("admin_login.html", {"request": request, "error": "Invalid credentials"})
    if email not in ADMIN_EMAILS:
        return templates.TemplateResponse("admin_login.html", {"request": request, "error": "You are not an admin"})

    if not user.is_admin:
        # user.is_admin=True 
        db.execute(
            text("UPDATE users SET is_admin = 1 WHERE id = :uid"),
            {"uid": user.id}
        )
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

    # all_users = db.query(models.User).all()
    all_users = db.execute(
        text("SELECT * FROM users")
    ).fetchall()
    non_admin_users = [u for u in all_users if u.email not in ADMIN_EMAILS]

    #subquery to help find users who have never posted an item(inactive users)
    # users_with_items = db.query(models.Item.owner_id).distinct().subquery() #users who have posted items
    # actually showing the inactive users
    # inactive_users = (db.query(models.User).filter(~models.User.id.in_(users_with_items)).all())
    inactive_users = db.execute(
        text("""
            SELECT * FROM users
            WHERE id NOT IN (SELECT DISTINCT owner_id FROM items)
        """)
    ).fetchall()

    # items": db.query(models.Item).all()
    # JOIN with users to get owner email since item.owner.email no longer works on raw rows
    items = db.execute(
        text("""
            SELECT i.*, u.email AS owner_email
            FROM items i
            JOIN users u ON i.owner_id = u.id
        """)
    ).fetchall()

    # fetching all reports with reporter/reported user names and suspension status
    # needed because report.reporter.name, report.reported_user.name, report.reported_user.is_suspended
    # no longer work on raw rows
    all_reports = db.execute(
        text("""
            SELECT r.*,
                   u1.name AS reporter_name,
                   u2.name AS reported_user_name,
                   u2.is_suspended AS reported_user_is_suspended
            FROM reports r
            JOIN users u1 ON r.reporter_id = u1.id
            JOIN users u2 ON r.reported_user_id = u2.id
        """)
    ).fetchall()

    return templates.TemplateResponse("admin.html", {
        "request": request, 
        "items": items,
        "users": non_admin_users,
        "inactive_users": inactive_users,
        "all_reports": all_reports,
    })

# next 4 functions do the same things essentially just approve/suspend/search/remove based on the item/userid

# approve item post
@router.post("/items/{item_id}/approve", dependencies=[Depends(require_admin)])
def approve(item_id: int, db: Session = Depends(get_db)):
    # item = db.query(models.Item).filter(models.Item.id==item_id).first()
    # if item:
    #     item.is_approved=True 
    #     db.commit()
    item = db.execute(
        text("SELECT id FROM items WHERE id = :iid"),
        {"iid": item_id}
    ).fetchone()
    if item:
        db.execute(
            text("UPDATE items SET is_approved = 1 WHERE id = :iid"),
            {"iid": item_id}
        )
        db.commit()
    return RedirectResponse(url="/admin", status_code=303)

# remove an item from the market
@router.post("/items/{item_id}/remove", dependencies=[Depends(require_admin)])
def delete(item_id: int, db: Session = Depends(get_db)):
    # item = db.query(models.Item).filter(models.Item.id==item_id).first()
    # if item:
    #     db.delete(item)
    #     db.commit()
    item = db.execute(
        text("SELECT id FROM items WHERE id = :iid"),
        {"iid": item_id}
    ).fetchone()
    if item:
        db.execute(
            text("DELETE FROM items WHERE id = :iid"),
            {"iid": item_id}
        )
        db.commit()
    return RedirectResponse(url="/admin", status_code=303)

# suspend user
@router.post("/users/{user_id}/suspend", dependencies=[Depends(require_admin)])
def suspend(user_id: int, db: Session=Depends(get_db)):
    # user = db.query(models.User).filter(models.User.id==user_id).first()
    # if user:
    #     user.is_suspended=True
    #     db.commit()
    user = db.execute(
        text("SELECT id FROM users WHERE id = :uid"),
        {"uid": user_id}
    ).fetchone()
    if user:
        db.execute(
            text("UPDATE users SET is_suspended = 1 WHERE id = :uid"),
            {"uid": user_id}
        )
        db.commit()
    return RedirectResponse(url="/admin", status_code=303)

# unsuspend user
@router.post("/users/{user_id}/unsuspend", dependencies=[Depends(require_admin)])
def unsuspend(user_id: int, db: Session = Depends(get_db)):
    # user = db.query(models.User).filter(models.User.id==user_id).first()
    # if user:
    #     user.is_suspended=False
    #     db.commit()
    user = db.execute(
        text("SELECT id FROM users WHERE id = :uid"),
        {"uid": user_id}
    ).fetchone()
    if user:
        db.execute(
            text("UPDATE users SET is_suspended = 0 WHERE id = :uid"),
            {"uid": user_id}
        )
        db.commit()
    return RedirectResponse(url="/admin", status_code=303)

# search based on uid
@router.get("/users/search", dependencies=[Depends(require_admin)])
def search_user(request: Request, user_id: int, db: Session = Depends(get_db)):
    # user = db.query(models.User).filter(models.User.id == user_id).first()
    user = db.execute(
        text("SELECT * FROM users WHERE id = :uid"),
        {"uid": user_id}
    ).fetchone()

    # items": db.query(models.Item).all()
    # "users": db.query(models.User).all()
    items = db.execute(
        text("""
            SELECT i.*, u.email AS owner_email
            FROM items i
            JOIN users u ON i.owner_id = u.id
        """)
    ).fetchall()
    users = db.execute(
        text("SELECT * FROM users")
    ).fetchall()

    return templates.TemplateResponse("admin.html", {    
        "request": request,
        "items": items,
        "users": users,
        "searched_user": user,  
        "search_id": user_id
    })


# dismiss a report
@router.post("/reports/{report_id}/dismiss", dependencies=[Depends(require_admin)])
def dismiss_report(report_id: int, db: Session = Depends(get_db)):
    # report = db.query(models.Report).filter(models.Report.id == report_id).first()
    # if report:
    #     db.delete(report)
    #     db.commit()
    db.execute(
        text("DELETE FROM reports WHERE id = :rid"),
        {"rid": report_id}
    )
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)