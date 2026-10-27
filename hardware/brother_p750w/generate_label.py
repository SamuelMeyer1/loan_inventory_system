"""Create a preview label PDF; no printer connection is required."""

import argparse
from datetime import datetime
from pathlib import Path
import re
import sys
import uuid

from reportlab.graphics.barcode.code128 import Code128
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "output" / "pdf"


def generate_label(item_id: str, name: str = "", output_dir=None) -> Path:
    """Return a new PDF path. The barcode contains exactly the supplied ID.

    IDs use printable ASCII (Code 128); spaces at either end are rejected
    rather than silently changing an existing inventory identifier.
    """
    if not item_id or len(item_id) > 64 or any(
        not 32 <= ord(char) <= 126 for char in item_id
    ) or item_id != item_id.strip():
        raise ValueError("ID ska vara 1-64 ASCII-tecken utan inledande/avslutande blanksteg.")
    if len(name) > 100 or any(ord(char) < 32 or ord(char) > 255 for char in name):
        raise ValueError("Namn ska vara högst 100 tecken och använda vanliga latinska bokstäver.")

    # Keep bars at a fixed width instead of shrinking long IDs beyond readability.
    # Quiet zones are included by ReportLab. This is a preview, not a tape preset.
    barcode = Code128(item_id, barWidth=0.34 * mm, barHeight=10 * mm, quiet=True)
    width = max(70 * mm, barcode.width + 8 * mm,
                stringWidth(item_id, "Helvetica-Bold", 11) + 8 * mm,
                stringWidth(name, "Helvetica", 9) + 8 * mm)
    height = 24 * mm
    directory = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    directory.mkdir(parents=True, exist_ok=True)
    safe_id = re.sub(r"[^A-Za-z0-9_-]+", "_", item_id)[:48]
    filename = f"label_{safe_id}_{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:8]}.pdf"
    destination = directory / filename
    pdf = canvas.Canvas(str(destination), pagesize=(width, height))
    pdf.setTitle(f"Etikett {item_id}")
    pdf.setFont("Helvetica", 9)
    pdf.drawCentredString(width / 2, height - 4 * mm, name)
    barcode.drawOn(pdf, (width - barcode.width) / 2, 7 * mm)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawCentredString(width / 2, 2.5 * mm, item_id)
    pdf.showPage()
    pdf.save()
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description="Skapa PDF-etikett med ID och Code 128.")
    parser.add_argument("--id", dest="item_id", help="Befintligt ID, exempelvis ID-12356")
    parser.add_argument("--name", help="Valfritt namn på etiketten")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    try:
        item_id = args.item_id if args.item_id is not None else input("Ange ID: ")
        name = args.name if args.name is not None else input("Namn (valfritt, Enter för att hoppa över): ")
        path = generate_label(item_id, name, args.output_dir)
    except (ValueError, OSError) as error:
        parser.exit(1, f"Kunde inte skapa etikett: {error}\n")
    except (EOFError, KeyboardInterrupt):
        print("\nAvbrutet.", file=sys.stderr)
        return 1
    print(f"PDF skapad: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
