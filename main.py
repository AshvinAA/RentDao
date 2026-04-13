from fastapi import FastAPI,Request,Depends,Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
import models
from sqlalchemy.orm import Session
from database import engine,get_db
from forms import ItemCreateForm
from security import get_password_hash

app = FastAPI()


models.Base.metadata.create_all(bind=engine) # This is the magic line that tells SQLAlchemy to build the tables!

templates = Jinja2Templates(directory="templates")  #creates a Jinja2 object and tells it to look to the templates package for everything

@app.get("/")
def read_root(request: Request):#request is a variable that basically catches all our data and packs them into our request variable
    # format for templates=         inside index html we would perform a request and the message that would be passed is "message"
    return templates.TemplateResponse("index.html" , {"request": request , "message": "Welcomes to RentDao's new crazy frontend "})

@app.get("/items")
def read_items(request: Request , db: Session = Depends(get_db)):
    items= db.query(models.Item).all()
    return templates.TemplateResponse("items.html",{"request":request , "items":items})

@app.post("/items")
def create_item(
    form_data: ItemCreateForm = Depends(), #catching the whole form at once
    db: Session = Depends(get_db)
):
    new_item = models.Item(name=form_data.name, description=form_data.description)
    
    db.add(new_item)
    db.commit()
    
    return RedirectResponse(url = "/items" , status_code=303)

@app.post("/items/delete/{item_id}")
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


@app.post("/register")
def register_user(
    email: str = Form(...),        
    name: str = Form(...),         
    password: str = Form(...),
    location: str = Form(...),
    phone_no: str = Form(...),
    picture: str = Form(None),     
    payment_option: str = Form(...),
    db: Session = Depends(get_db)
):
    hashed_pw = get_password_hash(password)

    
    new_user = models.User(
        email=email,
        name=name,
        hashed_password=hashed_pw,
        picture=picture,
        location=location,
        phone_no=phone_no,
        payment_option=payment_option
    )

    db.add(new_user)
    db.commit()

    return RedirectResponse(url='/login', status_code=303)

@app.get("/register")
def show_register_page(request: Request):
    return templates.TemplateResponse("register.html" , {"request": request})





#push
#uvicorn main:app --reload
#source venv/Scripts/activate



