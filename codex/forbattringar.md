# Prioriterad kod- och strukturgranskning

Status 2026-10-15: V1.6.0 lägger till serverbehörighet, lokala konton och
dataskyddsverktyg; SMTP-svar maskeras sedan V1.5.3 och Chart.js finns nu lokalt.
Delar av tabellen nedan är historiska fynd. Se `docs/dataskydd.md` för aktuellt
dataskyddsstöd och kvarstående risker, inklusive äldre Git-spårade datafiler.

Datum: 2026-09-30. Underlag: nuvarande arbetskopia, inklusive ej incheckade
ändringar. Detta är en strukturgranskning och riktad kodläsning, inte en fullständig
säkerhets- eller prestandarevision. Förslagen nedan är inte implementerade.

## Åtgärda korrekthet före större flyttar

| Prio | Konkret fynd | Föreslagen ändring och kontroll |
| --- | --- | --- |
| Hög | `loans.py`: `checkout` och `issue_item` läser saldo via `row()` innan skrivtransaktionen. Servern använder `ThreadingHTTPServer`. Två anrop kan därför utgå från samma gamla saldo. | Läs, validera och uppdatera i en gemensam transaktion med `BEGIN IMMEDIATE`, enligt gruppflödet. Testa två samtidiga uttag av sista exemplaret: bara ett ska lyckas. Risk identifierad i kod; samtidighetsfelet har inte reproducerats här. |
| Hög inför delad drift | `server.py` lämnar ut `get_system_settings()` direkt; den innehåller även `smtp_password`. Även uppdateringssvaret returnerar inställningarna. `refreshAll` hämtar dem oavsett UI-roll. | Separera publika inställningar från privata transportinställningar. Returnera exempelvis bara `smtp_password_configured`; testa GET/PUT utan lösenord i svar. Inför verklig serverautentisering/behörighet innan flera användare får åtkomst över nätet. Nuvarande standardbindning är localhost. |
| Hög för repo-hygien | `git ls-files data` visar redan spårade databaser, backuper och loggar trots `.gitignore`. | Planera att avregistrera uttryckligt valda filer ur Git-index med lokala kopior bevarade. Kontrollera backup först. Att ändra ignore-regler tar inte bort tidigare spårning eller historik. Ingen avregistrering eller historikomskrivning gjord i denna genomgång. |

## Störst nytta för fortsatt utveckling

Radantal är en ögonblicksbild, inte föreskrivna gränser.

| Prioritet | Nuläge / observation | Nästa steg |
| --- | --- | --- |
| 1 | `app.js`: 1 711 rader med state, navigation, jobb, användare, inställningar, export och bilder. `actions.js`: 846 rader. | Flytta en sammanhängande vy åt gången. Börja med jobb eller inställningar. Behåll namn och globala kontrakt under första flytten. |
| 2 | `loans.py`: 905 rader med lån, förfrågningar, förbrukningsrapporter och notisanrop. | Bryt först ut förbrukningsrapportering, sedan förfrågningar och deras statusregler. Behåll `services/__init__.py` som publik ingång och skicka samma `db`-anslutning genom atomiska operationer. |
| 3 | `refreshAll` hämtar tio API-resurser. Återlämning, hämtning och egna lån renderas två gånger. `statistics_data` beräknar dessutom dashboard-siffror som även hämtas separat. | Börja med att kontrollera beroenden och ta bort dubbelrendering. Inför därefter uppdatering per berörd vy/resurs. Mät anrop och rendering före/efter. |
| 4 | `inventory.py:list_objects` läser alla kolumner, inklusive bilder. `TABLE_RENDER_LIMIT = 500` begränsar rendering, inte hämtningen. | Lägg till serverpaginering och separata bildresurser när datamängden motiverar det. Bevara bilddelning via beskrivning och definiera hur sök/export hanterar alla sidor. |
| 5 | `styles.css`: 2 688 rader; `index.html`: 1 302 rader. | Dela CSS i bas, layout, komponenter och vyer med bibehållen kaskadordning. Flytta HTML först när en vald vy behöver det; undvik att införa ett byggsystem bara för filantalets skull. |
| 6 | `notifications.py` innehåller fortfarande inställningar, mallar, mottagarval och påminnelsepolicy. SMTP och Teams-transport ligger nu i `software/communications/`. `now_text`/`log_event` finns även i `common.py`. | Separera inställningar och mallar först när ett konkret flöde behöver det. Mocka `software.communications.smtp` vid transporttester. |
| 7 | `server.py` upprepar routing/felhantering. GET-fel, till exempel ogiltigt numeriskt `limit`, har inte samma skydd som POST. | Samla JSON-validering och felhantering, testa trasig JSON och ogiltiga parametrar. Domänvisa routefiler kan vänta tills routingen växer mer. |
| 8 | `database.py` blandar schema och successiva migreringar. | Inför namngivna migreringssteg/versionstabell när schemat fortsätter växa. Behåll vägen från äldre databaser. Använd syntetiska äldre scheman i tester. |

