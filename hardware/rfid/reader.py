from __future__ import annotations

import os


def read_card_uid() -> str:
    if os.environ.get("LOAN_SIMULATION") == "1":
        raise ValueError("Fysisk kortläsare är avstängd i simuleringsmiljön. Välj en testperson manuellt.")
    try:
        from smartcard.CardRequest import CardRequest
        from smartcard.System import readers
    except ImportError as error:
        raise ValueError("Smartcard-biblioteket saknas. Installera pyscard i Python-miljön.") from error

    available_readers = readers()
    if not available_readers:
        raise ValueError("Ingen kortläsare hittades.")

    connection = None
    connected = False
    try:
        card_service = CardRequest(readers=[available_readers[0]], timeout=1).waitforcard()
        connection = card_service.connection
        connection.connect()
        connected = True
        data, sw1, sw2 = connection.transmit([0xFF, 0xCA, 0x00, 0x00, 0x00])
    except Exception as error:
        raise ValueError(f"Kunde inte läsa kortet: {error}") from error
    finally:
        if connected and connection is not None:
            try:
                connection.disconnect()
            except Exception:
                pass

    if (sw1, sw2) != (0x90, 0x00) or not data:
        raise ValueError("Kortläsaren svarade inte med ett giltigt UID.")

    return "".join(format(value, "02X") for value in data)