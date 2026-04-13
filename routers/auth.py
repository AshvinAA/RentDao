from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import models
from database import get_db
from security import get_password_hash, verify_password
from forms import UserCreateForm
import shutil
import os
import uuid

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# --- REGISTRATION ROUTES ---
@router.get("/register")
def show_register_page(request: Request , error: str = None):
    return templates.TemplateResponse("register.html", {"request": request})

@router.post("/register")
def register_user(
    form_data: UserCreateForm = Depends(), # Using our new clean form!
    db: Session = Depends(get_db)
):
    #Check if the email / user already exists or not 
    existing_user = db.query(models.User).filter(models.User.email == form_data.email).first()
    
    #Throws an error if the user already exists
    if existing_user: 
        return RedirectResponse(url="/register?error=email_taken", status_code=303)

    hashed_pw = get_password_hash(form_data.password)
    saved_picture_path = None

    # Handle Image Upload
    if form_data.picture and form_data.picture.filename:
        os.makedirs("static/profiles", exist_ok=True)
        file_extension = form_data.picture.filename.split(".")[-1]
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_location = f"static/profiles/{unique_filename}"
        
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(form_data.picture.file, file_object)
            
        saved_picture_path = f"/{file_location}"

    # Save to Database
    new_user = models.User(
        email=form_data.email,
        name=form_data.name,
        hashed_password=hashed_pw,
        picture=saved_picture_path,
        location=form_data.location,
        phone_no=form_data.phone_no,
        payment_option=form_data.payment_option
    )

    db.add(new_user)
    db.commit()
    return RedirectResponse(url='/', status_code=303)


# --- LOGIN ROUTES ---
@router.get("/login")
def show_login_page(request: Request, error: str = None):
    return templates.TemplateResponse("login.html", {"request": request, "error": error})

@router.post("/login")
def login_user(
    email: str = Form(...), 
    password: str = Form(...), 
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.email == email).first()

    if not user:
        return RedirectResponse(url="/login?error=Invalid Email or Password", status_code=303)
    
    if verify_password(password, user.hashed_password):
        if user.is_suspended:
            return RedirectResponse(url="/login?error=Account is suspended", status_code=303)
        
        return RedirectResponse(url="/items", status_code=303)
    else:
        return RedirectResponse(url="/login?error=Invalid Email or Password", status_code=303)