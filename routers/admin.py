from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import bcrypt
import models
from database import get_db

router=APIRouter(prefix="/admin") #every route in the file starts with /admin
templates=Jinja2Templates(directory="templates")

# ADMIN_PASSWORD_HASH=b'$2b$12$/5cHFrUorCznmA72MTPEkeck3zjrhrQHXRniS/eU2WQLeyt4sNf6y' #idk eta claude ke diye bujha lagbe

#dependency function 
#anywhere that u see dependencies=[Depends(require_admin)] runs ts first
#if the admin isnt logged in then teh hhtpexception gets raised and the user is redirected status code 302 is the redirect
def require_admin(request: Request):
    if not request.session.get("admin_logged_in"):
        raise HTTPException(status_code=302, headers={"Location":"/admin/login"})

@router.get("/login") #admin login form
def loginPage(request:Request):
    return templates.TemplateResponse("admin_login.html", {"request": request})

ADMIN_EMAILS = {"admin@rentdao.com", "saiberry@gmail.com", "a5hv1n@gmail.com"}  # add whatever emails

@router.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email).first()
    
    if not user or not bcrypt.checkpw(password.encode(), user.hashed_password.encode()):
        return templates.TemplateResponse("admin_login.html", {"request": request, "error": "Invalid credentials"})
    
    if email not in ADMIN_EMAILS:  # check against hardcoded list instead of user.is_admin
        return templates.TemplateResponse("admin_login.html", {"request": request, "error": "You are not an admin"})
    
    request.session["admin_logged_in"] = True
    return RedirectResponse(url="/admin", status_code=303)

#admin logout
#next time we need to go through a protected route login is required
@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/admin/login", status_code =302)

#the three functions below all need to check for the dependency and then they perform operations based on the id tag of the item/user

#shows all items and users to the admin
@router.get("/", dependencies=[Depends(require_admin)])
def adminDash(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("admin.html",{"request":request, "items":db.query(models.Item).all(), "users":db.query(models.User).all()})

#to approve an item post
@router.post("/items/{item_id}/approve", dependencies=[Depends(require_admin)])
def approve(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.Item).filter(models.Item.id==item_id).first()
    if item:
        item.is_approved=True #approves the post
        db.commit() #makes the changes against the database (confirm button basically)
    return RedirectResponse(url="/admin", status_code=303)

#to remove an item post, same as above kinda
@router.post("/items/{item_id}/remove", dependencies=[Depends(require_admin)])
def delete(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.Item).filter(models.Item.id==item_id).first()
    if item:
        db.delete(item)
        db.commit()
    return RedirectResponse(url="/admin", status_code=303)
#suspnd user
@router.post("/users/{user_id}/suspend", dependencies=[Depends(require_admin)])
def suspend(user_id: int, db: Session=Depends(get_db)):
    user = db.query(models.User).filter(models.User.id==user_id).first()
    if user:
        user.is_suspended=True
        db.commit()
    return RedirectResponse(url="/admin",status_code=303)

@router.get("/users/search", dependencies=[Depends(require_admin)])
def search_user(request: Request, user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "items": db.query(models.Item).all(),
        "users": db.query(models.User).all(),
        "searched_user": user,  # None if not found
        "search_id": user_id
    })