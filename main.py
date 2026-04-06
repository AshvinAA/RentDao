from fastapi import FastAPI,Request,Depends,Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
import models
from sqlalchemy.orm import Session
from database import engine,get_db
from forms import ItemCreateForm

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


#push
#uvicorn main:app --reload
#source venv/Scripts/activate



