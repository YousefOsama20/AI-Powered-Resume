from .BaseController import BaseController
from fastapi import UploadFile
from models import ResponseSignal
import os

class ProjectController(BaseController):
    
    def __init__(self):
        # Type: Sub-function
        super().__init__()

    def get_customer_path(self, customer_id: str):
        # Type: Main function
        customer_dir = os.path.join(
            self.files_dir,
            customer_id
        )

        if not os.path.exists(customer_dir):
            os.makedirs(customer_dir)

        return customer_dir

    
