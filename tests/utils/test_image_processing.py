import io

import pytest
from PIL import Image
from werkzeug.datastructures import FileStorage

from app.utils.image_processing import CorruptImage, ImageProcessor, WrongImageFormat


class TestImageProcessor:
    def test_basic_attributes(self):
        ip = ImageProcessor(FileStorage(open("tests/test_img_files/small-but-perfectly-formed.png", "rb")))

        assert ip.size == (1, 1)
        assert ip.height == 1
        assert ip.width == 1

    def test_errors_if_file_type_different_than_expected(self):
        with pytest.raises(WrongImageFormat):
            ImageProcessor(
                FileStorage(open("tests/test_img_files/small-but-perfectly-formed.png", "rb")), img_format="jpeg"
            )

    def test_errors_if_corrupted_magic_numbers(self):
        with pytest.raises(WrongImageFormat):
            ImageProcessor(FileStorage(open("tests/test_img_files/corrupt-magic-numbers.png", "rb")))

    def test_errors_if_truncated_png(self):
        """A valid PNG file with some bytes removed from the end"""
        with pytest.raises(CorruptImage):
            ImageProcessor(FileStorage(open("tests/test_img_files/truncated.png", "rb")))

    def test_errors_if_corrupted_png(self):
        """A valid PNG file with some bytes removed from the middle"""
        with pytest.raises(CorruptImage):
            ImageProcessor(FileStorage(open("tests/test_img_files/corrupted.png", "rb")))

    def test_resize_image(self):
        ip = ImageProcessor(FileStorage(open("tests/test_img_files/its-a-wide-one.png", "rb")))

        ip.resize(new_width=3)

        assert ip.size == (3, 1)
        assert ip.width == 3
        assert ip.height == 1
        assert ip.get_data().read() == open("tests/test_img_files/its-a-less-wide-one.png", "rb").read()

    def test_resize_image_cannot_increased_width(self):
        ip = ImageProcessor(FileStorage(open("tests/test_img_files/small-but-perfectly-formed.png", "rb")))
        with pytest.raises(NotImplementedError):
            ip.resize(new_width=5)

    def test_resize_image_not_implemented_for_height(self):
        ip = ImageProcessor(FileStorage(open("tests/test_img_files/small-but-perfectly-formed.png", "rb")))
        with pytest.raises(NotImplementedError):
            ip.resize(new_height=5)

    def test_pad_width_not_implemented(self):
        ip = ImageProcessor(FileStorage(open("tests/test_img_files/small-but-perfectly-formed.png", "rb")))
        with pytest.raises(NotImplementedError):
            ip.pad(to_width=5)

    def test_pad_to_zero_height_error(self):
        ip = ImageProcessor(FileStorage(open("tests/test_img_files/small-but-perfectly-formed.png", "rb")))
        with pytest.raises(ValueError):
            ip.pad(to_height=0)

    def test_pad_to_shrink_height_error(self):
        ip = ImageProcessor(FileStorage(open("tests/test_img_files/its-a-tall-one.png", "rb")))
        with pytest.raises(ValueError):
            ip.pad(to_height=3)

    def test_pad_adds_transparency_to_top_and_bottom(self):
        ip = ImageProcessor(FileStorage(open("tests/test_img_files/its-a-tall-one.png", "rb")))

        ip.pad(to_height=10)

        assert ip.size == (1, 10)
        assert ip.width == 1
        assert ip.height == 10

        # Normalize both images
        actual = Image.open(io.BytesIO(ip.get_data().read()))
        expected = Image.open("tests/test_img_files/its-a-taller-padded-one.png")

        actual_bytes = io.BytesIO()
        expected_bytes = io.BytesIO()

        actual.save(actual_bytes, format="PNG")
        expected.save(expected_bytes, format="PNG")

        assert actual_bytes.getvalue() == expected_bytes.getvalue()

    def test_get_data(self):
        ip = ImageProcessor(FileStorage(open("tests/test_img_files/small-but-perfectly-formed.png", "rb")))

        assert ip.get_data().read() == open("tests/test_img_files/small-but-perfectly-formed.png", "rb").read()
