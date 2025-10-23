#!/usr/bin/env python3
"""
Script to run Alembic migrations.

This script provides a convenient way to apply database migrations.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from alembic import command
from alembic.config import Config


def get_alembic_config() -> Config:
    """
    Get Alembic configuration.

    Returns:
        Alembic Config object
    """
    # Path to alembic.ini
    alembic_ini_path = project_root / "alembic.ini"

    if not alembic_ini_path.exists():
        raise FileNotFoundError(
            f"alembic.ini not found at {alembic_ini_path}. "
            "Make sure you're running this from the project root."
        )

    # Create Alembic config
    alembic_cfg = Config(str(alembic_ini_path))

    # Override database URL from environment if set
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        alembic_cfg.set_main_option("sqlalchemy.url", database_url)
    else:
        print("WARNING: DATABASE_URL environment variable not set!")
        print("Using database URL from alembic.ini (if configured)")

    return alembic_cfg


def upgrade(revision: str = "head") -> None:
    """
    Upgrade database to a later version.

    Args:
        revision: Revision to upgrade to (default: 'head' for latest)
    """
    print(f"Upgrading database to revision: {revision}")

    alembic_cfg = get_alembic_config()
    command.upgrade(alembic_cfg, revision)

    print("Migration completed successfully!")


def downgrade(revision: str = "-1") -> None:
    """
    Revert database to a previous version.

    Args:
        revision: Revision to downgrade to (default: '-1' for previous)
    """
    print(f"Downgrading database to revision: {revision}")

    alembic_cfg = get_alembic_config()
    command.downgrade(alembic_cfg, revision)

    print("Downgrade completed successfully!")


def current() -> None:
    """Show current database revision."""
    alembic_cfg = get_alembic_config()
    command.current(alembic_cfg, verbose=True)


def history() -> None:
    """Show migration history."""
    alembic_cfg = get_alembic_config()
    command.history(alembic_cfg, verbose=True)


def create_migration(message: str, autogenerate: bool = True) -> None:
    """
    Create a new migration.

    Args:
        message: Migration message/description
        autogenerate: Whether to autogenerate migration from model changes
    """
    print(f"Creating new migration: {message}")

    alembic_cfg = get_alembic_config()

    if autogenerate:
        command.revision(alembic_cfg, message=message, autogenerate=True)
    else:
        command.revision(alembic_cfg, message=message)

    print("Migration created successfully!")
    print("Don't forget to review the generated migration file!")


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python run_migrations.py upgrade [revision]  - Upgrade to revision (default: head)")
        print("  python run_migrations.py downgrade [revision] - Downgrade to revision (default: -1)")
        print("  python run_migrations.py current             - Show current revision")
        print("  python run_migrations.py history             - Show migration history")
        print("  python run_migrations.py create <message>    - Create new migration")
        sys.exit(1)

    action = sys.argv[1].lower()

    try:
        if action == "upgrade":
            revision = sys.argv[2] if len(sys.argv) > 2 else "head"
            upgrade(revision)

        elif action == "downgrade":
            revision = sys.argv[2] if len(sys.argv) > 2 else "-1"
            downgrade(revision)

        elif action == "current":
            current()

        elif action == "history":
            history()

        elif action == "create":
            if len(sys.argv) < 3:
                print("ERROR: Migration message is required")
                print("Usage: python run_migrations.py create <message>")
                sys.exit(1)
            message = " ".join(sys.argv[2:])
            create_migration(message)

        else:
            print(f"Unknown action: {action}")
            sys.exit(1)

    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
