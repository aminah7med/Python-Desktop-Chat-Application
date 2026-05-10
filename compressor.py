import os
from PIL import Image


class ImageCompressor:
    @staticmethod
    def compress(input_path, output_path="temp/compressed.jpg", quality=35):
        try:
            os.makedirs("temp", exist_ok=True)

            image = Image.open(input_path)

            if image.mode in ("RGBA", "P"):
                image = image.convert("RGB")

            image.save(
                output_path,
                "JPEG",
                optimize=True,
                quality=quality
            )

            return output_path

        except Exception as e:
            print("Compression Error:", e)
            return None

    @staticmethod
    def save_hd_copy(input_path, output_path="temp/hd.jpg"):
        try:
            os.makedirs("temp", exist_ok=True)

            image = Image.open(input_path)

            if image.mode in ("RGBA", "P"):
                image = image.convert("RGB")

            image.save(
                output_path,
                "JPEG",
                quality=100
            )

            return output_path

        except Exception as e:
            print("HD Copy Error:", e)
            return None

    @staticmethod
    def get_bytes(file_path):
        try:
            with open(file_path, "rb") as file:
                return file.read()
        except Exception as e:
            print("Read Error:", e)
            return None