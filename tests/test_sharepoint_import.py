from io import BytesIO
import unittest
from zipfile import ZipFile

from scripts.import_sharepoint_simulation import build_import_rows


def sharepoint_row(excel_row, name, unit_ids):
    return {
        "_excel_row": excel_row,
        "title": name,
        "fabrikat": "Test brand",
        "modell": "Model A",
        "matomrade": "",
        "price_per_unit": None,
        "placering": "Test shelf",
        "id_nummer": unit_ids,
        "bild": "",
        "item_type": "Element",
    }


class SharePointSimulationImportTest(unittest.TestCase):
    def setUp(self):
        self.archive_buffer = BytesIO()
        self.archive = ZipFile(self.archive_buffer, "w")
        self.addCleanup(self.archive.close)

    def test_corrected_rows_get_distinct_ids_and_quantity_one(self):
        rows = [
            sharepoint_row(42, "Kabel", "004712\n004713"),
            sharepoint_row(77, "Termineringsplugg", "004712\n004713"),
        ]

        imported, summary = build_import_rows(rows, self.archive)

        self.assertEqual([(item["object_id"], item["unit_volvo_ids"], item["total_quantity"])
                          for item in imported], [
            ("SP-0042", "004712", 1),
            ("SP-0077", "004713", 1),
        ])
        self.assertEqual(summary["quantity"], 2)

    def test_unexpected_id_reuse_aborts_mapping(self):
        rows = [sharepoint_row(2, "First", "0100"), sharepoint_row(3, "Second", "0100")]

        with self.assertRaisesRegex(ValueError, "ovantade rader"):
            build_import_rows(rows, self.archive)


if __name__ == "__main__":
    unittest.main()
