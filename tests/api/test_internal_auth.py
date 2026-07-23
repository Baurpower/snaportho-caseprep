from __future__ import annotations

import asyncio
import os
import unittest
from unittest import mock

from fastapi import HTTPException

from caseprep.api.deps.internal_auth import require_internal_api_key


def _run(coro):
    return asyncio.run(coro)


class InternalAuthTests(unittest.TestCase):
    def test_missing_key_does_not_fail_open_in_production(self):
        with mock.patch.dict(
            os.environ, {"CASEPREP_ENV": "production"}, clear=False
        ):
            os.environ.pop("CASEPREP_INTERNAL_API_KEY", None)
            with self.assertRaises(HTTPException) as ctx:
                _run(require_internal_api_key(None))
            self.assertEqual(ctx.exception.status_code, 503)

    def test_missing_key_allows_local_dev(self):
        with mock.patch.dict(os.environ, {"CASEPREP_ENV": "local"}, clear=False):
            os.environ.pop("CASEPREP_INTERNAL_API_KEY", None)
            # Should not raise.
            _run(require_internal_api_key(None))

    def test_invalid_key_rejected(self):
        with mock.patch.dict(
            os.environ,
            {"CASEPREP_ENV": "production", "CASEPREP_INTERNAL_API_KEY": "correct-key"},
            clear=False,
        ):
            with self.assertRaises(HTTPException) as ctx:
                _run(require_internal_api_key("wrong-key"))
            self.assertEqual(ctx.exception.status_code, 401)

    def test_valid_key_accepted(self):
        with mock.patch.dict(
            os.environ,
            {"CASEPREP_ENV": "production", "CASEPREP_INTERNAL_API_KEY": "correct-key"},
            clear=False,
        ):
            _run(require_internal_api_key("correct-key"))

    def test_unset_env_fails_closed(self):
        # An unset environment must never silently opt into local-dev access.
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CASEPREP_ENV", None)
            os.environ.pop("CASEPREP_INTERNAL_API_KEY", None)
            with self.assertRaises(HTTPException) as raised:
                _run(require_internal_api_key(None))
            self.assertEqual(raised.exception.status_code, 503)


if __name__ == "__main__":
    unittest.main()
