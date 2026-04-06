from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

SQLALCHEMY_DATABASE_URL = "mysql+pymysql://bYQ197N8JPYfXq4.root:zE4l9vk6EZPTabRl@gateway01.ap-southeast-1.prod.aws.tidbcloud.com:4000/rentdao?ssl_verify_cert=true&ssl_verify_identity=true" #The connection string  (this might not work on the host pc, change it localhost if it doesnt)

engine = create_engine(SQLALCHEMY_DATABASE_URL) # The Engine is the actual connection to the database

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base() # Base is the parent class for all our future table models

def get_db():   #this works as a open and close mechanism for the database , so that we learn how to open exit the connection each time our databse is  interacted with
    db= SessionLocal()  #opens the connection
    try:
        yield db        #acts as a pause button and opens the database connection to read/write data \
    finally:
        db.close() #shuts down the connection after the job is done


