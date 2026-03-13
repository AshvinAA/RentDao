from fastapi import Form

class ItemCreateForm:
    def __init__(self,
        name: str = Form(...),
        description: str = Form(...),  #Form(...) means this field is absolutely required
    ):
        self.name=name
        self.description=description