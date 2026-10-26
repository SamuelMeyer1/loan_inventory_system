# Todo: buggar och förbättringar

Senast uppdaterad: 2026-10-26. Status avser version 1.18.0.

Gemensam lista för rapporterade buggar och överenskomna förbättringar.
Varje punkt har ett beständigt ID och ett kort namn så att vi kan hänvisa
till den, till exempel **T006 – Antal vid jobbretur**.

## Kvar att göra

- [x] **T028 – Certifikatfel vid uppdateringskontroll** (1.18.2)
  1.18.0 fick `CERTIFICATE_VERIFY_FAILED / unable to get local issuer certificate`
  medan Edge på samma dator kunde läsa GitHubs release-API. Uppdateringsanropet
  använder nu truststore och Windows certifikatverifiering med bibehållen
  värdnamns-/kedjekontroll. Lokal API-kontroll och riktade tester godkända;
  exakt orsak i testdatorns certifikatkedja är inte fastställd.
  Användarens bild 2026-10-26 kl. 10:22 bekräftar fungerande kontroll på
  testdatorn: installerad och publicerad version 1.18.2, utan certifikatfel.
  Erbjudande och nedladdning av en senare version återstår att prova där.

- [x] **T027 – Versionskontroll vid start** (1.18.0)
  Kontroll mot separat publikt release-repo, fråga innan webbläsaren öppnar
  rätt produktions-Setup. Ingen automatisk installation och ingen publicering
  av kodrepo/databaser. BAT-källkod uppdateras inte av Setup.
  Första release publiceras manuellt av ägaren; appen ska hantera att den saknas.
  Verifierat mot det publika repot utan release, med 26 riktade tester,
  verkligt Tk-fönster (asynkron kontroll och samtycke) och fryst installationsprov.
  Publicering på GitHub återstår som manuellt ägarsteg; inget har laddats upp.

### Test 1 – 2026-10-26

- [x] **T025 – Tydligare gemensamma Adminnotiser** (1.17.0)
  Efter förtydligande: ingen separat granskning av jobb. Endast klockan
  pulserar orange vid olästa händelser. Öppnad panel läsmarkerar för både
  Admin och Superadmin; jobbet ändras inte. Länken heter Gå till jobblistan.
  Senaste 20 händelser finns kvar; läsmarkering raderar inte historiken.
  Samtidiga nya händelser lämnas olästa. Minskad rörelse stänger av animation.
- [x] **T026 – Stäng notispanelen utanför klockan** (1.17.0)
  Klick utanför (även på rubriken Jobb), navigation och Escape stänger
  panelen. Klick inne i panelen stänger den inte. Webbläsartestat.

### Lista från 2026-10-23 – påbörjad 2026-10-26

Användaren valde att börja med T019, T020 och T022. Dessa är klara i 1.15.1.
Listan nedan följer användarens sju punkter. T017, T018 och T021
återstår; deras öppna beslut ska stämmas av innan genomförande.

- [ ] **T017 – Tydligare låneformulär** (punkt 1, öppet designbeslut)
  Engine ID, Project Number och övriga låneuppgifter smälter ihop med
  artikelvalet. Överväg att flytta upp och gruppera dem tydligare så att nästa
  steg blir begripligt. Användaren har ännu inte bestämt att de ska flyttas.
- [ ] **T018 – Interna villkor och kontaktgodkännande** (punkt 2)
  Utöver dataskyddsinformationen önskas ett separat godkännande efter att
  låntagaren läst de interna lånevillkoren, med underlag i bifogad bild 2.
  Ta även upp kontakt via e-post och SMS inför återlämning och vid sen retur.
  Exakt villkorstext, vilka godkännanden som krävs och hur kontaktvalen ska
  fungera behöver fastställas. Detta innebär inte att SMS-sändning redan finns.
- [x] **T019 – Tomt antal vid full lånekorg** (punkt 3, klart i 1.15.1)
  Repro enligt bilder 3–5: ha OBJ-1001 vald och 3 av 4 tillgängliga exemplar
  i korgen. Öka korgradens antal till 4. Kvar att välja blir 0 av 4 och
  Antal-fältet blir tomt (beskrivet som "NULL"). Därefter visas
  "Saknar uppgift – Ange ett positivt heltal."
  Reproducerat med regressionstest: sändning försökte lägga till samma artikel
  igen trots att korgraden redan hade rätt antal. Sändning bevarar nu antalet
  för redan tillagda artiklar. Lägg till artikel är inaktiverad vid 0 kvar,
  med texten Inga fler att lägga till i antalvalet. Webbläsartestat att
  OBJ-1001 kan skickas med exakt 4 exemplar, även tillsammans med annan artikel.
