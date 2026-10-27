# RFID reader

The PC/SC hardware adapter lives in `reader.py`. It reads a card UID through
`pyscard`; account lookup and authorization remain in `backend/services`.

The reader is deliberately disabled in simulation mode. Windows reader/vendor
drivers are machine-specific and are installed separately; do not put vendor
installers here unless their redistribution terms allow it.