from arcapi.transport.session import Session

class Local(Session):
    def __init__(self):
        self.local = True
