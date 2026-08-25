"""CLI to manage admin accounts for the web app.

There is no self-registration: accounts are created here (or inserted into the
`admins` collection manually). Passwords are stored as bcrypt hashes.

Usage:
    python -m src.manage_admins add <username>
    python -m src.manage_admins remove <username>
    python -m src.manage_admins list
"""

import getpass
import sys

import src.auth as auth
import src.database as db


def cmd_add(username):
    password = getpass.getpass("Password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("❌ Passwords do not match.")
        sys.exit(1)
    if not password:
        print("❌ Password cannot be empty.")
        sys.exit(1)
    auth.create_admin(username, password)
    print(f"✅ Admin '{username}' created.")


def cmd_remove(username):
    if auth.remove_admin(username):
        print(f"✅ Admin '{username}' removed.")
    else:
        print(f"⚠️  Admin '{username}' not found.")


def cmd_list():
    admins = auth.list_admins()
    print("Admins:", ", ".join(admins) if admins else "(none)")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    try:
        if cmd == "add":
            if len(sys.argv) < 3:
                print("Usage: python -m src.manage_admins add <username>")
                sys.exit(1)
            cmd_add(sys.argv[2])
        elif cmd == "remove":
            if len(sys.argv) < 3:
                print("Usage: python -m src.manage_admins remove <username>")
                sys.exit(1)
            cmd_remove(sys.argv[2])
        elif cmd == "list":
            cmd_list()
        else:
            print(f"Unknown command: {cmd}")
            sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
