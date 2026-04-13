from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import models
from database import get_db
from forms import ItemCreateForm

# Create the router
router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/items")
def read_items(request: Request , db: Session = Depends(get_db)):
    items= db.query(models.Item).all()
    return templates.TemplateResponse("items.html",{"request":request , "items":items})

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