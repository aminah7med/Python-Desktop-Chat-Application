import os
from PIL import Image, UnidentifiedImageError


class ImageCompressor:
    """
    Handles image compression and HD copy before sending over the network.

    Two modes:
      compress()      — quality=35  (small file, fast transfer)
      save_hd_copy()  — quality=95  (high quality, larger file)
    """

    TEMP_DIR = "temp"

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    @staticmethod
    def compress(input_path, output_path=None, quality=35):
        """
        Compress an image to JPEG at the given quality level.
        Returns the output path on success, None on failure.
        """
        if not ImageCompressor._validate(input_path):
            return None

        output_path = output_path or os.path.join(ImageCompressor.TEMP_DIR, "compressed.jpg")
        return ImageCompressor._save_as_jpeg(input_path, output_path, quality)

    @staticmethod
    def save_hd_copy(input_path, output_path=None):
        """
        Save a near-lossless JPEG copy (quality=95).
        Returns the output path on success, None on failure.
        """
        if not ImageCompressor._validate(input_path):
            return None

        output_path = output_path or os.path.join(ImageCompressor.TEMP_DIR, "hd.jpg")
        return ImageCompressor._save_as_jpeg(input_path, output_path, quality=95)

    @staticmethod
    def get_bytes(file_path):
        """Read a file from disk and return its bytes. Returns None on failure."""
        if not file_path or not os.path.exists(file_path):
            print(f"[Compressor] File not found: {file_path}")
            return None
        try:
            with open(file_path, "rb") as f:
                return f.read()
        except Exception as e:
            print(f"[Compressor] Read error: {e}")
            return None

    @staticmethod
    def cleanup_temp():
        """Delete all files in the temp folder (call after sending)."""
        if not os.path.exists(ImageCompressor.TEMP_DIR):
            return
        for filename in os.listdir(ImageCompressor.TEMP_DIR):
            path = os.path.join(ImageCompressor.TEMP_DIR, filename)
            try:
                os.remove(path)
            except Exception as e:
                print(f"[Compressor] Cleanup warning: {e}")

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _validate(input_path):
        """Check the file exists and is a valid image before processing."""
        if not input_path:
            print("[Compressor] No file path provided.")
            return False

        if not os.path.exists(input_path):
            print(f"[Compressor] File not found: {input_path}")
            return False

        try:
            with Image.open(input_path) as img:
                img.verify()   # Raises if file is not a valid image
            return True
        except UnidentifiedImageError:
            print(f"[Compressor] Not a valid image file: {input_path}")
            return False
        except Exception as e:
            print(f"[Compressor] Validation error: {e}")
            return False

    @staticmethod
    def _save_as_jpeg(input_path, output_path, quality):
        """Convert any supported format to JPEG and save to output_path."""
        try:
            os.makedirs(ImageCompressor.TEMP_DIR, exist_ok=True)

            with Image.open(input_path) as image:
                # RGBA and P (palette) modes can't be saved as JPEG
                if image.mode in ("RGBA", "P", "LA"):
                    image = image.convert("RGB")

                image.save(
                    output_path,
                    format="JPEG",
                    optimize=True,
                    quality=quality,
                )

            original_kb  = os.path.getsize(input_path)  / 1024
            compressed_kb = os.path.getsize(output_path) / 1024
            print(
                f"[Compressor] {os.path.basename(input_path)}"
                f"  {original_kb:.0f} KB → {compressed_kb:.0f} KB"
                f"  (quality={quality})"
            )
            return output_path

        except Exception as e:
            print(f"[Compressor] Save error: {e}")
            return None
