from fastapi import FastAPI,Request 
from fastapi.templating import Jinja2Templates

app = FastAPI()

templates = Jinja2Templates(directory="templates")  #creates a Jinja2 object and tells it to look to the templates package for everything

@app.get("/")
def read_root(request: Request):#request is a variable that basically catches all our data and packs them into our request variable
    # format for templates=         inside index html we would perform a request and the message that would be passed is "message"
    return templates.TemplateResponse("index.html" , {"request": request , "message": "Welcomes to RentDao's new frontend"})


#uvicorn main:app --reload


    