- [x] **T020 – Bekräftelse utan ordet karantän** (punkt 4, klart i 1.15.1)
  Bekräftelsen visar fortfarande antal återlämnade och skadade, men inte
  ordet karantän. Verifierat på svenska och engelska. Skadat material
  spärras fortsatt och återförs inte till tillgängligt lager.
- [ ] **T021 – Översyn av skadehanteringen** (punkt 5, senare arbete)
  Se över hela flödet för skador/defekter och karantän.
  Ingen ombyggnad nu; omfattning och önskat arbetsflöde behöver beslutas.
  Ta inte bort spärrar för skadade exemplar som en bieffekt av T020.
- [x] **T022 – Retur utan skadebeskrivning** (punkt 6, klart i 1.15.1)
  Skadebeskrivning döljs vid 0 skadade i både retursidan och jobbkortet.
  Fältet visas och krävs när skada anges. Byte tillbaka till 0 rensar
  inaktuell beskrivning. Verifierat frisk retur utan text, skada med
  obligatorisk text, språkbyte med bevarat skadeutkast samt mobilvy.
- [x] **T023 – Varning för skada eller delretur på jobbet** (1.17.0)
  Test 1 förtydligade önskemålet: varningstriangel bredvid artikelantalet,
  med antal, skadebeskrivning och åtgärd under Visa artiklar/Detaljer.
  Lagerför allt är inaktiverad vid kvarvarande lån eller olösta skador.
  Grunddemons jobb #32 har avsiktligt en ej åtgärdad skada; efter reparation
  försvinner varningen och lagerföring fungerar utan dubblerat saldo.
  Testat delretur, skada, reparation, lagerföring och båda språken.
  Ingen ny skadehändelse i notisklockan eller externa utskick införs.
  Detta är inte den större ombyggnaden i T021.

Bilderna hör till chatten 2026-10-23 kl. 16:20. Personliga kontaktuppgifter
från bilderna kopieras inte till denna lista.

### Tidigare lista med åtta önskemål

De tidigare åtta överenskomna önskemålen nedan är genomförda. SMS avser bara en
inaktiverad symbol, inte fungerande SMS-sändning. Distributionsvarningarna
är fortfarande olösta.

| Ursprunglig punkt | Kort namn | Todo-ID |
| --- | --- | --- |
| 1 | Knappar bredvid login | T001 |
| 2 | Låntagare utan roll | T002 |
| 3 | Inaktivitet och manuell lånetillåtelse | T003, T014, T016 |
| 4 | Visa mer för objekt | T004 |
| 5 | Adminnotiser | T015, T016 |
| 6 | Framtida SMS-symbol | T005 |
| 7 | Antal vid återlämning | T006 |
| 8 | Gemensamma steg på jobbkortet | T007 |

## Känd begränsning – inte löst

- [ ] **T008 – Edge- och Windowsvarningar** (distribution)
  Installationsfilen är osignerad och kan ge nedladdnings-/SmartScreenvarningar.
  Ny ikon och serverfixar löser inte detta. Ingen köpt signering är planerad;
  självsignering ger inte automatiskt förtroende på kollegornas datorer.
  Skydd ska inte stängas av eller kringgås. En accepterad distributionslösning
  återstår; varningsfri installation kan inte utlovas.

## Klart

- [x] **T024 – Sparad demonstration med återställning** (1.16.0)
  Egen simuleringsdatabas med 5 grupper, 15 påhittade interna/externa personer,
  befintliga 8 artiklar, 20 pågående jobb (24 lånerader), 7 återlämnade samt
  förfrågningar och äldre historik. Spärrar, inaktivitet, delretur, skador och
  varierade lagerlägen finns med. Teständringar sparas mellan starter.
  Återställning efter stopp arkiverar bara demon och skapar ny data vid nästa
  start. Verifierat i webbläsare, startfönster och fryst installationspaket:
  sparad ändring efter omstart, arkivering/återskapande och spärr under drift.
  128 Python-tester och fem JavaScript-testsviter godkända.

- [x] **T001 – Knappar vid login** (1.15.0)
  Sök och språk ligger intill inloggningen till höger.
  Simuleringsmarkeringen ligger kvar till vänster. Små skärmar får radbrytning.
