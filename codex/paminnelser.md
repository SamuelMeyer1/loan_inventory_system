# Domänregler och fallgropar

Kontrollerat mot arbetskopian 2026-09-30. Allmänna arbetsregler finns i `AGENTS.md`.

- Förbrukningsvaror får inte lånas. Backendens `is_consumable_object` känner
  igen både `is_consumable` och vissa beskrivande texter; frontend har egen logik.
  Bevara detta tills en uttrycklig datamigrering ersätter texttolkningen.
- Rapport om slut på lager sätter `available_quantity` till 0.
- Flera artikelrader hör ihop via `request_group_id`. Äldre rader kan sakna
  grupp-ID; befintlig kod använder `COALESCE(request_group_id, request_id)`.
- Gruppflödet är `requested → approved → prepared → loaned → returned → stocked`.
  Gruppändringar och valda återlämningar ska vara atomiska: allt eller inget.
- Godkännande/förberedelse/utlämning av flerartikeljobb kräver gruppanrop.
  Äldre blandade kort får komma ikapp utan att avancerade rader flyttas tillbaka.
  Jobbkortets returformulär använder samma antal-/skadevalidering och
  `expected_returned_quantity` som den separata återlämningssidan.
- Upprepad återlämning får inte öka saldot igen. Valda lån ska tillhöra användaren.
- Lånekorgen visar tillgängligt lager minus den egna korgen; detta är ingen reservation.
  Förfrågan hämtar nytt saldo och servern validerar summerat antal per artikel
  atomiskt mot tillgängligt lager. Faktisk utlåning måste fortfarande kontrollera saldot igen.
- `loans.quantity` är ursprungligt antal; aktivt antal är `quantity - returned_quantity`.
  `loan_returns` innehåller varje retur och skadepost. Nya delreturer måste ange
  `expected_returned_quantity`; validering och saldon ligger i samma skrivtransaktion.
- Skadade returer är `quarantined`, inte tillgängliga. Admin åtgärdar hela posten:
  `repaired` ökar tillgängligt, `discarded` minskar totalt. Jobb får lagerföras först
  när återstående lån och karantän är tomma. Gallring/radering skyddar öppna skador.
- Behåll kompatibilitet med API:ts äldre enartikelformat när flerartikelstöd ändras.
- Lånespärr, lånetid och aktiv användare måste kontrolleras i backend.
- Notiser ska hantera fel utan att dölja att en databasändring redan genomförts.
  Notifieringssimuleringen kan skicka till testmottagare; mocka transporten i tester.
  Startfönstrets isolerade simulering (`LOAN_SIMULATION=1`) spärrar däremot
  alla externa transporter och fysisk kortläsning, och använder en märkt separat
  `simulations/demo.db`. Ändringar sparas mellan starter. Återställning kräver
  stoppad server och arkiverar bara denna demo; testning ska ha eget temporärt storage.
- `open_door` i `common.py` skriver idag en logghändelse; det är inte färdig
  fysisk styrning av hiss/skåp. Kortläsaren använder däremot `pyscard`.
- Migreringar ska fungera både vid ny databas och upprepad start. Bevara
  användarredigerade meddelandemallar och befintliga lån.

Äldre anteckningar om manuellt inlagda ändhylsor finns i `uppdateringar.md`.
De bevisar inte dagens saldo eller att artiklarna ingår i seed-data.
Tidigare önskemål om placeringen av Lägg till objekt måste stämmas av mot
dagens UI innan de behandlas som återstående arbete.
