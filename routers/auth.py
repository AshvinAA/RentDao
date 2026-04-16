from fastapi import APIRouter, Request, Depends, Form , Cookie, UploadFile, File
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
ADMIN_EMAILS = {"admin@rentdao.com", "saiberry@gmail.com", "a5hv1n@gmail.com"}  # add whatever emails


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
def show_login_page(request: Request):
    error = request.query_params.get("error")
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
        
        if email in ADMIN_EMAILS and not user.is_admin:
            user.is_admin=True
            db.commit()
        
        # SUCCESS: Redirect to profile
        response = RedirectResponse(url="/profile", status_code=303)
        
        # Give them the ALL-ACCESS Cookie
        response.set_cookie(key="user_email", value=user.email, path="/")
        return response
        
    else:
        return RedirectResponse(url="/login?error=Invalid Email or Password", status_code=303)
    
@router.get("/logout")
def logout():
    response = RedirectResponse(url="/login" , status_code =383)
    response.delete_cookie("user_email") #Delete the cookie
    return response

# --- PROFILE ROUTES ---

@router.get("/profile")
def show_profile(
    request: Request, 
    user_email: str = Cookie(None), 
    db: Session = Depends(get_db)
):
    # THE SHIELD: If they have no cookie, bounce them to login WITH a message!
    if not user_email:
        return RedirectResponse(url="/login?error=You are not logged in. Please log in first.", status_code=303)

    # If they DO have the cookie, load their data
    user = db.query(models.User).filter(models.User.email == user_email).first()
    
    return templates.TemplateResponse("profile.html", {
        "request": request, 
        "user": user,
        "is_admin": user_email in ADMIN_EMAILS 
    })

@router.post("/profile/edit")
def edit_profile(
    name: str = Form(...), 
    location: str = Form(...), 
    phone_no: str = Form(...),
    payment_option: str = Form(...), 
    picture: UploadFile = File(None),
    user_email: str = Cookie(None), 
    db: Session = Depends(get_db)
):
    
    if not user_email:
        return RedirectResponse(url="/login?error=You are not logged in.", status_code=303)

    user = db.query(models.User).filter(models.User.email == user_email).first()
    
    # Update the text fields
    user.name = name
    user.location = location
    user.phone_no = phone_no
    user.payment_option = payment_option

    # Update the picture if they uploaded one
    if picture and picture.filename:
        os.makedirs("static/profiles", exist_ok=True)
        file_extension = picture.filename.split(".")[-1]
        file_location = f"static/profiles/{uuid.uuid4()}.{file_extension}"
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(picture.file, file_object)
        user.picture = f"/{file_location}"

    db.commit()
    
    # Bounce them back to the profile page to see their updated info
    return RedirectResponse(url="/profile", status_code=303)

