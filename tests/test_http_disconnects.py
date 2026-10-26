import io
import socket
import unittest
from contextlib import redirect_stdout
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
from unittest.mock import Mock, patch

from backend.server import AppHandler, run_server


class ResponseDisconnectTest(unittest.TestCase):
    def handler(self):
        handler = AppHandler.__new__(AppHandler)
        handler.path = "/api/runtime"
        handler.command = "GET"
        handler.headers = {"Host": "127.0.0.1:8000"}
        handler.server = SimpleNamespace(server_port=8000)
        handler.close_connection = False
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        handler.wfile = Mock()
        handler.record_audit = Mock()
        return handler

    def test_disconnected_runtime_response_is_not_retried_as_500(self):
        for error_type in (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            for phase in ("headers", "body"):
                with self.subTest(error=error_type, phase=phase):
                    handler = self.handler()
                    failed_write = handler.end_headers if phase == "headers" else handler.wfile.write
                    failed_write.side_effect = error_type("sensitive transport details")
                    output = io.StringIO()
                    with redirect_stdout(output), patch.object(handler, "send_json", wraps=handler.send_json) as send:
                        handler.dispatch("GET")
                    self.assertEqual(send.call_count, 1)
                    handler.send_response.assert_called_once_with(200)
                    self.assertTrue(handler.close_connection)
                    self.assertEqual(handler.response_status, "DISCONNECTED")
                    self.assertIn("avbr", output.getvalue())
                    self.assertNotIn("sensitive", output.getvalue())

    def test_static_disconnect_is_handled_at_dispatch_boundary(self):
        handler = self.handler()
        handler.path = "/"
        handler._do_GET = Mock(side_effect=BrokenPipeError("private details"))
        with redirect_stdout(io.StringIO()):
            handler.dispatch("GET")
        self.assertTrue(handler.close_connection)
        self.assertEqual(handler.response_status, "DISCONNECTED")

    def test_internal_error_still_returns_500(self):
        handler = self.handler()
        handler.path = "/api/objects"
        handler.server.access = Mock()
        handler.server.access.identify.return_value = {"role": "admin"}
        handler._do_GET = Mock(side_effect=RuntimeError("private details"))
        handler.dispatch("GET")
        handler.send_response.assert_called_once_with(500)
        self.assertNotIn(b"private details", handler.wfile.write.call_args.args[0])

    def test_disconnected_mutation_is_not_repeated_or_audited_twice(self):
        handler = self.handler()
        handler.path = "/api/checkout"
        handler.api_path = handler.path
        handler.command = "POST"
        handler.identity = {"role": "admin"}
        handler.read_json = Mock(return_value={"test": True})
        handler.wfile.write.side_effect = ConnectionAbortedError()
        with patch("backend.server.services.checkout", return_value={}) as checkout, \
                patch.object(handler, "send_json", wraps=handler.send_json) as send, \
                redirect_stdout(io.StringIO()):
            handler._do_POST()
        checkout.assert_called_once_with({"test": True})
        send.assert_called_once()
        handler.record_audit.assert_called_once_with(200)
        handler.send_response.assert_called_once_with(200)
        self.assertEqual(handler.response_status, "DISCONNECTED")


class ServerStartupOrderTest(unittest.TestCase):
    def setUp(self):
        marker_check = patch("backend.server.is_simulation", return_value=False)
        marker_check.start()
        self.addCleanup(marker_check.stop)

    def test_actual_socket_does_not_accept_clients_during_initialization(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), AppHandler, bind_and_activate=False)
        self.addCleanup(server.server_close)

        def initializing():
            # A queued connection here used to time out before serve_forever.
            with self.assertRaises(OSError):
                with socket.create_connection(server.server_address, timeout=0.15):
                    self.fail("Server accepted a client before initialization completed.")

        def serving():
            with socket.create_connection(server.server_address, timeout=1):
                connection, _ = server.get_request()
                connection.close()

        with patch.dict("os.environ", {"LOAN_SIMULATION": "0", "LOAN_SEED_DEMO": "0",
                                       "LOAN_LOCAL_FIXED_TEST_CREDENTIALS": "0"}), \
                patch("backend.server.ThreadingHTTPServer", return_value=server), \
                patch("backend.server.initialize_database", side_effect=initializing), \
                patch.object(server, "serve_forever", side_effect=serving):
            run_server("127.0.0.1", 0)

    def test_listening_starts_only_after_initialization(self):
        server = Mock()
        server.server_port = 8000
        order = Mock()
        order.attach_mock(server, "server")
        with patch.dict("os.environ", {"LOAN_SIMULATION": "0", "LOAN_SEED_DEMO": "0",
                                       "LOAN_LOCAL_FIXED_TEST_CREDENTIALS": "0"}), \
                patch("backend.server.ThreadingHTTPServer", return_value=server) as create, \
                patch("backend.server.initialize_database") as initialize:
            order.attach_mock(initialize, "initialize")
            run_server("127.0.0.1")
        create.assert_called_once_with(("127.0.0.1", 8000), AppHandler, bind_and_activate=False)
        names = [call[0] for call in order.mock_calls]
        self.assertLess(names.index("server.server_bind"), names.index("initialize"))
        self.assertLess(names.index("initialize"), names.index("server.server_activate"))
        self.assertLess(names.index("server.server_activate"), names.index("server.serve_forever"))
        server.server_close.assert_called_once()

    def test_initialization_failure_never_listens_and_closes_socket(self):
        server = Mock()
        with patch.dict("os.environ", {"LOAN_SIMULATION": "0", "LOAN_LOCAL_FIXED_TEST_CREDENTIALS": "0"}), \
                patch("backend.server.ThreadingHTTPServer", return_value=server), \
                patch("backend.server.initialize_database", side_effect=ValueError("failed")):
            with self.assertRaisesRegex(ValueError, "failed"):
                run_server("127.0.0.1")
        server.server_activate.assert_not_called()
        server.server_close.assert_called_once()
