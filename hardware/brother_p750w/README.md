# Brother PT-P750W – PDF-etiketter

Fristående första steg: ange ett befintligt ID och ett valfritt namn. Verktyget
skapar en PDF med namn, Code 128 och ID i klartext. Streckkoden innehåller exakt
det angivna ID:t, inklusive `ID-` om det anges. Inga nya ID:n slumpas fram.

Kör från projektroten (`loan_inventory_system`):

```powershell
python -m pip install -r hardware/brother_p750w/requirements.txt
python -m hardware.brother_p750w.generate_label
```

Eller ange värden direkt:

```powershell
python -m hardware.brother_p750w.generate_label --id ID-12356 --name "Momentnyckel"
```

PDF:er sparas i `hardware/brother_p750w/output/pdf/`. Den fullständiga sökvägen
skrivs ut; öppna filen i en PDF-läsare. Varje körning får ett eget filnamn.
Brother PT-P750W:s Windows-drivrutin/installerare ligger i
`hardware/brother_p750w/drivers/` och installeras separat. Kontrollera enhet
och godkänd version med IT innan installation.
Använd `--output-dir` för en annan målmapp. Utan namn används endast streckkod
och ID. ID måste vara 1–64 utskrivbara ASCII-tecken utan blanksteg i början
eller slutet. Namn stödjer bland annat svenska bokstäver.

## Anropa från befintligt program

```python
from hardware.brother_p750w.generate_label import generate_label

pdf_path = generate_label("ID-12356", name="Momentnyckel")
```

PDF:en är en förhandsvisning, minst 70 × 24 mm. Långa värden gör sidan bredare
så att strecken behåller sin bredd. Svart kod på vit bakgrund med fria marginaler.
Denna layout är inte kalibrerad för skrivarens faktiska utskriftsyta eller tejp.
Nästa steg är att anpassa till installerad tejp och koppla utskrift till Brother.
Ingen skrivare eller databas kontaktas av verktyget. Webbkameraskanning ingår
inte i detta steg; avläsning på faktisk tejp behöver verifieras vid integrationen.
