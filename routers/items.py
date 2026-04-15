from fastapi import APIRouter, Request, Depends ,Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import models, math
from database import get_db
from forms import ItemCreateForm

# Create the router
router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/items")
def read_items(request: Request , db: Session = Depends(get_db), page: int =1, limit: int=5): #calculating how many items to show on the page
    # Calculate how many items to skip based on the current page
    # e.g. page 2 with limit 5 → skip the first 10 items
    offset = (page - 1) * limit
    
    # Get the total number of items in the database (needed to calculate total pages)
    total = db.query(models.Item).count()
    
    # Fetch only the items for the current page
    items = db.query(models.Item).offset(offset).limit(limit).all()
    
    # Round up so partial pages still get their own page number
    # e.g. 11 items with limit 5 → 3 pages, not 2
    total_pages = math.ceil(total / limit)
    
    # Pass everything to the template — page and total_pages drive the pagination buttons
    return templates.TemplateResponse("items.html", {
        "request": request,
        "items": items,
        "page": page,
        "total_pages": total_pages
    })

@router.post("/items")
def create_item(
    form_data: ItemCreateForm = Depends(), #catching the whole form at once
    db: Session = Depends(get_db)
):
    new_item = models.Item(name=form_data.name, description=form_data.description)
    
    db.add(new_item)
    db.commit()
    
    return RedirectResponse(url = "/items" , status_code=303)

@router.post("/items/delete/{item_id}")
def delete_item(
    item_id: int , #The id that would be deleted
    db: Session = Depends(get_db)
):
    #Finding that item
    item= db.query(models.Item).filter(models.Item.id== item_id).first()

    if item: #checking if the item really exists
        db.delete(item)
        db.commit()
    
    return RedirectResponse(url = "/items" , status_code=303)

@router.post("/items/edit/{item_id}")
def edit_item(
    item_id: int,
    name: str = Form(...),
    description: str = Form(...),
    db: Session = Depends(get_db)
    ):

    item = db.query(models.Item).filter(models.Item.id == item_id).first()

    if item:
        item.name = name 
        item.description = description
        db.commit()

    return RedirectResponse (url="/profile" , status_code = 303)