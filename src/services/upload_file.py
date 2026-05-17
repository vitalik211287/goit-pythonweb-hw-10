import cloudinary
import cloudinary.uploader
from fastapi import UploadFile

from src.conf.config import settings

cloudinary.config(
    cloud_name=settings.CLD_NAME,
    api_key=settings.CLD_API_KEY,
    api_secret=settings.CLD_API_SECRET,
    secure=True,
)


class UploadFileService:
    def upload_file(self, file: UploadFile, username: str):

        public_id = f"ContactsApp/{username}"

        result = cloudinary.uploader.upload(
            file.file,
            public_id=public_id,
            overwrite=True,
        )

        return result["secure_url"]
