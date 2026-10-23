"""Original inventory-box icon shared by the launcher and Windows packaging."""
from __future__ import annotations

import struct
import zlib


def icon_png(size: int) -> bytes:
    if not 16 <= size <= 256:
        raise ValueError("Icon size must be between 16 and 256.")
    scale = 4 if size <= 64 else 2
    side = size * scale
    pixels = bytearray(side * side * 4)

    def paint(x: int, y: int, color: tuple[int, int, int, int]) -> None:
        offset = (y * side + x) * 4
        pixels[offset:offset + 4] = bytes(color)

    for y in range(side):
        for x in range(side):
            px, py = (x + 0.5) * 100 / side, (y + 0.5) * 100 / side
            cx, cy = min(80, max(20, px)), min(80, max(20, py))
            if (px - cx) ** 2 + (py - cy) ** 2 <= 16 ** 2:
                paint(x, y, (27, 70 + int(py / 5), 112 + int(py / 5), 255))

    def polygon(points: list[tuple[int, int]], color: tuple[int, int, int, int]) -> None:
        for y in range(side):
            py = (y + 0.5) * 100 / side
            crossings = []
            for (ax, ay), (bx, by) in zip(points, points[1:] + points[:1]):
                if (ay <= py < by) or (by <= py < ay):
                    crossings.append(ax + (py - ay) * (bx - ax) / (by - ay))
            crossings.sort()
            for left, right in zip(crossings[::2], crossings[1::2]):
                for x in range(max(0, int(left * side / 100)), min(side, int(right * side / 100))):
                    paint(x, y, color)

    polygon([(22, 35), (50, 21), (78, 35), (50, 49)], (245, 252, 255, 255))
    polygon([(22, 40), (47, 53), (47, 81), (22, 67)], (193, 220, 235, 255))
    polygon([(53, 53), (78, 40), (78, 67), (53, 81)], (235, 247, 252, 255))

    raw = bytearray()
    for y in range(size):
        raw.append(0)
        for x in range(size):
            samples = [((y * scale + sy) * side + x * scale + sx) * 4
                       for sy in range(scale) for sx in range(scale)]
            alpha = sum(pixels[index + 3] for index in samples)
            for channel in range(3):
                raw.append(round(sum(pixels[index + channel] * pixels[index + 3]
                                     for index in samples) / alpha) if alpha else 0)
            raw.append(round(alpha / len(samples)))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw))
            + chunk(b"IEND", b""))


def icon_ico() -> bytes:
    sizes = (16, 24, 32, 48, 64, 128, 256)
    images = [icon_png(size) for size in sizes]
    directory = bytearray(struct.pack("<HHH", 0, 1, len(sizes)))
    offset = 6 + 16 * len(sizes)
    for size, image in zip(sizes, images):
        directory.extend(struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(image), offset))
        offset += len(image)
    return bytes(directory) + b"".join(images)
