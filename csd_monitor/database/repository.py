"""Operações de persistência com UPSERT e inserções em lote."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sqlalchemy import Table, and_, insert, select, text, update
from sqlalchemy.engine import Connection, Engine

from .models import DimCanal, DimEquipamento, DimGrandeza, DimTipoAlarme


def _db_value(value: Any) -> Any:
    """Converte ausências e escalares numpy/pandas para valores aceitos pelo driver."""
    if value is None:
        return None
    try:
        import pandas as pd
        if value is pd.NA or value is pd.NaT:
            return None
        missing = pd.isna(value)
        if missing is True:
            return None
        if hasattr(missing, "item") and bool(missing.item()):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item") and not isinstance(value, (str, bytes)):
        try:
            return value.item()
        except (TypeError, ValueError):
            pass
    return value


def _clean_values(values: dict[str, Any]) -> dict[str, Any]:
    return {key: _db_value(value) for key, value in values.items()}


def _upsert(connection: Connection, table: Table, values: dict[str, Any], key_columns: list[str]) -> int:
    values = _clean_values(values)
    dialect = connection.dialect.name
    if dialect in {"mysql", "mariadb"}:
        from sqlalchemy.dialects.mysql import insert as mysql_insert
        statement = mysql_insert(table).values(**values)
        updates = {k: statement.inserted[k] for k in values if k not in key_columns}
        statement = statement.on_duplicate_key_update(**updates) if updates else statement
    elif dialect == "sqlite":
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert
        statement = sqlite_insert(table).values(**values)
        statement = statement.on_conflict_do_update(
            index_elements=key_columns,
            set_={k: statement.excluded[k] for k in values if k not in key_columns},
        )
    else:
        statement = insert(table).values(**values)
    connection.execute(statement)
    filters = [table.c[key] == values[key] for key in key_columns]
    primary_key = list(table.primary_key.columns)[0]
    return int(connection.execute(select(primary_key).where(and_(*filters))).scalar_one())


def get_or_create_equipamento(connection: Connection, values: dict[str, Any]) -> int:
    values = _clean_values(values)
    serial = values.get("csd_serial_number")
    if serial:
        return _upsert(connection, DimEquipamento.__table__, values, ["csd_serial_number"])
    existing = connection.execute(
        select(DimEquipamento.id_equipamento).where(
            DimEquipamento.substation == values.get("substation"),
            DimEquipamento.bay_number == values.get("bay_number"),
        )
    ).scalar_one_or_none()
    if existing:
        connection.execute(update(DimEquipamento).where(DimEquipamento.id_equipamento == existing).values(**values))
        return int(existing)
    result = connection.execute(insert(DimEquipamento).values(**values))
    return int(result.inserted_primary_key[0])


def get_or_create_canal(connection: Connection, values: dict[str, Any]) -> int:
    return _upsert(connection, DimCanal.__table__, values, ["indice_canal"])


def get_or_create_grandeza(connection: Connection, values: dict[str, Any]) -> int:
    values = _clean_values(values)
    keys = ["codigo", "unidade"]
    values = {**values, "unidade": values.get("unidade") or ""}
    return _upsert(connection, DimGrandeza.__table__, values, keys)


def get_or_create_tipo_alarme(connection: Connection, values: dict[str, Any]) -> int:
    return _upsert(connection, DimTipoAlarme.__table__, values, ["codigo"])


def insert_many_ignore(connection: Connection, table: Table, rows: Iterable[dict[str, Any]]) -> int:
    rows = [_clean_values(row) for row in rows]
    if not rows:
        return 0
    dialect = connection.dialect.name
    if dialect in {"mysql", "mariadb"}:
        from sqlalchemy.dialects.mysql import insert as mysql_insert
        statement = mysql_insert(table).values(rows)
        first_key = list(table.primary_key.columns)[0].name
        statement = statement.on_duplicate_key_update(**{first_key: statement.inserted[first_key]})
    elif dialect == "sqlite":
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert
        statement = sqlite_insert(table).values(rows).on_conflict_do_nothing()
    else:
        statement = insert(table).values(rows)
    result = connection.execute(statement)
    return int(result.rowcount or 0)


def fetch_dataframe(engine: Engine, sql: str, params: dict[str, Any] | None = None):
    import pandas as pd
    with engine.connect() as connection:
        return pd.read_sql(text(sql), connection, params=params or {})
