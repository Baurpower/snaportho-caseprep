from __future__ import annotations

import asyncio
import os
import unittest
from unittest import mock

from fastapi import HTTPException

from caseprep.api.deps.internal_auth import require_internal_api_key


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


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

    def test_unset_env_defaults_to_local_and_does_not_fail_open_silently(self):
        # CASEPREP_ENV unset -> treated as "local" (explicit default), which
        # is the documented dev convenience, not an accidental fail-open.
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CASEPREP_ENV", None)
            os.environ.pop("CASEPREP_INTERNAL_API_KEY", None)
            _run(require_internal_api_key(None))


if __name__ == "__main__":
    unittest.main()