- [x] **T002 – Låntagare utan rollval** (1.15.0)
  Rollvalet och låntagartabellens rollkolumn är borttagna. Formuläret förklarar
  att profilen inte är ett inloggningskonto. Befintliga lagrade roller bevaras;
  riktiga kontons behörigheter ändras inte.
- [x] **T003 – Förtydliga aktiv användare** (1.15.0)
  Manuell lånetillåtelse visas bara vid redigering, som
  Tillåt utlåning till personen, med förklaring. Den är skild från
  inaktivitetsvarningen och avstängda personer återaktiveras inte automatiskt.
- [x] **T004 – Visa mer för objekt** (1.15.0)
  Extrauppgifter är utfällbara. Namn, kvarvarande antal och status visas direkt.
  Byte/rensning av objekt stänger detaljerna; uppdatering av samma objekt
  behåller öppet läge.
- [x] **T005 – SMS-symbol** (1.15.0)
  Inaktiverad mobilknapp bredvid hämtningsmejlet är märkt som framtida funktion.
  Ingen SMS-sändning sker.
- [x] **T006 – Antal vid jobbretur** (1.15.0)
  Jobbkortet öppnar ett formulär med antal och eventuella skador per artikel.
  Avbryt/Escape ändrar inget; 0 hoppar över artikeln. Efter 4 av 15 visas
  4 återlämnade och 11 kvar. Aktuella antal hämtas och inaktuella returer
  avvisas med synligt fel i formuläret.
- [x] **T007 – Gemensamma jobbsteg** (1.15.0)
  Godkännande, förberedelse och utlämning sker för hela kortet.
  Oönskade artiklar kan tas bort före utlämning. API:t avvisar enskild
  framflyttning i flerartikeljobb, med bevarat stöd för äldre enartikelanrop.
  Äldre blandade kort kan stegvis komma ikapp utan att öppna avslutade lån igen.
- [x] **T009 – Serverstart och avbruten anslutning** (1.13.1)
  Servern börjar lyssna först efter initiering. Avbrutna svar hanteras utan
  upprepade felutskrifter på samma trasiga anslutning. Användaren har bekräftat
  uppstart utan serverfel.
- [x] **T010 – Boxikon på genvägar** (1.13.4)
  Installationen använder en separat versionsmärkt boxikon för skrivbords-
  och startmenygenvägar. Installation och uppgradering är testade lokalt;
  resultatet på kollegans dator är ännu inte bekräftat.
- [x] **T011 – Visa mer för låntagare** (1.13.4)
  Namnet visas direkt och extra kontaktuppgifter kan fällas ut och döljas.
- [x] **T012 – Stoppa fler än lagersaldot** (1.13.5)
  Exempelvis 16 exemplar när bara 15 finns avvisas både i gränssnittet och
  på servern, även när flera rader tillsammans överskrider saldot.
- [x] **T013 – Räkna bort egen lånekorg** (1.13.5)
  Tillgängligt antal i lånevyn räknar bort den egna korgen och uppdateras
  vid ändring eller borttagning. Korgen reserverar inte verkligt lager;
  lagret minskas först vid utlämning.
- [x] **T014 – Inaktivitetsvarning vid namn** (1.14.0)
  Varning visas efter valt antal dagar utan lån, normalt 365 dagar.
  För personer som aldrig lånat används registreringsdatum om det finns.
  Pågående ärenden undantas. Ingen raderas eller spärras automatiskt.
- [x] **T015 – Adminnotiser** (1.14.0)
  Klocka vid inloggningen visar nya låneförfrågningar och/eller genomförda
  utlån enligt valda inställningar. Lässtatus sparas separat för varje Admin.
- [x] **T016 – Inställningar för reglerna** (1.14.0)
  Systemadmin kan under System → Allmänt slå av/på inaktivitetsvarningen,
  ange antal dagar och välja typer av Adminnotiser. Valen sparas över omstarter.

## Håll listan uppdaterad

- Lägg nya rapporterade buggar och överenskomna förbättringar här med nästa
  lediga ID, ett kort namn och en kort beskrivning av önskat beteende.
- Komplettera en befintlig punkt vid samma problem i stället för att skapa
  dubbletter. Behåll ID:t när punkten flyttas mellan avsnitt.
- Markera klart först när beteendet är verifierat och ange version.
  Skilj mellan lokalt verifierat och bekräftat på användarens dator.
- Allmänna, ännu inte beslutade idéer finns i [Ides](../Ides).
  Versionshistoriken finns i [uppdates](../uppdates); denna lista visar arbetsläget.
