from sqlalchemy import Column , Integer , String , Boolean , Float , ForeignKey , Date
from sqlalchemy.orm import relationship 
from database import Base


class Item(Base):
    
    __tablename__ = "items"  # This tells SQLAlchemy what to name the table in MySQL

    id = Column(Integer, primary_key = True , index = True)
    name = Column(String(50) , index = True)
    description = Column(String(400))
    is_available = Column(Boolean,default = True)
    is_approved=Column(Boolean, default=False)
    # rating=Column(Float, default=0.0)
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="items_posted")
    price_per_day = Column(Integer , index = True)
    discount = Column(Integer , default=0)
    rating =Column(Float , index = True)


class User(Base):
    __tablename__= "users"

    #Core Identifiers
    id= Column(Integer, primary_key=True ,index= True)
    email=Column(String(100) , unique= True, index=True)
    name=Column(String(100))
    hashed_password = Column(String(255))

    #Profile Details
    picture = Column(String(255) , nullable =True) #We will store the image URL/path and not the image file itself
    location = Column(String(100), index=True, nullable=False)
    phone_no = Column(String(20))
    rating = Column(Float, default=0.0)
    payment_option = Column(String(100))

    #Admin/Suspended Flags
    is_admin = Column(Boolean , default=False)
    is_suspended = Column(Boolean , default=False)
    user_rating = Column(Float,index=True, default=0.0)
    items_count = Column(Integer, index=True, default=0)


    items_posted = relationship("Item",back_populates="owner")

    history = relationship("Booking_details", backref="items_booked")
    
class Booking_details(Base):
    __tablename__="booking_details"

    id=Column(Integer, primary_key=True, index=True)
    item_id=Column(Integer, ForeignKey("items.id"))
    user_id=Column(Integer, ForeignKey("users.id"))
    item = relationship("Item")
    start_date=Column(Date)
    end_date=Column(Date)
    total_price=Column(Integer)
    status = Column(String(20), default="pending") #pending, approved, rejected, completed
    booking_status = Column(Boolean, default=False) #False means the booking is not yet completed, True means the booking is completed
    rentor_id = Column(Integer, ForeignKey("users.id") ,default=None) 
    @property
    def location(self):
        if self.item and self.item.owner:
            return self.item.owner.location
        return None
 
         
class Delivery_drivers(Base):
    __tablename__ = "delivery_drivers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(255))
    phone_no = Column(String(20))
    license = Column(String(255))
    vehicle_type = Column(String(255))
    is_available = Column(Boolean, default=True)
    rating = Column(Float, default=0.0)
    delivery_history = relationship("Delivery_history", back_populates="driver")      
    
class Delivery_history(Base):
    __tablename__ = "delivery_history"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("booking_details.id"))
    driver_id = Column(Integer, ForeignKey("delivery_drivers.id"))
    delivery_status = Column(String(20), default="pending") #pending, in_transit, delivered
    delivery_date = Column(Date)
    driver = relationship("Delivery_drivers", foreign_keys=[driver_id], back_populates="delivery_history") 
    pickup_location = Column(String(100))
    dropoff_location = Column(String(100))
    
class Item_Tags(Base):
    __tablename__="item_tags"

    id=Column(Integer, primary_key=True, index=True)
    item_id=Column(Integer, ForeignKey("items.id"))
    tag=Column(String(50), index=True)
    items = relationship("Item", backref="tags")

class Cart(Base):
    __tablename__="cart"

    id=Column(Integer, primary_key=True, index=True)
    user_id=Column(Integer, ForeignKey("users.id"))
    item_id=Column(Integer, ForeignKey("items.id"))
    item = relationship("Item")
    users = relationship("User")

class Item_Images(Base):
    __tablename__="item_images"

    id=Column(Integer, primary_key=True, index=True)
    item_id=Column(Integer, ForeignKey("items.id"))
    image_url=Column(String(255))
    item = relationship("Item", backref="images")

class Wishlist(Base):
    __tablename__="wishlist"

    id=Column(Integer, primary_key=True, index=True)
    user_id=Column(Integer, ForeignKey("users.id"))
    item_id=Column(Integer, ForeignKey("items.id"))
    item = relationship("Item")
    users = relationship("User")

class Reviews(Base):
    review_id=Column(Integer, primary_key=True, index=True)
    item_id=Column(Integer, ForeignKey("items.id"))
    booking_id=Column(Integer, ForeignKey("booking_details.id"))
    reviewer_id=Column(Integer, ForeignKey("users.id"))
    reviewee_id=Column(Integer, ForeignKey("users.id"))
    rating=Column(Integer)
    comment=Column(String(400) , default="")

class Reports(Base):
    __tablename__="reports"

    id=Column(Integer, primary_key=True, index=True)
    reporter_id=Column(Integer, ForeignKey("users.id"))
    reported_user_id=Column(Integer, ForeignKey("users.id"))
    item_id=Column(Integer, ForeignKey("items.id"), nullable=True)
    reason=Column(String(400))
    details =Column(String(400) , default="")

class Insurance(Base):
    __tablename__="insurance"

    id=Column(Integer, primary_key=True, index=True)
    item_id=Column(Integer, ForeignKey("items.id"))
    insurance_provider=Column(String(100))
    policy_number=Column(String(100))
    coverage_details=Column(String(400))


class Payment(Base):
    __tablename__="payments"

    id=Column(Integer, primary_key=True, index=True)
    booking_id=Column(Integer, ForeignKey("booking_details.id"))
    owner_id=Column(Integer, ForeignKey("users.id"))
    amount=Column(Integer)
    payment_status=Column(String(20), default="pending") #pending, completed, failed
    payment_details=Column(String(400) , default="")
    payment_method=Column(String(100))
    payment_status=Column(String(20), default="pending")

