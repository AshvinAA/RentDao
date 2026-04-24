from fastapi import APIRouter, Request, Depends ,Form, Cookie, HTTPException , File, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import date
import models, math
from database import get_db
from forms import ItemCreateForm
import os ,uuid ,shutil 
from typing import List

# Create the router
router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/items") #only approved items will show up here, the ones pending approval can only be seen on the admin panel
def read_items(request: Request , db: Session = Depends(get_db), page: int =1, limit: int=5): #calculating how many items to show on the page
    #how many items per page
    offset = (page - 1) * limit #which item to start from on the page
    today = date.today()
    #subquery to find all the items that have pending or approved status in the db
    booked_item_ids = (
        db.query(models.Booking_details.item_id)
        .filter(
            models.Booking_details.status.in_(["pending", "approved"]),
            models.Booking_details.end_date >= today #bookings that are ending after today
        )
        .subquery()
    )
    # get the total number of approved items that arent currently booked for the pagination
    #only approved items
    total = (
        db.query(models.Item)
        .filter(
            models.Item.is_approved == True,
            ~models.Item.id.in_(db.query(models.Booking_details.item_id).filter(
                models.Booking_details.status.in_(["pending", "approved"]), #basically uporer subquery
                models.Booking_details.end_date >= today 
            ))
        )
        .count()
    )
    
    # Get items on the current page that are NOT currently booked
    items = (
        db.query(models.Item)
        .filter(
            models.Item.is_approved == True,
            ~models.Item.id.in_(booked_item_ids) #approved items in the list of items that are pending or approved from the subquery above
        )
        .offset(offset)
        .limit(limit)
        .all()
    )
    
    # Round up so partial pages still get their own page number
    total_pages = math.ceil(total / limit)
    return templates.TemplateResponse("browse.html", {
        "request": request,
        "items": items,
        "page": page,
        "total_pages": total_pages
    })

@router.post("/items")
def create_item(
    name: str = Form(...),
    description: str = Form(...),
    price_per_day: int = Form(0), # New field!
    discount: int = Form(0),      # New field!
    pictures: List[UploadFile] = File(None), # Accepts multiple files!
    user_email: str = Cookie(None),
    db: Session = Depends(get_db)
):
    if not user_email: #chcek if the user is logegd in 
        return RedirectResponse(url="/login?error=You aren't logged in.", status_code=303)
    user = db.query(models.User).filter(models.User.email == user_email).first()
    
    # 1. Create the core item
    new_item = models.Item(
        name=name, 
        description=description, 
        price_per_day=price_per_day,
        discount=discount,
        owner_id=user.id
    )
    db.add(new_item)
    db.flush() # Saves to DB to generate the item ID, but doesn't finalize yet

    # 2. Handle Multiple Images
    if pictures and pictures[0].filename: # Make sure they actually uploaded something
        os.makedirs("static/items", exist_ok=True)
        for pic in pictures:
            if pic.filename:
                # Generate unique filename and save to hard drive
                file_extension = pic.filename.split(".")[-1]
                unique_filename = f"{uuid.uuid4()}.{file_extension}"
                file_location = f"static/items/{unique_filename}"
                
                with open(file_location, "wb+") as file_object:
                    shutil.copyfileobj(pic.file, file_object)
                
                # Link the image to the Item in the database
                new_image = models.Item_Images(item_id=new_item.id, image_url=f"/{file_location}")
                db.add(new_image)

    db.commit() # Finalize everything!
    return RedirectResponse(url="/items", status_code=303)

@router.post("/items/edit/{item_id}")
def edit_item(
    item_id: int,
    name: str = Form(...),
    description: str = Form(...),
    price_per_day: int = Form(...), 
    discount: int = Form(...),
    pictures: List[UploadFile] = File(None), # For adding MORE pictures later
    user_email: str = Cookie(None),
    db: Session = Depends(get_db)
):
    if not user_email:
        return RedirectResponse(url="/login?error=You aren't logged in.", status_code=303)
        
    user = db.query(models.User).filter(models.User.email == user_email).first()
    item = db.query(models.Item).filter(models.Item.id == item_id).first()

    if item and item.owner_id == user.id: #only owner can edit
        # Update text fields
        item.name = name 
        item.description = description
        item.price_per_day = price_per_day
        item.discount = discount
        
        # Add new pictures if they uploaded more
        if pictures and pictures[0].filename:
            os.makedirs("static/items", exist_ok=True)
            for pic in pictures:
                if pic.filename:
                    ext = pic.filename.split(".")[-1]
                    file_location = f"static/items/{uuid.uuid4()}.{ext}"
                    with open(file_location, "wb+") as file_object:
                        shutil.copyfileobj(pic.file, file_object)
                    
                    new_image = models.Item_Images(item_id=item.id, image_url=f"/{file_location}")
                    db.add(new_image)

        db.commit()

    return RedirectResponse(url="/profile", status_code=303)

@router.post("/items/edit/{item_id}")
def edit_item(
    item_id: int,
    name: str = Form(...),
    user_email: str=Cookie(None),#email of the owner
    description: str = Form(...),
    db: Session = Depends(get_db)
    ):

    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not user_email:
        return RedirectResponse(url="/login?error=You aren't logged in.", status_code=303)
    user=db.query(models.User).filter(models.User.email==user_email).first()#matching the user to the email used to crreate the item so that only they can delete the post
    

    if item and item.owner_id==user.id:
        item.name = name 
        item.description = description
        db.commit()

    return RedirectResponse (url="/profile" , status_code = 303)

#to let users add items from their profile page
@router.get("/add-item")
def add_item_page(request: Request, user_email: str = Cookie(None)):
    if not user_email:
        return RedirectResponse(url="/login?error=You are not logged in.", status_code=303)
    return templates.TemplateResponse("items.html", {"request": request})

@router.post("/bookings/approve/{booking_id}")
def approve_booking(
    booking_id: int,
    user_email: str = Cookie(None),
    db: Session = Depends(get_db)
):
    #the booking id in question
    booking = db.query(models.Booking_details).filter(models.Booking_details.id == booking_id).first()
    
    if booking:
        booking.status = "approved"

        new_delivery = models.Delivery_history(
            booking_id=booking.id,
            delivery_status="awaiting_admin", #REMOVE TS
            pickup_location=booking.item.owner.location, 
            dropoff_location=booking.rentor.location,
            delivery_date=booking.start_date
        )
        db.add(new_delivery)
        db.commit()

    return RedirectResponse(url="/profile", status_code=303)