from fastapi import APIRouter, Request, Depends, Form, Cookie
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import text # <--- Brought in the raw SQL engine!
import models
from database import get_db
from security import get_password_hash, verify_password  

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
    # Checking if the driver exists
    existing_driver = db.execute(
        text("SELECT id FROM delivery_drivers WHERE email = :email"),
        {"email": email}
    ).fetchone()

    if existing_driver:
        return RedirectResponse(url="/driver/register?error=Email already in use", status_code=303)
        
    hashed_pw = get_password_hash(password)
    
    #Inserting a new driver 
    db.execute(
        text("""
            INSERT INTO delivery_drivers (name, email, hashed_password, phone_no, license, vehicle_type, is_available)
            VALUES (:name, :email, :password, :phone_no, :license, :vehicle_type, 1)
        """),
        {
            "name": name, 
            "email": email, 
            "password": hashed_pw, 
            "phone_no": phone_no, 
            "license": license, 
            "vehicle_type": vehicle_type
        }
    )
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
    # RAW SQL: Fetch driver by email
    driver = db.execute(
        text("SELECT * FROM delivery_drivers WHERE email = :email"),
        {"email": email}
    ).fetchone()

    if not driver or not verify_password(password, driver.hashed_password):
        return RedirectResponse(url="/driver/login?error=Invalid Credentials", status_code=303)

    # SUCCESS! Redirect to driver dashboard
    response = RedirectResponse(url="/driver/dashboard", status_code=303)
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
    if not driver_email:
        return RedirectResponse(url="/driver/login?error=Please log in first", status_code=303)
        
    # RAW SQL: Get current driver
    driver = db.execute(
        text("SELECT * FROM delivery_drivers WHERE email = :email"),
        {"email": driver_email}
    ).fetchone()
    
    # RAW SQL: Fetch available jobs with JOINs to get the item name
    available_jobs = db.execute(
        text("""
            SELECT dh.*, i.name AS item_name 
            FROM delivery_history dh
            JOIN booking_details bd ON dh.booking_id = bd.id
            JOIN items i ON bd.item_id = i.id
            WHERE dh.delivery_status = 'pending' AND dh.driver_id IS NULL
        """)
    ).fetchall()
    
    # RAW SQL: Fetch active jobs for THIS driver
    my_active_jobs = db.execute(
        text("""
            SELECT dh.*, i.name AS item_name 
            FROM delivery_history dh
            JOIN booking_details bd ON dh.booking_id = bd.id
            JOIN items i ON bd.item_id = i.id
            WHERE dh.driver_id = :driver_id AND dh.delivery_status = 'in_transit'
        """),
        {"driver_id": driver.id}
    ).fetchall()

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

    driver = db.execute(
        text("SELECT id FROM delivery_drivers WHERE email = :email"),
        {"email": driver_email}
    ).fetchone()
    
    if not driver:
        return RedirectResponse(url="/driver/login", status_code=303)

    # RAW SQL: Safely attempt to claim the job (prevents race conditions)
    result = db.execute(
        text("""
            UPDATE delivery_history 
            SET driver_id = :driver_id, delivery_status = 'in_transit'
            WHERE id = :delivery_id AND driver_id IS NULL AND delivery_status = 'pending'
        """),
        {"driver_id": driver.id, "delivery_id": delivery_id}
    )
    
    # If the update was successful, mark the driver as busy
    if result.rowcount > 0:
        db.execute(
            text("UPDATE delivery_drivers SET is_available = 0 WHERE id = :driver_id"),
            {"driver_id": driver.id}
        )
        db.commit()
        
    return RedirectResponse(url="/driver/dashboard", status_code=303)

@router.post("/complete/{delivery_id}")
def complete_delivery(delivery_id: int, driver_email: str = Cookie(None), db: Session = Depends(get_db)):
    if not driver_email:
        return RedirectResponse(url="/driver/login", status_code=303)

    driver = db.execute(
        text("SELECT id FROM delivery_drivers WHERE email = :email"),
        {"email": driver_email}
    ).fetchone()
    
    if not driver:
        return RedirectResponse(url="/driver/login", status_code=303)

    # RAW SQL: Find the delivery to verify ownership and get the booking_id
    delivery = db.execute(
        text("SELECT id, booking_id FROM delivery_history WHERE id = :delivery_id AND driver_id = :driver_id"),
        {"delivery_id": delivery_id, "driver_id": driver.id}
    ).fetchone()
    
    if delivery:
        # 1. Update delivery status to delivered
        db.execute(
            text("UPDATE delivery_history SET delivery_status = 'delivered' WHERE id = :delivery_id"),
            {"delivery_id": delivery_id}
        )
        
        # 2. Free up the driver for the next job
        db.execute(
            text("UPDATE delivery_drivers SET is_available = 1 WHERE id = :driver_id"),
            {"driver_id": driver.id}
        )
        
        # 3. Automatically complete the core Booking
        db.execute(
            text("UPDATE booking_details SET status = 'completed' WHERE id = :booking_id"),
            {"booking_id": delivery.booking_id}
        )
        
        db.commit()
        
    return RedirectResponse(url="/driver/dashboard", status_code=303)