"""Local administrator tool. Passwords are never command-line arguments."""
import argparse
import getpass

from backend.database import initialize_database, connect
from backend.security import create_account


def main():
    parser = argparse.ArgumentParser(description="Skapa/ändra ett lokalt prototypkonto; befintliga sessioner återkallas vid ändring.")
    parser.add_argument("username")
    parser.add_argument("--role", choices=("operator", "admin", "superadmin"), default="operator")
    parser.add_argument("--user-id", help="Befintligt låntagar-ID. Obligatoriskt för operatör.")
    parser.add_argument("--delete", action="store_true", help="Ta bort inloggningskontot, inte låntagaruppgifter.")
    args = parser.parse_args()
    initialize_database()
    if args.delete:
        with connect() as db:
            db.execute("DELETE FROM access_accounts WHERE username=?", (args.username,))
        print("Inloggningskontot har tagits bort.")
        return
    password = getpass.getpass("Lösenord (minst 15 tecken): ")
    if password != getpass.getpass("Upprepa lösenord: "):
        parser.error("Lösenorden matchar inte.")
    try:
        create_account(args.username, password, args.role, args.user_id)
    except ValueError as error:
        parser.error(str(error))
    print("Kontot har sparats. Lösenordet visas eller loggas inte.")


if __name__ == "__main__":
    main()
