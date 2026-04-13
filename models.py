from sqlalchemy import Column , Integer , String , Boolean , Float , ForeignKey
from sqlalchemy.orm import relationship 
from database import Base


class Item(Base):
    
    __tablename__ = "items"  # This tells SQLAlchemy what to name the table in MySQL

    id = Column(Integer, primary_key = True , index = True)
    name = Column(String(50) , index = True)
    description = Column(String(400))
    is_available = Column(Boolean,default = True)

    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="items_posted")

class User(Base):
    __tablename__= "users"

    #Core Identifiers
    id= Column(Integer, primary_key=True ,index= True)
    email=Column(String(100) , unique= True, index=True)
    name=Column(String(100))
    hashed_password = Column(String(255))

    #Profile Details
    picture = Column(String(255) , nullable =True) #We will store the image URL/path and not the image file itself
    location = Column(String(100))
    phone_no = Column(String(20))
    rating = Column(Float, default=0.0)
    payment_option = Column(String(100))

    #Admin/Suspended Flags
    is_admin = Column(Boolean , default=False)
    is_suspended = Column(Boolean , default=False)

    items_posted = relationship("Item",back_populates="owner")

    #Uncomment when rental is done
    #history =relationship("Rental",back_populates="user")
    






