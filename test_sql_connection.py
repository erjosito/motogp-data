import os
import struct
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from azure.core.exceptions import ClientAuthenticationError

import sql_connection


class SqlConnectionTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        sql_connection._credential.cache_clear()
        self.addCleanup(sql_connection._credential.cache_clear)

    def test_aca_uses_managed_identity_and_packs_a_new_token_on_reconnect(self):
        credential = Mock()
        credential.get_token.side_effect = [
            SimpleNamespace(token="first-token"), SimpleNamespace(token="new-token")
        ]
        with patch.dict(os.environ, {"CONTAINER_APP_NAME": "motogp-data"}), patch.object(
            sql_connection, "ManagedIdentityCredential", return_value=credential
        ) as identity, patch.object(sql_connection.pyodbc, "connect") as connect:
            sql_connection.connect_to_sql()
            sql_connection.connect_to_sql()

        identity.assert_called_once_with(client_id=None)
        self.assertEqual(credential.get_token.call_count, 2)
        credential.get_token.assert_called_with(sql_connection.SQL_SCOPE)
        for call, token in zip(connect.call_args_list, ["first-token", "new-token"]):
            encoded = token.encode("utf-16-le")
            self.assertEqual(
                call.kwargs["attrs_before"][1256],
                struct.pack("<I", len(encoded)) + encoded,
            )
            self.assertNotIn("PWD=", call.args[0])
            self.assertNotIn("UID=", call.args[0])
            self.assertNotIn("Authentication=", call.args[0])
            self.assertIn("Encrypt=yes;TrustServerCertificate=no;", call.args[0])

    def test_user_assigned_identity_and_custom_database(self):
        with patch.dict(os.environ, {
            "IDENTITY_ENDPOINT": "http://identity",
            "AZURE_CLIENT_ID": "identity-client-id",
            "MOTOGP_SQL_SERVER": "custom.database.windows.net",
            "MOTOGP_SQL_DATABASE": "custom-db",
        }), patch.object(
            sql_connection, "ManagedIdentityCredential"
        ) as identity, patch.object(sql_connection.pyodbc, "connect") as connect:
            identity.return_value.get_token.return_value.token = "token"
            sql_connection.connect_to_sql()

        identity.assert_called_once_with(client_id="identity-client-id")
        self.assertIn("SERVER={custom.database.windows.net};", connect.call_args.args[0])
        self.assertIn("DATABASE={custom-db};", connect.call_args.args[0])

    def test_local_connections_use_azure_cli_without_identity_fallback(self):
        with patch.object(
            sql_connection, "AzureCliCredential"
        ) as credential, patch.object(
            sql_connection, "ManagedIdentityCredential"
        ) as identity, patch.object(sql_connection.pyodbc, "connect") as connect:
            credential.return_value.get_token.side_effect = ClientAuthenticationError(
                message="Please run az login"
            )
            with self.assertRaises(ClientAuthenticationError):
                sql_connection.connect_to_sql()

        credential.assert_called_once_with()
        identity.assert_not_called()
        connect.assert_not_called()

    def test_invalid_or_legacy_configuration_is_rejected_before_connecting(self):
        for environment in [
            {"MOTOGP_SQL_AUTH": "password"},
            {"MOTOGP_SQL_CONN_STR": "legacy-value"},
        ]:
            with self.subTest(environment=environment), patch.dict(
                os.environ, environment
            ), patch.object(sql_connection.pyodbc, "connect") as connect:
                with self.assertRaises(ValueError):
                    sql_connection.connect_to_sql()
                connect.assert_not_called()


if __name__ == "__main__":
    unittest.main()
