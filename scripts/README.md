# Scripts

Manual helper scripts for data work.

- `import_articles_excel.py` imports a MaintMaster/Excel export into SQLite.
- `import_sharepoint_simulation.py` imports the reviewed SharePoint workbook and
  exact-name image matches into the launcher's saved simulation only. It is a
  dry run by default; `--apply` creates a timestamped backup before writing.
- `seed_demo_activity.py` adds demo loans and jobs for testing statistics and
  job views.

These scripts are not started by `python main.py`. Run them only when you want
to change or prepare the local database.

SharePoint simulation import prerequisites: `openpyxl` and `Pillow`. Install
them from `requirements-import.txt`. Preview with:

```powershell
python -B scripts/import_sharepoint_simulation.py
```

Write only after reviewing the summary:

```powershell
python -B scripts/import_sharepoint_simulation.py --apply
```

The target is `%LOCALAPPDATA%\LoanInventoryLauncher\simulations\demo.db`.
Existing SharePoint-style `SP-` IDs prevent a second import. To repair only the
two corrected rows, preview with `--repair-corrected-ids`, then add
`--apply`; a backup is created before the update.

