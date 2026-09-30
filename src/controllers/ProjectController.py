from .BaseController import BaseController
from fastapi import UploadFile
from models import ResponseSignal
import os

class ProjectController(BaseController):
    
    def __init__(self):
        # Type: Sub-function
        super().__init__()

    def get_project_path(self, project_id: str):
        # Type: Main function
        project_dir = os.path.join(
            self.files_dir,
            project_id
        )

        if not os.path.exists(project_dir):
            os.makedirs(project_dir)

        return project_dir

    
