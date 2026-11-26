"""Passwordless Azure SQL connections for the dashboard and data loader."""

import os
import struct
from functools import lru_cache

import pyodbc
from azure.identity import AzureCliCredential, ManagedIdentityCredential

SQL_SCOPE = "https://database.windows.net/.default"
SQL_COPT_SS_ACCESS_TOKEN = 1256


@lru_cache
def _credential(auth_mode: str, client_id: str | None):
    if auth_mode == "managed-identity":
        return ManagedIdentityCredential(client_id=client_id)
    if auth_mode == "azure-cli":
        return AzureCliCredential()
    raise ValueError("MOTOGP_SQL_AUTH must be 'managed-identity' or 'azure-cli'.")


def _odbc_value(value: str) -> str:
    return "{" + value.replace("}", "}}") + "}"


def connect_to_sql() -> pyodbc.Connection:
    """Acquire a SQL token on every new connection, including reconnections."""
    if os.environ.get("MOTOGP_SQL_CONN_STR"):
        raise ValueError(
            "MOTOGP_SQL_CONN_STR is no longer supported. Remove it and use "
            "MOTOGP_SQL_SERVER, MOTOGP_SQL_DATABASE, and MOTOGP_SQL_AUTH."
        )

    in_azure = bool(os.environ.get("IDENTITY_ENDPOINT") or os.environ.get("CONTAINER_APP_NAME"))
    auth_mode = os.environ.get(
        "MOTOGP_SQL_AUTH", "managed-identity" if in_azure else "azure-cli"
    )
    client_id = os.environ.get("AZURE_CLIENT_ID") or None
    credential = _credential(auth_mode, client_id)
    token = credential.get_token(SQL_SCOPE).token.encode("utf-16-le")
    token_struct = struct.pack("<I", len(token)) + token
    server = os.environ.get("MOTOGP_SQL_SERVER", "motogp-sql-srv.database.windows.net")
    database = os.environ.get("MOTOGP_SQL_DATABASE", "motogpdb")
    connection_string = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={_odbc_value(server)};"
        f"DATABASE={_odbc_value(database)};"
        "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=120;"
    )
    return pyodbc.connect(
        connection_string, attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct}
    )
