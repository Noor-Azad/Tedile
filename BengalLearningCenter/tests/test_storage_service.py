import importlib
import os
import unittest

from app.services.storage_service import StorageService, build_s3_key


class StorageServiceTests(unittest.TestCase):
    def test_build_s3_key_uses_category_and_clean_filename(self):
        key = build_s3_key("students", 125, "My Photo.JPG")
        self.assertEqual(key, "students/125/My_Photo.JPG")

    def test_build_storage_url_uses_bucket_and_region(self):
        service = StorageService(bucket_name="bengal-learning-center", region="ap-south-1")
        url = service.get_public_url("students/125/My_Photo.JPG")
        self.assertEqual(
            url,
            "https://bengal-learning-center.s3.ap-south-1.amazonaws.com/students/125/My_Photo.JPG",
        )

    def test_create_app_uses_production_config_when_app_env_is_production(self):
        original_app_env = os.environ.get("APP_ENV")
        original_debug = os.environ.get("FLASK_DEBUG")

        try:
            os.environ["APP_ENV"] = "production"
            os.environ["FLASK_DEBUG"] = "false"
            import config
            importlib.reload(config)

            import app as app_module
            importlib.reload(app_module)
            app = app_module.create_app()

            self.assertFalse(app.config["DEBUG"])
            self.assertEqual(app.config["S3_BUCKET_NAME"], os.getenv("S3_BUCKET_NAME", "bengal-learning-center"))
        finally:
            if original_app_env is None:
                os.environ.pop("APP_ENV", None)
            else:
                os.environ["APP_ENV"] = original_app_env

            if original_debug is None:
                os.environ.pop("FLASK_DEBUG", None)
            else:
                os.environ["FLASK_DEBUG"] = original_debug

            import config
            importlib.reload(config)
            import app as app_module
            importlib.reload(app_module)


if __name__ == "__main__":
    unittest.main()
