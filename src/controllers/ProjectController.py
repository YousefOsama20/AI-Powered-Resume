from .BaseController import BaseController
from fastapi import UploadFile
from models import ResponseSignal
import os

class ProjectController(BaseController):
    
    def __init__(self):
        # Type: Sub-function
        super().__init__()

    def get_customer_path(self, customer_id: str):
        # Get or create the file storage directory for a customer. | Customer
        # Type: Main function
        customer_dir = os.path.join(
            self.files_dir,
            customer_id
        )

        if not os.path.exists(customer_dir):
            os.makedirs(customer_dir)

        return customer_dir

    def get_avatar_path(self, profile_id: str):
        # Get or create the avatar storage directory for a profile (customer or company).
        # Type: Main function
        base_dir = os.path.dirname(os.path.dirname(__file__))
        avatars_dir = os.path.join(base_dir, "assets", "avatars", profile_id)

        if not os.path.exists(avatars_dir):
            os.makedirs(avatars_dir)

        return avatars_dir

    
