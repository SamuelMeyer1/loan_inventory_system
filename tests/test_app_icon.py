import struct
import unittest
import zlib

from app_icon import icon_ico, icon_png


class AppIconTest(unittest.TestCase):
    def test_png_dimensions_alpha_and_checksums(self):
        for size in (16, 32, 256):
            with self.subTest(size=size):
                image = icon_png(size)
                self.assertEqual(image[:8], b"\x89PNG\r\n\x1a\n")
                self.assertEqual(struct.unpack(">IIBBBBB", image[16:29]), (size, size, 8, 6, 0, 0, 0))
                offset = 8
                while offset < len(image):
                    length = struct.unpack_from(">I", image, offset)[0]
                    kind = image[offset + 4:offset + 8]
                    data = image[offset + 8:offset + 8 + length]
                    checksum = struct.unpack_from(">I", image, offset + 8 + length)[0]
                    self.assertEqual(checksum, zlib.crc32(kind + data))
                    if kind == b"IDAT":
                        raw = zlib.decompress(data)
                        self.assertEqual(len(raw), size * (1 + 4 * size))
                        self.assertEqual(raw[4], 0)  # Transparent outer corner.
                        center_alpha = (size // 2) * (1 + 4 * size) + 1 + (size // 2) * 4 + 3
                        self.assertEqual(raw[center_alpha], 255)
                    offset += 12 + length
                self.assertEqual(offset, len(image))

    def test_ico_has_all_windows_sizes_and_matching_images(self):
        image = icon_ico()
        self.assertEqual(struct.unpack_from("<HHH", image), (0, 1, 7))
        offset = 6 + 7 * 16
        for index, size in enumerate((16, 24, 32, 48, 64, 128, 256)):
            width, height, colors, reserved, planes, bits, length, start = struct.unpack_from(
                "<BBBBHHII", image, 6 + index * 16)
            self.assertEqual((width, height, colors, reserved, planes, bits),
                             (size % 256, size % 256, 0, 0, 1, 32))
            self.assertEqual(start, offset)
            self.assertEqual(image[start:start + length], icon_png(size))
            offset += length
        self.assertEqual(offset, len(image))
