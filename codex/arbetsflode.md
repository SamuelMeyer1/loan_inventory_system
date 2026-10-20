# Tokensnålt utvecklingsarbete

## Formulera en avgränsad uppgift

Beskriv beteende, berörd vy, ett konkret exempel och när uppgiften är klar.
Hänvisa till filer i stället för att klistra in dem igen.

```text
I Återlämna: visa antal valda artikelrader bredvid knappen.
Exempel: när två rader är markerade ska knappen visa Återlämna (2).
Följ AGENTS.md och kodkartan. Implementera och verifiera berört flöde.
Klart när både svenska och engelska fungerar och räknaren uppdateras vid avmarkering.
```

För en strukturell ändring, skilj flytten från nytt beteende:

```text
Flytta jobbvyns rendering från app.js till frontend/js/views/jobs.js.
Behåll funktionernas namn och befintligt beteende. Uppdatera scriptordning,
berörda tester och kodkartan. Verifiera gruppjobb och artikelundantag i webbläsaren.
```

## Läsning och avslut

- Börja i berört arbetsflöde och följ anropen därifrån. Läs stora filer i relevanta
  avsnitt. Gör en bred genomgång när uppgiften faktiskt gäller hela arkitekturen.
- Håll en sammanhängande ändring per uppgift. Blanda inte in byte av ramverk,
  format på alla filer eller orelaterade namnbyten.
- Använd Git-diffen för att granska ändringen. Uppdatera bara dokument som påverkas.
- Avsluta med vad som ändrades, utförd verifiering och verkliga begränsningar.
- Vid paus i större arbete: spara några rader om mål, berörda filer, tester och
  nästa steg i projektminnet; undvik fullständiga chattloggar.

Detta upplägg följer OpenAI:s råd om korta startinstruktioner och dokument som
läses efter behov: [officiell vägledning](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra).
Det ger ingen garanterad procentsats eller hård gräns för tokenåtgång.

## Verifiering från projektroten

| Ändring | Kontroll |
| --- | --- |
| Enbart dokument | Kontrollera filhänvisningar, kommandon och avgränsad Git-diff. |
| Backend | `python -m compileall backend main.py` samt tester för berört beteende. |
| Lån / grupper / API | `python -B -m unittest discover -s tests -p 'test_*.py' -v` |
| Lånekorg / återlämningsåtgärder | `node tests/test_loan_cart.cjs` |
| Ändrad JS-fil | Exempel: `node --check frontend/js/actions.js`; testa sedan i webbläsaren. |
| Schema | Testa ny och äldre tillfällig databas samt migrering två gånger. |
| Frontend | Starta/återanvänd `python main.py`, öppna `http://127.0.0.1:8000` och testa berört flöde. |

Kontrollera om port 8000 används innan en ny server startas. Stoppa inte en
befintlig process bara för att den använder porten. Appstart migrerar och fyller
på data; använd en uttryckligen isolerad databas för tester som skriver.
Databassökvägen är idag en Python-konstant, inte ett färdigt kommandoradsval.

Python-testet använder tillfällig SQLite och ett lokalt HTTP-test på ledig port.
Notistester mockar sändning. Node-testet använder simulerad DOM/API och kontrollerar
inte riktig layout, scriptladdning eller hårdvara. Nya tester behöver behålla isoleringen.

Baslinje 2026-09-30: 14 Python-tester och Node-testet godkända. Python och Node
finns i denna miljö; kontrollera installationen vid byte av dator.
