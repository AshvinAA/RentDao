from fastapi import FastAPI,Request,Depends
from fastapi.templating import Jinja2Templates
import models
from sqlalchemy.orm import Session
from database import engine,get_db

app = FastAPI()


models.Base.metadata.create_all(bind=engine) # This is the magic line that tells SQLAlchemy to build the tables!
 
templates = Jinja2Templates(directory="templates")  #creates a Jinja2 object and tells it to look to the templates package for everything

@app.get("/")
def read_root(request: Request):#request is a variable that basically catches all our data and packs them into our request variable
    # format for templates=         inside index html we would perform a request and the message that would be passed is "message"
    return templates.TemplateResponse("index.html" , {"request": request , "message": "Welcomes to RentDao's new frontend"})

@app.get("/items")
def read_items(request: Request , db: Session = Depends(get_db)):
    items= db.query(models.Item).all()
    return templates.TemplateResponse("items.html",{"request":request , "items":items})






#uvicorn main:app --reload
#source venv/Scripts/activate


    
