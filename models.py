from sqlalchemy import Column , Integer , String ,Boolean
from database import Base

class Item(Base):
    
    __tablename__ = "items"  # This tells SQLAlchemy what to name the table in MySQL

    id = Column(Integer, primary_key = True , index = True)
    name = Column(String(50) , index = True)
    description = Column(String(400))
    is_available = Column(Boolean,default = True)

