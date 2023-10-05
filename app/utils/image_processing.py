from io import BytesIO

import PIL
import PIL.Image
from werkzeug.datastructures import FileStorage


class WrongImageFormat(ValueError):
    pass


class CorruptImage(ValueError):
    pass


class ImageProcessor:
    def __init__(self, fp: FileStorage, img_format: str = "png"):
        if not isinstance(fp, FileStorage):
            raise ValueError("Expected fp of type werkzeug.DataStructures.FileStorage")

        self.fp = fp.stream
        self.img_format = img_format
        try:
            self._image = PIL.Image.open(self.fp, formats=(img_format,))
        except PIL.UnidentifiedImageError as e:
            raise WrongImageFormat from e

        try:
            self._image.verify()

            # PIL.Image.verify() closes fp, we need to re-open. We know this shouldn't error.
            self._image = PIL.Image.open(self.fp, formats=(img_format,))

        except Exception as e:  # noqa
            raise CorruptImage from e

    @property
    def size(self) -> tuple[int, int]:
        return self._image.size

    @property
    def height(self) -> int:
        return self._image.height

    @property
    def width(self) -> int:
        return self._image.width

    def resize(self, new_height=None, new_width=None) -> None:
        """Resize an image to fit inside the new size constraints. Maintains aspect ratio."""
        if new_height is not None:
            raise NotImplementedError("`new_height` parameter currently unsupported")

        if new_width > self.width:
            raise NotImplementedError("Cannot increase image size with this method")

        self._image.thumbnail((new_width, self.height), PIL.Image.LANCZOS)

    def pad(self, to_height=None, to_width=None):
        """Pads a smaller image to increase to size.

        Any extra space required is fully transparent.
        """
        if to_width is not None:
            raise NotImplementedError

        if self.height > to_height:
            raise ValueError("Current image is taller than requested height; use `.resize()` instead.")

        if to_height <= 0:
            raise ValueError("Cannot resize to <=0 height")

        height_padding_required = (to_height - self.height) // 2

        # Create a new transparent image and paste the existing image on top, centered vertically.
        new_image = PIL.Image.new("RGBA", (self._image.width, to_height), (255, 0, 0, 0))
        new_image.paste(self._image, (0, height_padding_required))

        self._image = new_image

    def get_data(self) -> BytesIO:
        """Return a BytesIO instance containing the image data"""
        data = BytesIO()

        self._image.save(data, format=self.img_format)
        data.seek(0)

        return data
