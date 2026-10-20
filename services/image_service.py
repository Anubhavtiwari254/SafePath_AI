import os
import uuid
import logging
from pathlib import Path
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from config import Config

logger = logging.getLogger(__name__)


class ImageService:
    """Handles secure image upload, validation, EXIF metadata stripping, and optimization."""

    @classmethod
    def allowed_file(cls, filename: str) -> bool:
        if not filename or "." not in filename:
            return False
        ext = filename.rsplit(".", 1)[1].lower()
        return ext in Config.ALLOWED_EXTENSIONS

    @classmethod
    def save_hazard_photo(cls, file: FileStorage) -> str:
        """
        Validate, strip GPS/EXIF metadata, resize if oversized, and store safely.
        Returns the saved unique filename.
        """
        if not file or not file.filename:
            raise ValueError("No file provided.")

        if not cls.allowed_file(file.filename):
            raise ValueError(f"File type not supported. Allowed formats: {', '.join(Config.ALLOWED_EXTENSIONS)}")

        # Ensure upload folder exists
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

        original_ext = file.filename.rsplit(".", 1)[1].lower()
        if original_ext == "jpeg":
            original_ext = "jpg"
        unique_name = f"hazard_{uuid.uuid4().hex[:16]}.{original_ext}"
        destination_path = Path(Config.UPLOAD_FOLDER) / unique_name

        try:
            # Attempt processing with Pillow to strip EXIF GPS metadata
            from PIL import Image

            img = Image.open(file.stream)
            img_format = img.format or "JPEG"

            # Check if image has RGB mode for JPEG
            if img.mode in ("RGBA", "P") and original_ext in ("jpg", "jpeg"):
                img = img.convert("RGB")

            # Resize if dimensions exceed 1600px
            max_size = (1600, 1600)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)

            # Save without EXIF data (stripping GPS and camera info)
            # Create fresh image copy without original metadata dictionary
            clean_img = Image.new(img.mode, img.size)
            clean_img.putdata(list(img.getdata()))
            clean_img.save(destination_path, format=img_format, quality=85, optimize=True)
            logger.info("Saved image with stripped EXIF: %s", unique_name)
            return unique_name

        except ImportError:
            # If Pillow is not available yet, save safely after extension verification
            logger.warning("Pillow not installed. Saving file directly after extension validation.")
            file.seek(0)
            file.save(str(destination_path))
            return unique_name
        except Exception as e:
            logger.error("Error processing photo upload: %s", e)
            raise ValueError("Invalid or corrupted image file.")
