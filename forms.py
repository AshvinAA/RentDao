from fastapi import Form , UploadFile, File 

class ItemCreateForm:
    def __init__(self,
        name: str = Form(...),
        description: str = Form(...),  #Form(...) means this field is absolutely required
    ):
        self.name=name
        self.description=description

class UserCreateForm:
    def __init__(
        self,
        email: str = Form(...),
        name: str = Form(...),
        password: str = Form(...),
        location: str = Form(...),
        phone_no: str = Form(...),
        payment_option: str = Form(...),
        picture: UploadFile = File(None) # Catches the image upload
    ):
        self.email = email
        self.name = name
        self.password = password
        self.location = location
        self.phone_no = phone_no
        self.payment_option = payment_option
        self.picture = picture
        
class TagForm:
    def __init__(
        self,
        tag: str = Form(...)
    ):
        self.tag = tag