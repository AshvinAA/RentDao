from fastapi import APIRouter, Request, Depends ,Form, Cookie, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import models, math
from database import get_db
from forms import ItemCreateForm

# Create the router
router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/items") #only approved items will show up here, the ones pending approval can only be seen on the admin panel
def read_items(request: Request , db: Session = Depends(get_db), page: int =1, limit: int=5): #calculating how many items to show on the page
    #how many items per page
    offset = (page - 1) * limit #which item to start from on the page
    # Get the total number of items in the database 
    total = db.query(models.Item).filter(models.Item.is_approved == True).count()
    #items on the current page
    items = db.query(models.Item).filter(models.Item.is_approved == True).offset(offset).limit(limit).all()
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
    form_data: ItemCreateForm = Depends(), #catching the whole form at once
    user_email: str=Cookie(None),#user email used to make post
    db: Session = Depends(get_db)
    ):
    
    if not user_email:
        return RedirectResponse(url="/login?error=You aren't logged in.", status_code=303)
    user=db.query(models.User).filter(models.User.email==user_email).first()#matching the user to the email used to crreate the item post
    
    new_item = models.Item(name=form_data.name, description=form_data.description, owner_id=user.id)#last one links the post to the owner
    
    db.add(new_item)
    db.commit()
    
    return RedirectResponse(url = "/items" , status_code=303)

@router.post("/items/delete/{item_id}")
def delete_item(
    item_id: int , #The id that would be deleted
    user_email: str=Cookie(None),#email of the owner
    db: Session = Depends(get_db)
):
    if not user_email:
        return RedirectResponse(url="/login?error=You aren't logged in.", status_code=303)
    user=db.query(models.User).filter(models.User.email==user_email).first()#matching the user to the email used to crreate the item so that only they can delete the post
    
    #Finding that item
    item= db.query(models.Item).filter(models.Item.id== item_id).first()
    if not item:
        return RedirectResponse(url="/items", status_code=303)
    
    if item.owner_id!=user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="You are not authorized to delete this item") #only the owner can delete their own posts, not anyone and the admin can delete any post
    
    if item: #checking if the item really exists
        db.delete(item)
        db.commit()
    
    return RedirectResponse(url = "/items" , status_code=303)

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