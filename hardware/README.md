# Hardware

Här samlas adapters och fristående verktyg för hårdvara som programmet
använder.

- `rfid/reader.py`: läs kort-UID via PC/SC och `pyscard`.
- `razer_camera/scanner.py`: fristående liveavläsning av Code 128 med USB-kamera.
- `rfid/drivers/`: plats för godkända RFID-/PC/SC-drivrutiner per läsarmodell.
- `brother_p750w/`: etikettförberedelse för Brother PT-P750W.
- `brother_p750w/drivers/`: Windows-drivrutin/installerare för skrivaren.

`backend/services/smartcard.py` är en kompatibilitetsadapter. Den kopplar
kortläsarens UID till användare i databasen; den fysiska läsningen ligger i
`rfid/reader.py`.

Brother-verktyget skapar i nuläget en PDF. Det skickar ännu inte utskriftsjobb
till skrivaren.
