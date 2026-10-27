# Razer Kiyo – testa streckkodsavläsning

Kör från projektroten `loan_inventory_system`:

```powershell
python -m pip install -r hardware/razer_camera/requirements.txt
python -m hardware.razer_camera.scanner
```

Du kan också köra filen direkt: `python hardware/razer_camera/scanner.py`.
Koppla in Kiyo med USB. Programmet öppnar en livebild och läser Code 128,
samma format som Brother-verktyget skapar. Ingen OCR av tryckta siffror ingår.
Ingen Razer SDK används; kameran öppnas via Windows vanliga kameragränssnitt.

Visa hela streckkoden inklusive vita marginaler. Avläst ID skrivs med `print`
på en egen rad i terminalen, exempelvis `12345`. `00123` och `ID-12345`
bevaras exakt. Samma värde måste läsas i två bildrutor i följd. En kod skrivs
bara en gång medan den hålls framför kameran; ta bort den minst en sekund
och visa den igen för att läsa samma kod på nytt. Olika koder kan läsas direkt
efter varandra. Flera synliga koder kan ge flera avläsningar.

En grön ram markerar hittade koder. Senaste avlästa värdet visas i livebilden.
Avsluta med **Q**, **Esc**, fönstrets kryss eller **Ctrl+C**.
Inga bilder eller avläsningar sparas till disk. Ingen utlåning registreras.
Status/fel går till stderr, ID:n till stdout för senare programintegration.

## Om fel kamera öppnas

Kamera 0 är inte garanterat din Kiyo. Prova:

```powershell
python -m hardware.razer_camera.scanner --camera 1
python -m hardware.razer_camera.scanner --camera 2
```

Programmet försöker DirectShow och därefter Media Foundation på Windows.
Vid problem kan du välja `--backend msmf` manuellt. Stäng andra kameraappar
och kontrollera **Inställningar → Sekretess och säkerhet → Kamera → Tillåt
skrivbordsappar att komma åt kameran**. `opencv-python-headless` ger inget
kamerafönster; använd paketet i requirements-filen.

## Testa innan skrivaren fungerar

Skapa en etikett med Brother-verktyget och visa PDF:en på en annan skärm eller
mobil framför kameran. Använd en tydlig, stor kod och undvik reflexer. Håll
etiketten stilla och prova olika avstånd för skärpa. Avläsning på riktig tejp
måste också provas när skrivaren är installerad.

Framtida huvudprogram kan använda `decode_frame(frame)` och `ScanFilter`,
eller läsa ID-rader från denna process. Kopplingen till produkt/utlåning och
validering mot befintliga ID:n görs då av huvudprogrammet.

## Starta utifrån och hämta ett ID

Ett annat Python-program kan anropa `scan_once` när exempelvis en knapp trycks
eller en begäran kommer in. Importen startar inte kameran. Anropet startar
livebilden, väntar på ett bekräftat ID och stänger kameran innan det returnerar:

```python
from hardware.razer_camera.scanner import scan_once

# Kör när huvudprogrammet vill starta en skanning.
scanned_id = scan_once(camera_index=1, backend="dshow")
if scanned_id is not None:
    print("Avläst ID:", scanned_id)
    # Här kan huvudprogrammet söka upp prylen och hantera utlåningen.
else:
    print("Skanningen avbröts.")
```

`scanned_id` är en sträng (t.ex. `"00123"`), så inledande nollor bevaras.
Q, Esc, stängt fönster eller Ctrl+C ger `None`. Kamerafel ger ett undantag
som anroparen kan fånga. Funktionen väntar tills skanningen är klar; kör den
från huvudtråden i ett lokalt skrivbordsprogram. Funktionen ska inte anropas
direkt i webbserverns HTTP-tråd. Senare serverkoppling behöver en separat
lokal kameraprocess. Visa bara en kod åt gången i detta läge; flera koder
accepteras inte som ett entydigt resultat. Varje nytt anrop startar en ny
skanning utan att återanvända något gammalt ID. Ingen global variabel behövs.

Samma engångsskanning kan testas från terminalen:

```powershell
python -m hardware.razer_camera.scanner --camera 1 --backend dshow --once
```

ID skrivs till stdout och processen avslutas med kod 0. Avbrutet utan ID ger
kod 2; fel ger kod 1 och feltext i stderr. Utan `--once` fortsätter det tidigare
kontinuerliga testläget. Huvudprogrammets `main.py` är ännu inte inkopplat.
