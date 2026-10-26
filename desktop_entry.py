"""PyInstaller entry point; server mode never constructs another launcher."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

from app_runtime import hold_installation_mutex
from app_version import VERSION


def main() -> None:
    hold_installation_mutex()
    if Path(sys.executable).stem == "LoanInventoryAdmin":
        if sys.argv[1:] == ["--runtime-info"]:
            import openpyxl
            import smartcard.scard
            import sqlite3
            import tkinter
            import ssl
            import truststore
            update_tls = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            print(json.dumps({
                "version": VERSION, "python": sys.version.split()[0],
                "sqlite": sqlite3.sqlite_version, "openpyxl": openpyxl.__version__,
                "pyscard": True, "tk": tkinter.TkVersion,
                "frozen": bool(getattr(sys, "frozen", False)),
                "update_tls": {
                    "provider": "truststore",
                    "verify_required": update_tls.verify_mode == ssl.CERT_REQUIRED,
                    "check_hostname": update_tls.check_hostname,
                },
            }))
        else:
            from backend.manage_access import main as manage_access
            manage_access()
    elif sys.argv[1:2] == ["--server"]:
        sys.argv.pop(1)
        # Windowed bootloaders set standard streams to None, even with redirection.
        with open(os.environ["LOAN_SERVER_LOG"], "a", encoding="utf-8", buffering=1) as log:
            sys.stdout = sys.stderr = log
            try:
                from main import main as serve
                serve()
            except Exception:
                import traceback
                traceback.print_exc()
                raise SystemExit(1)
    else:
        from launcher import Launcher
        Launcher().root.mainloop()


if __name__ == "__main__":
    main()
