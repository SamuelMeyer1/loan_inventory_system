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
- Upprepad återlämning får inte öka saldot igen. Valda lån ska tillhöra användaren.
- Behåll kompatibilitet med API:ts äldre enartikelformat när flerartikelstöd ändras.
- Lånespärr, lånetid och aktiv användare måste kontrolleras i backend.
- Notiser ska hantera fel utan att dölja att en databasändring redan genomförts.
  Simuleringsläget kan skicka till testmottagare; mocka transporten i tester.
- `open_door` i `common.py` skriver idag en logghändelse; det är inte färdig
  fysisk styrning av hiss/skåp. Kortläsaren använder däremot `pyscard`.
- Migreringar ska fungera både vid ny databas och upprepad start. Bevara
  användarredigerade meddelandemallar och befintliga lån.

Äldre anteckningar om manuellt inlagda ändhylsor finns i `uppdateringar.md`.
De bevisar inte dagens saldo eller att artiklarna ingår i seed-data.
Tidigare önskemål om placeringen av Lägg till objekt måste stämmas av mot
dagens UI innan de behandlas som återstående arbete.
