# Only application code imported by the entry point and these explicit assets
# enter the distribution. Never collect the repository or its data directory.
from pathlib import Path
import sys
from PyInstaller.utils.hooks import collect_submodules, copy_metadata

root = Path(SPECPATH).parent
assets = [
    "frontend/index.html", "frontend/privacy.html", "frontend/styles.css",
    "frontend/js/actions.js", "frontend/js/api.js", "frontend/js/app.js",
    "frontend/js/charts.js", "frontend/js/i18n.js", "frontend/js/loan-views.js",
    "frontend/js/privacy.js", "frontend/js/search.js", "frontend/js/session.js",
    "frontend/js/translations.js", "frontend/js/ui-utils.js",
    "frontend/vendor/chart.umd.js", "frontend/vendor/Chart.js-LICENSE.md",
    "frontend/sample-images/bit-set.svg", "frontend/sample-images/caliper.svg",
    "frontend/sample-images/fuse-pack.svg", "frontend/sample-images/inductive-sensor.svg",
    "frontend/sample-images/pneumatic-adapter.svg", "frontend/sample-images/pressure-sensor.svg",
    "frontend/sample-images/relay-module.svg", "frontend/sample-images/service-cable.svg",
    "frontend/sample-images/threadlocker.svg", "frontend/sample-images/torque-wrench.svg",
]
datas = [(str(root / name), str(Path(name).parent)) for name in assets]
datas += [(str(root / "windows-installation" / "SETUP.md"), "docs"),
          (str(root / "docs" / "dataskydd.md"), "docs"),
          (str(Path(sys.base_prefix) / "LICENSE.txt"), "licenses/python")]
for package in ("openpyxl", "et-xmlfile", "pyscard", "pyinstaller", "truststore"):
    datas += copy_metadata(package)

a = Analysis(
    [str(root / "desktop_entry.py")], pathex=[str(root)],
    binaries=[], datas=datas,
    hiddenimports=collect_submodules("openpyxl") + collect_submodules("smartcard"),
    hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=["pytest", "numpy", "pandas", "matplotlib", "IPython"],
    noarchive=False,
)
pyz = PYZ(a.pure)
gui = EXE(pyz, a.scripts, [], exclude_binaries=True, name="LoanInventory",
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          icon=str(root / "build" / "windows" / "loan-inventory.ico"),
          console=False, version=str(Path(SPECPATH) / "version-info.txt"))
admin = EXE(pyz, a.scripts, [], exclude_binaries=True, name="LoanInventoryAdmin",
            debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
            icon=str(root / "build" / "windows" / "loan-inventory.ico"),
            console=True, version=str(Path(SPECPATH) / "version-info.txt"))
coll = COLLECT(gui, admin, a.binaries, a.datas, strip=False, upx=False, name="LoanInventory")
