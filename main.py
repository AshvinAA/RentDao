from fastapi import FastAPI, Request, Cookie
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
# from fastapi.middleware.sessions import SessionMiddleware #idk this either
from starlette.middleware.sessions import SessionMiddleware #if i put this taile kaj kore have to ask claude tokens ferot ashle
import os
import models
from database import engine
# from routers import auth, items, admin, driver
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="change-this-to-something-secret") #idk this

from routers import items, auth, admin, bookings, insurance, reviews, reports, payments, item_tags, wishlist ,driver ,detail

models.Base.metadata.create_all(bind=engine) # This is the magic line that tells SQLAlchemy to build the tables!

templates = Jinja2Templates(directory="templates")  #creates a Jinja2 object and tells it to look to the templates package for everything

# Creates a folder called "static" to hold images and CSS
os.makedirs("static/profiles", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

#importing the routes
app.include_router(items.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(driver.router)
app.include_router(bookings.router)
app.include_router(reviews.router)
app.include_router(reports.router)
app.include_router(payments.router)
app.include_router(insurance.router)
app.include_router(item_tags.router)
app.include_router(wishlist.router)
app.include_router(detail.router)


@app.get("/")
def read_root(request: Request, user_email: str=Cookie(None)):#request is a variable that basically catches all our data and packs them into our request variable
    # format for templates=         inside index html we would perform a request and the message that would be passed is "message"
    return templates.TemplateResponse("index.html", {
    "request": request, 
    "message": "Welcome to RentDao's new crazy frontend",
    "user_email": user_email
})




#push
#uvicorn main:app --reload
#source venv/Scripts/activate