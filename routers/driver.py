from fastapi import APIRouter, Request, Depends, Form, Cookie
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import models
from database import get_db
from security import get_password_hash, verify_password  # Assuming you have this from your auth setup!

router = APIRouter(prefix="/driver")
templates = Jinja2Templates(directory="templates")

# ==========================================
# 1. DRIVER AUTHENTICATION ROUTES
# ==========================================

@router.get("/register")
def show_driver_register(request: Request, error: str = None):
    return templates.TemplateResponse("driver_register.html", {"request": request, "error": error})

@router.post("/register")
def register_driver(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    phone_no: str = Form(...),
    license: str = Form(...),
    vehicle_type: str = Form(...),
    db: Session = Depends(get_db)
):
    # FIXED: Changed to Delivery_drivers
    existing_driver = db.query(models.Delivery_drivers).filter(models.Delivery_drivers.email == email).first()

    if existing_driver:
        return RedirectResponse(url="/driver/register?error=Email already in use", status_code=303)
    hashed_pw = get_password_hash(password)
    
    # FIXED: Changed to Delivery_drivers
    new_driver = models.Delivery_drivers(
        name=name,
        email=email,
        hashed_password=hashed_pw,
        phone_no=phone_no,
        license=license,
        vehicle_type=vehicle_type,
        is_available=True
    )
    db.add(new_driver)
    db.commit()

    return RedirectResponse(url="/driver/login", status_code=303)

@router.get("/login")
def show_driver_login(request: Request, error: str = None):
    return templates.TemplateResponse("driver_login.html", {"request": request, "error": error})    

@router.post("/login")
def login_driver(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    driver = db.query(models.Delivery_drivers).filter(models.Delivery_drivers.email == email).first()

    if not driver or not verify_password(password, driver.hashed_password):
        return RedirectResponse(url="/driver/login?error=Invalid Credentials", status_code=303)

    # SUCCESS! Redirect to driver dashboard
    response = RedirectResponse(url="/driver/dashboard", status_code=303)
    
    # Give them the DRIVER cookie, not the normal user cookie
    response.set_cookie(key="driver_email", value=driver.email, path="/")
    return response

@router.get("/logout")
def logout_driver():
    response = RedirectResponse(url="/driver/login", status_code=303)
    response.delete_cookie("driver_email")
    return response

# ==========================================
# 2. DRIVER DASHBOARD & OPERATIONS
# ==========================================


@router.get("/dashboard")
def driver_dashboard(request: Request, driver_email: str = Cookie(None), db: Session = Depends(get_db)):
    # Shield: Bounce unauthenticated drivers
    if not driver_email:
        return RedirectResponse(url="/driver/login?error=Please log in first", status_code=303)
        
    driver = db.query(models.Delivery_drivers).filter(models.Delivery_drivers.email == driver_email).first()
    
    # Fetch jobs that Admins have approved ("pending") AND have no driver yet
    available_jobs = db.query(models.Delivery_history).filter(
        models.Delivery_history.delivery_status == "pending",
        models.Delivery_history.driver_id == None
    ).all()
    
    # Fetch jobs this specific driver has accepted and is currently delivering
    my_active_jobs = db.query(models.Delivery_history).filter(
        models.Delivery_history.driver_id == driver.id,
        models.Delivery_history.delivery_status == "in_transit"
    ).all()

    return templates.TemplateResponse("driver_dashboard.html", {
        "request": request, 
        "driver": driver, 
        "available_jobs": available_jobs,
        "my_active_jobs": my_active_jobs
    })

@router.post("/accept/{delivery_id}")
def accept_delivery(delivery_id: int, driver_email: str = Cookie(None), db: Session = Depends(get_db)):
    if not driver_email:
        return RedirectResponse(url="/driver/login", status_code=303)

    driver = db.query(models.Delivery_drivers).filter(models.Delivery_drivers.email == driver_email).first()
    delivery = db.query(models.Delivery_history).filter(models.Delivery_history.id == delivery_id).first()
    
    # Ensure the job hasn't been taken by another driver in the meantime
    if delivery and delivery.driver_id is None and delivery.delivery_status == "pending":
        delivery.driver_id = driver.id
        delivery.delivery_status = "in_transit"
        
        # Mark driver as busy
        driver.is_available = False 
        db.commit()
        
    return RedirectResponse(url="/driver/dashboard", status_code=303)

@router.post("/complete/{delivery_id}")
def complete_delivery(delivery_id: int, driver_email: str = Cookie(None), db: Session = Depends(get_db)):
    if not driver_email:
        return RedirectResponse(url="/driver/login", status_code=303)

    driver = db.query(models.Delivery_drivers).filter(models.Delivery_drivers.email == driver_email).first()
    delivery = db.query(models.Delivery_history).filter(models.Delivery_history.id == delivery_id).first()
    
    # Ensure this is the correct driver updating their own job
    if delivery and delivery.driver_id == driver.id:
        delivery.delivery_status = "delivered"
        driver.is_available = True # Free them up for the next job
        
        # Automatically update the core Booking status to complete!
        if delivery.booking:
            delivery.booking.status = "completed"
            delivery.booking.booking_status = True
            
        db.commit()
        
    return RedirectResponse(url="/driver/dashboard", status_code=303)