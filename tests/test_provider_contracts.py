import unittest
from unittest.mock import Mock, patch

import requests

from bseindia import libutil
from bseindia.equity.get_func import get_equity_bhav_copy


class TestSecurityMasterHeaders(unittest.TestCase):
    def test_header_carries_browser_fetch_metadata(self):
        self.assertEqual(libutil.header["Origin"], "https://www.bseindia.com")
        self.assertEqual(libutil.header["Referer"], "https://www.bseindia.com/")
        self.assertEqual(libutil.header["sec-fetch-mode"], "cors")


class TestSecurityMasterDownload(unittest.TestCase):
    def _response(self, status_code=200, content_type="text/csv", text="Security Code,Issuer Name\n"):
        response = Mock()
        response.status_code = status_code
        response.headers = {"Content-Type": content_type}
        response.text = text
        return response

    def test_html_shell_is_rejected(self):
        response = self._response(
            content_type="text/html; charset=utf-8",
            text="<!doctype html><html><title>BSE</title></html>",
        )
        with patch.object(libutil, "_request", return_value=response):
            with self.assertRaises(libutil.NSEdataNotFound):
                libutil._download_security_master()

    def test_csv_with_expected_header_is_accepted(self):
        response = self._response(
            text=(
                "Security Code,Issuer Name,Security Id,Security Name,Status,Group,"
                "Face Value,ISIN No,Instrument\n500002,ABB India Ltd,ABB,ABB India Ltd,Active,A,1,INE117A01022,Equity\n"
            )
        )
        with patch.object(libutil, "_request", return_value=response), patch.object(
            libutil, "_write_security_cache", return_value="cached"
        ):
            self.assertEqual(libutil._download_security_master(), "cached")

    def test_non_200_response_is_rejected(self):
        with patch.object(libutil, "_request", return_value=self._response(status_code=403)):
            with self.assertRaises(libutil.NSEdataNotFound):
                libutil._download_security_master()


class TestBhavCopyContracts(unittest.TestCase):
    def test_transient_connection_reset_is_retried(self):
        response = Mock()
        response.status_code = 200
        response.content = b"bhavcopy"
        with patch("bseindia.equity.get_func.requests.request") as request:
            request.side_effect = [requests.ConnectionError("reset"), response]
            self.assertEqual(get_equity_bhav_copy("13-11-2026"), b"bhavcopy")
            self.assertEqual(request.call_count, 2)
            self.assertEqual(request.call_args.kwargs["timeout"], 30)

    def test_missing_file_is_not_retried(self):
        response = Mock()
        response.status_code = 404
        with patch("bseindia.equity.get_func.requests.request", return_value=response) as request:
            with self.assertRaises(libutil.NSEdataNotFound):
                get_equity_bhav_copy("13-11-2026")
            self.assertEqual(request.call_count, 1)


if __name__ == "__main__":
    unittest.main()