## Exempel på målstruktur

Detta är en möjlig stegvis målbild. Skapa mapparna när kod faktiskt flyttas dit;
tomma lager och en fil per liten hjälpfunktion gör projektet svårare att överblicka.

```text
AGENTS.md                       korta gemensamma projektinstruktioner
codex/                          kodkarta, arbetssätt, prioriteringar
docs/                           systemförklaring; senare api.md och testing.md vid behov
backend/
  server.py                     HTTP och routing
  database.py                   anslutning och migreringsingång
  services/
    __init__.py                 stabil publik ingång
    loans.py                    direktutlåning och återlämning
    loan_requests.py            förfrågningar och gruppstatus
    consumables.py              uttag och slutrapporter
    inventory.py, users.py, stats.py, common.py, smartcard.py
    settings.py                 validering, publika/privata inställningar
    notifications.py            samordning av notiser
  integrations/                 när transporter bryts ut
    email.py, teams.py
frontend/
  index.html                    sidans skal och scriptordning
  js/
    app.js                      start och samordning
    state.js                    gemensamt tillstånd
    api.js, i18n.js, translations.js, ui-utils.js
    views/                      jobb, objekt, användare, inställningar
    actions/                    motsvarande användaråtgärder
    loan-views.js, search.js, charts.js
  css/
    base.css, layout.css, components.css, views.css
tests/                          befintliga tester; dela efter domän när antalet växer
scripts/                        import och utvecklingsverktyg
windows-installation/           installationsskript och paketinstruktioner
data/                           lokala driftsdata med dokumenterad backuphantering
```

Välj antingen fortsatt global scriptmodell under flyttarna eller ett separat
projekt för ES-moduler med explicita imports. Enbart fler filer löser inte
beroenden mellan globalt state, DOM och renderingsfunktioner.

## Filer och distribution

- **`uppdates` och `Ides`:** byt på sikt till `CHANGELOG.md` och `docs/backlog.md`
  i en egen ändring. Uppdatera `AGENTS.md`, README, paketbyggaren och övriga
  referenser samtidigt. Behåll en enda auktoritativ versionslogg.
- **Tester:** `tests/` är ännu ospårad i den granskade arbetskopian. Ta med testerna
  när de tillhörande kodändringarna checkas in. Lägg först till täckning för direktuttag,
  inställningssvar och felhantering; dela i domänmappar senare vid behov.
- **`.work/`:** innehåller tillfälliga auditfiler. Granska dem och flytta återanvändbara
  verktyg till `scripts/` innan mappen eventuellt ignoreras. Radera inte automatiskt.
- **Installation:** `windows-installation/offline/` innehåller Python-installation
  och wheels. Håll stora leveranspaket utanför vanliga koddiffar; dokumentera
  versioner och hur ett offlinepaket återskapas innan lagringsplats ändras.
- **Offlinefunktion:** `index.html` hämtar Chart.js från en extern CDN utan
  versionslåsning. Diagrammen har alltså ett nätberoende trots offlineinstallationen.
  Paketera en testad version lokalt och verifiera statistikvyn utan nät.
- **Beroenden:** dokumentera testade Python-/paketversioner. Skilj vid behov på
  import- och kortläsarstöd så att installation och felsökning blir tydligare.

## Föreslagen ordning och klart-kriterier

1. **Projektminne** — genomfört i denna uppgift: kortare startinstruktioner,
   kodkarta, uppdaterade testkommandon och den här prioriteringen.
2. **Korrekthet** — isolerade tester för direktuttag och känsliga inställningssvar,
   följt av avgränsade rättningar. Samtidiga lån får inte skapa fel saldo.
3. **Första kodflytten** — välj jobbvyn eller förbrukningsrapporter. Samma beteende,
   fungerande anrop/scriptordning och relevanta tester ska vara kvar.
4. **Prestanda och distribution** — mät `refreshAll`, minska dubbelarbete och
   verifiera offlinepaketet. Arbeta vidare med paginering utifrån verkligt behov.

Behåll Python/SQLite och den statiska frontendens enkelhet under dessa steg.
Det finns redan en användbar serviceuppdelning; bygg vidare på den.

## Verifiering av genomgången

- `python -B -m unittest discover -s tests -p 'test_*.py' -v`: 14 godkända tester.
- `node tests/test_loan_cart.cjs`: godkänt.
- Ingen appkod ändrad och ingen webbläsar-, hårdvaru- eller prestandatest utförd.
- Live-databasen har inte öppnats för granskning eller ändrats av denna uppgift.
