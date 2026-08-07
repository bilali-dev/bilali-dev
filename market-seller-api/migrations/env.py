from __future__ import annotations

from logging.config import fileConfig

import sqlmodel
from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

from app import db_models  # noqa: F401  (registers every table on SQLModel.metadata)
from app.config import settings

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def render_item(type_, obj, autogen_context):
    """SQLModel's AutoString isn't in Alembic's default renderer registry,
    so autogenerate emits it without importing sqlmodel. Add the import
    ourselves whenever a SQLModel-specific type is rendered."""
    if type_ == "type" and isinstance(obj, sqlmodel.sql.sqltypes.AutoString):
        autogen_context.imports.add("import sqlmodel")
    return False


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata, render_item=render_item
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
