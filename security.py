from passlib.context import CryptContext

# This tells FastAPI to use the industry-standard bcrypt algorithm to scramble passwords
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str):
    #hashes the password 
    return pwd_context.hash(password)

def verify_password(plain_password: str , hashed_password : str):
    #Checks if the plain password matches the hashed one in the database
    return pwd_context.verify(plain_password , hashed_password)


    ##INSTALL PASSLIB##

    # pip install "passlib[bcrypt]"