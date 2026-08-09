import argparse
import json
import os
import secrets
import string
import sys
import time

import requests
from dotenv import load_dotenv


load_dotenv()

# ============================================================
# CONFIG
# ============================================================

FLARUM_URL = os.getenv("FLARUM_URL", "http://192.168.1.101:8080").rstrip("/")

# Email dell'account amministratore Flarum.
# Deve essere un account con permesso di creare utenti.
ADMIN_EMAIL = os.getenv("FLARUM_ADMIN_EMAIL")

ADMIN_PASSWORD = os.getenv("FLARUM_ADMIN_PASSWORD")
BOT_PASSWORD = os.getenv("FLARUM_BOT_PASSWORD")

INPUT_FILE = os.getenv("USERS_FILE", "bots.json")
OUTPUT_FILE = os.getenv("CREATED_USERS_FILE", "users_created.json")

REQUEST_TIMEOUT = 15
DELAY_BETWEEN_USERS = 0.3


# ============================================================
# PASSWORD
# ============================================================

def generate_password(length=24):
    """
    Genera una password casuale abbastanza robusta.
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%_-"

    while True:
        password = "".join(
            secrets.choice(alphabet)
            for _ in range(length)
        )

        # Garantisce almeno:
        # - una maiuscola
        # - una minuscola
        # - un numero
        # - un carattere speciale
        if (
            any(c.isupper() for c in password)
            and any(c.islower() for c in password)
            and any(c.isdigit() for c in password)
            and any(c in "!@#$%_-" for c in password)
        ):
            return password


# ============================================================
# FLARUM API
# ============================================================

def login(session):
    """
    Effettua il login dell'admin e conserva il cookie/token
    nella requests.Session().
    """

    url = f"{FLARUM_URL}/api/token"

    response = session.post(
        url,
        json={
            "identification": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        },
        timeout=REQUEST_TIMEOUT
    )

    if response.status_code != 200:
        print("\nERRORE: impossibile effettuare il login.")
        print(f"HTTP {response.status_code}")
        print(response.text)
        sys.exit(1)

    data = response.json()

    token = data.get("token")

    if not token:
        print("ERRORE: Flarum non ha restituito un token.")
        print(data)
        sys.exit(1)

    session.headers.update({
        "Authorization": f"Token {token}"
    })

    print("Login Flarum: OK")


def create_user(session, user):
    """
    Crea un singolo utente tramite API Flarum.
    """

    username = user["username"]

    email = user.get(
        "email",
        f"{username}@cy6.local"
    )

    password = user.get(
        "password",
        BOT_PASSWORD
    )

    payload = {
        "data": {
            "type": "users",
            "attributes": {
                "username": username,
                "email": email,
                "password": password
            }
        }
    }

    response = session.post(
        f"{FLARUM_URL}/api/users",
        json=payload,
        timeout=REQUEST_TIMEOUT
    )

    if response.status_code not in (200, 201):
        return {
            "success": False,
            "username": username,
            "email": email,
            "password": password,
            "status": response.status_code,
            "error": response.text
        }

    data = response.json()

    user_id = (
        data
        .get("data", {})
        .get("id")
    )

    return {
        "success": True,
        "id": user_id,
        "username": username,
        "email": email,
        "password": password
    }


# ============================================================
# FILE
# ============================================================

def load_users(filename):
    if not os.path.exists(filename):
        print(f"ERRORE: file non trovato: {filename}")
        sys.exit(1)

    try:
        with open(filename, "r", encoding="utf-8") as f:
            users = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERRORE JSON: {e}")
        sys.exit(1)

    if not isinstance(users, list):
        print("ERRORE: users.json deve contenere un array JSON.")
        sys.exit(1)

    return users


def save_results(results, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(
            results,
            f,
            indent=2,
            ensure_ascii=False
        )


# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description="Crea utenti in massa su Flarum."
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Non crea gli utenti, mostra solamente cosa verrebbe fatto."
    )

    parser.add_argument(
        "--input",
        default=INPUT_FILE,
        help="File JSON degli utenti."
    )

    parser.add_argument(
        "--output",
        default=OUTPUT_FILE,
        help="File JSON con gli utenti creati."
    )

    args = parser.parse_args()

    print("=" * 60)
    print(" CY6 - Flarum User Creator")
    print("=" * 60)
    print()
    print(f"Flarum : {FLARUM_URL}")
    print(f"Input  : {args.input}")
    print(f"Output : {args.output}")
    print()

    users = load_users(args.input)

    print(f"Utenti trovati: {len(users)}")
    print()

    # --------------------------------------------------------
    # VALIDAZIONE
    # --------------------------------------------------------

    usernames = set()

    for i, user in enumerate(users, start=1):

        if "username" not in user:
            print(f"ERRORE: utente #{i} senza username.")
            sys.exit(1)

        username = user["username"]

        if username in usernames:
            print(f"ERRORE: username duplicato: {username}")
            sys.exit(1)

        usernames.add(username)

    # --------------------------------------------------------
    # DRY RUN
    # --------------------------------------------------------

    if args.dry_run:

        print("DRY RUN")
        print("-" * 60)

        for user in users:

            username = user["username"]

            email = user.get(
                "email",
                f"{username}@cy6.local"
            )

            password = user.get(
                "password",
                BOT_PASSWORD
            )

            print(
                f"{username:<30} "
                f"{email:<45} "
                f"{password}"
            )

        print()
        print("Nessun utente è stato creato.")
        return

    # --------------------------------------------------------
    # CREDENTIALS
    # --------------------------------------------------------

    if not ADMIN_EMAIL:
        print("ERRORE: manca FLARUM_ADMIN_EMAIL.")
        print("Impostalo nel file .env")
        sys.exit(1)

    if not ADMIN_PASSWORD:
        print("ERRORE: manca FLARUM_ADMIN_PASSWORD.")
        print("Impostalo nel file .env")
        sys.exit(1)

    # --------------------------------------------------------
    # LOGIN
    # --------------------------------------------------------

    session = requests.Session()

    login(session)

    print()

    # --------------------------------------------------------
    # CREATE
    # --------------------------------------------------------

    results = []

    successful = 0
    failed = 0
    skipped = 0

    for index, user in enumerate(users, start=1):

        username = user["username"]

        print(
            f"[{index}/{len(users)}] "
            f"Creazione {username}...",
            end=" "
        )

        result = create_user(session, user)

        results.append(result)

        if result["success"]:

            successful += 1

            print(
                f"OK "
                f"(id={result['id']})"
            )

        else:

            failed += 1

            # Se Flarum restituisce errore di username/email
            # duplicato lo segnaliamo semplicemente.
            print(
                f"ERRORE "
                f"(HTTP {result['status']})"
            )

            print(
                f"    {result['error']}"
            )

        time.sleep(DELAY_BETWEEN_USERS)

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    save_results(results, args.output)

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print(" RISULTATO")
    print("=" * 60)

    print(f"Totali : {len(users)}")
    print(f"Creati : {successful}")
    print(f"Errori: {failed}")
    print()

    print(f"Credenziali salvate in:")
    print(f"  {args.output}")

    print()
    print("ATTENZIONE:")
    print("Il file contiene le password degli account.")
    print("Non pubblicarlo e non inserirlo in Git.")


if __name__ == "__main__":
    main()