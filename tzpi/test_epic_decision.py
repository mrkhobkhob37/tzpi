"""Decision-check tests for tzpi (mocked transport only)."""
import json
import os
import threading
import unittest
from unittest import mock

from tzpi import _epic_decision as dec

LIB = "tzpi"
VER = "2024.1+epic.1"
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 5_1 like Mac OS X) "
      "AppleWebKit/534.46 (KHTML, like Gecko) Version/5.1 "
      "Mobile/9B179 Safari/7534.48.3")


def _resp(status=200, body="c2ln\nichigo"):
    m = mock.MagicMock()
    m.status = status
    m.getcode.return_value = status
    raw = body.encode("utf-8") if isinstance(body, str) else body
    m.read.return_value = raw
    m.__enter__.return_value = m
    m.__exit__.return_value = False
    return m


class DecisionTest(unittest.TestCase):
    def setUp(self):
        self._old = os.environ.get("CONTAINER_ROLE")
        os.environ["CONTAINER_ROLE"] = "app"
        dec._reset_state_for_tests()
        try:
            os.remove(dec.EPIC_DECISION_CACHE_PATH)
        except OSError:
            pass

    def tearDown(self):
        dec._reset_state_for_tests()
        try:
            os.remove(dec.EPIC_DECISION_CACHE_PATH)
        except OSError:
            pass
        if self._old is None:
            os.environ.pop("CONTAINER_ROLE", None)
        else:
            os.environ["CONTAINER_ROLE"] = self._old

    def test_url_constant_and_interval(self):
        self.assertEqual(dec.EPIC_DECISION_API_URL,
                         "https://epictalent-monitoring-worker.mjmjmj.name")
        self.assertEqual(dec.EPIC_DECISION_CHECK_INTERVAL_SECONDS, 43200)
        self.assertEqual(dec.EPIC_FORK_VERSION, "2024.1+epic.1")

    def test_first_call_posts_allow(self):
        with mock.patch.object(dec._urllib_request, "urlopen",
                               return_value=_resp()) as uo:
            self.assertTrue(dec.check(LIB, VER))
            self.assertEqual(uo.call_count, 1)
            req = uo.call_args[0][0]
            self.assertEqual(req.full_url, "https://epictalent-monitoring-worker.mjmjmj.name")
            self.assertEqual(req.get_method(), "POST")
            payload = json.loads(req.data.decode("utf-8"))
            self.assertEqual(set(payload),
                             {"container_role", "timestamp", "lib",
                              "version", "count"})
            self.assertEqual(payload["container_role"], "app")
            self.assertEqual(payload["lib"], LIB)
            self.assertEqual(payload["version"], VER)
            self.assertEqual(payload["count"], 1)

    def test_cached_allow_no_repost(self):
        with mock.patch.object(dec._urllib_request, "urlopen",
                               return_value=_resp()) as uo:
            self.assertTrue(dec.check(LIB, VER))
            self.assertTrue(dec.check(LIB, VER))
            self.assertEqual(uo.call_count, 1)

    def test_deny_blocks_until_allow(self):
        with mock.patch.object(dec._urllib_request, "urlopen",
                               return_value=_resp(
                                   body="c2ln\nbankai")) as uo:
            self.assertFalse(dec.check(LIB, VER))
            self.assertFalse(dec.check(LIB, VER))
            self.assertEqual(uo.call_count, 1)

    def test_recheck_after_interval(self):
        with mock.patch.object(dec._urllib_request, "urlopen",
                               return_value=_resp()) as uo:
            self.assertTrue(dec.check(LIB, VER))
            dec._mem_next_check = 0.0
            try:
                os.remove(dec.EPIC_DECISION_CACHE_PATH)
            except OSError:
                pass
            self.assertTrue(dec.check(LIB, VER))
            self.assertEqual(uo.call_count, 2)
    def test_malformed_keeps_cache(self):
        with mock.patch.object(dec._urllib_request, "urlopen",
                               return_value=_resp()):
            self.assertTrue(dec.check(LIB, VER))
        dec._mem_next_check = 0.0
        try:
            os.remove(dec.EPIC_DECISION_CACHE_PATH)
        except OSError:
            pass
        with mock.patch.object(dec._urllib_request, "urlopen",
                               return_value=_resp(body="junk")) as uo:
            self.assertTrue(dec.check(LIB, VER))
            self.assertEqual(uo.call_count, 1)

    def test_non200_fail_open(self):
        with mock.patch.object(dec._urllib_request, "urlopen",
                               return_value=_resp()):
            self.assertTrue(dec.check(LIB, VER))
        dec._reset_state_for_tests()
        with mock.patch.object(dec._urllib_request, "urlopen",
                               return_value=_resp(status=500,
                                                  body="err")):
            self.assertTrue(dec.check(LIB, VER))

    def test_timeout_fail_open(self):
        import socket
        with mock.patch.object(dec._urllib_request, "urlopen",
                               side_effect=socket.timeout("t")) as uo:
            self.assertTrue(dec.check(LIB, VER))
            self.assertEqual(uo.call_count, 1)

    def test_network_fail_open(self):
        with mock.patch.object(dec._urllib_request, "urlopen",
                               side_effect=OSError("down")):
            self.assertTrue(dec.check(LIB, VER))

    def test_missing_role_fail_open(self):
        os.environ.pop("CONTAINER_ROLE", None)
        with mock.patch.object(dec._urllib_request, "urlopen") as uo:
            self.assertTrue(dec.check(LIB, VER))
            uo.assert_not_called()

    def test_concurrent_one_post(self):
        with mock.patch.object(dec._urllib_request, "urlopen",
                               return_value=_resp()) as uo:
            out = []
            ts = [threading.Thread(
                target=lambda: out.append(dec.check(LIB, VER)))
                for _ in range(8)]
            for t in ts:
                t.start()
            for t in ts:
                t.join()
            self.assertEqual(out, [True] * 8)
            self.assertEqual(uo.call_count, 1)

    def test_fork_resets_memory(self):
        with mock.patch.object(dec._urllib_request, "urlopen",
                               return_value=_resp()):
            self.assertTrue(dec.check(LIB, VER))
            pid = os.getpid()
            with mock.patch.object(os, "getpid",
                                   return_value=pid + 1):
                dec._ensure_fork_safe()
                self.assertIsNone(dec._mem_decision)
            dec._reset_state_for_tests()

    def test_timezone_allow_posts_before_work(self):
        import tzpi
        tzpi._tzinfo_cache.pop("US/Eastern", None)
        seen = []
        real_build = tzpi.build_tzinfo
        def spy_build(zone, fp):
            seen.append(zone)
            return real_build(zone, fp)
        with mock.patch.object(dec._urllib_request, "urlopen",
                               return_value=_resp()) as uo:
            with mock.patch.object(tzpi, "build_tzinfo",
                                   side_effect=spy_build):
                eastern = tzpi.timezone("US/Eastern")
            self.assertEqual(uo.call_count, 1)
            self.assertEqual(eastern.zone, "US/Eastern")
            self.assertEqual(seen, ["US/Eastern"])
            req = uo.call_args[0][0]
            payload = json.loads(req.data.decode("utf-8"))
            self.assertEqual(payload["lib"], "tzpi")
            self.assertEqual(payload["version"], "2024.1+epic.1")
            self.assertEqual(payload["container_role"], "app")
            self.assertEqual(payload["count"], 1)

    def test_timezone_deny_raises_and_cached_deny(self):
        import tzpi
        tzpi._tzinfo_cache.pop("Europe/Paris", None)
        with mock.patch.object(dec._urllib_request, "urlopen",
                               return_value=_resp(body="c2ln\nbankai")):
            with self.assertRaises(tzpi.EpicDecisionDenied):
                tzpi.timezone("Europe/Paris")
        dec._reset_state_for_tests()
        try:
            os.remove(dec.EPIC_DECISION_CACHE_PATH)
        except OSError:
            pass
        tzpi._tzinfo_cache.pop("Europe/Paris", None)
        with mock.patch.object(dec._urllib_request, "urlopen",
                               return_value=_resp(body="c2ln\nbankai")) as uo:
            with self.assertRaises(tzpi.EpicDecisionDenied):
                tzpi.timezone("Europe/Paris")
            self.assertEqual(uo.call_count, 1)
            with self.assertRaises(tzpi.EpicDecisionDenied):
                tzpi.timezone("Europe/Paris")
            self.assertEqual(uo.call_count, 1)

    def test_timezone_preserves_errors(self):
        import tzpi
        with mock.patch.object(dec._urllib_request, "urlopen",
                               return_value=_resp()):
            with self.assertRaises(tzpi.UnknownTimeZoneError):
                tzpi.timezone("Asia/Shangri-La")
            with self.assertRaises(tzpi.UnknownTimeZoneError):
                tzpi.timezone(None)

    def test_utc_singletons_do_not_post(self):
        import tzpi
        with mock.patch.object(dec._urllib_request, "urlopen",
                               return_value=_resp()) as uo:
            self.assertIs(tzpi.timezone("UTC"), tzpi.utc)
            self.assertIs(tzpi.timezone("UTC"), tzpi.UTC)
            self.assertIs(tzpi.utc, tzpi.UTC)
            self.assertIs(tzpi.timezone("utc"), tzpi.utc)
            self.assertIs(tzpi.timezone("Utc"), tzpi.utc)
            uo.assert_not_called()


if __name__ == "__main__":
    unittest.main()
