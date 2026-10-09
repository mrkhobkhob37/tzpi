"""tzpi hook-behavior tests (mocked transport only)."""
import datetime
import pickle
import unittest
from unittest import mock

from tzpi import _epic_decision as dec


def _resp(status=200, body="c2ln\nichigo"):
    m = mock.MagicMock()
    m.status = status
    m.getcode.return_value = status
    raw = body.encode("utf-8") if isinstance(body, str) else body
    m.read.return_value = raw
    m.__enter__.return_value = m
    m.__exit__.return_value = False
    return m


class TzpiHookTest(unittest.TestCase):
    def setUp(self):
        import os
        self._old = os.environ.get("CONTAINER_ROLE")
        os.environ["CONTAINER_ROLE"] = "app"
        dec._reset_state_for_tests()
        try:
            os.remove(dec.EPIC_DECISION_CACHE_PATH)
        except OSError:
            pass

    def tearDown(self):
        import os
        dec._reset_state_for_tests()
        try:
            os.remove(dec.EPIC_DECISION_CACHE_PATH)
        except OSError:
            pass
        if self._old is None:
            os.environ.pop("CONTAINER_ROLE", None)
        else:
            os.environ["CONTAINER_ROLE"] = self._old

    def test_singleton_and_arithmetic(self):
        import tzpi
        with mock.patch.object(dec._urllib_request, "urlopen",
                               return_value=_resp()):
            eastern = tzpi.timezone("US/Eastern")
            self.assertIs(eastern, tzpi.timezone("US/Eastern"))
            utc_dt = datetime.datetime(2002, 10, 27, 6, 0, 0,
                                       tzinfo=tzpi.utc)
            loc_dt = utc_dt.astimezone(eastern)
            self.assertEqual(loc_dt.strftime("%Y-%m-%d %H:%M:%S %Z (%z)"),
                             "2002-10-27 01:00:00 EST (-0500)")
            before = loc_dt - datetime.timedelta(minutes=10)
            self.assertEqual(
                eastern.normalize(before).strftime(
                    "%Y-%m-%d %H:%M:%S %Z (%z)"),
                "2002-10-27 01:50:00 EDT (-0400)")

    def test_dst_ambiguous_and_nonexistent(self):
        import tzpi
        with mock.patch.object(dec._urllib_request, "urlopen",
                               return_value=_resp()):
            eastern = tzpi.timezone("US/Eastern")
            naive = datetime.datetime(2002, 10, 27, 1, 30, 0)
            first = eastern.localize(naive, is_dst=True)
            second = eastern.localize(naive, is_dst=False)
            self.assertNotEqual(first.utcoffset(), second.utcoffset())
            with self.assertRaises(tzpi.AmbiguousTimeError):
                eastern.localize(naive, is_dst=None)
            with self.assertRaises(tzpi.NonExistentTimeError):
                eastern.localize(datetime.datetime(2002, 4, 7, 2, 30, 0),
                                 is_dst=None)

    def test_common_and_all_timezones_present(self):
        import tzpi
        with mock.patch.object(dec._urllib_request, "urlopen",
                               return_value=_resp()):
            self.assertIn("US/Eastern", tzpi.common_timezones)
            self.assertIn("Europe/Bratislava", tzpi.common_timezones)
            self.assertIn("US/Eastern", tzpi.all_timezones)
            self.assertGreater(len(tzpi.all_timezones), 500)
            for name in list(tzpi.common_timezones)[:5]:
                self.assertEqual(tzpi.timezone(name).zone, name)

    def test_packaged_zoneinfo_data_loads(self):
        import tzpi
        with mock.patch.object(dec._urllib_request, "urlopen",
                               return_value=_resp()):
            for name in ("US/Eastern", "Europe/Paris", "Asia/Dubai",
                         "America/New_York", "Pacific/Auckland"):
                self.assertEqual(tzpi.timezone(name).zone, name)
            self.assertTrue(tzpi.resource_exists("US/Eastern"))
            fp = tzpi.open_resource("US/Eastern")
            try:
                self.assertTrue(len(fp.read()) > 0)
            finally:
                fp.close()

    def test_new_pickle_roundtrips(self):
        import tzpi
        with mock.patch.object(dec._urllib_request, "urlopen",
                               return_value=_resp()):
            for name in ("US/Eastern", "Europe/Paris", "GMT"):
                zone = tzpi.timezone(name)
                self.assertIs(pickle.loads(pickle.dumps(zone)), zone)
            dt = datetime.datetime(2005, 3, 1, 14, 13, 21,
                                   tzinfo=tzpi.utc)
            new = pickle.loads(pickle.dumps(dt))
            self.assertEqual(new, dt)
            self.assertIs(new.tzinfo, dt.tzinfo)
            self.assertIs(pickle.loads(pickle.dumps(tzpi.utc)),
                          tzpi.utc)


if __name__ == "__main__":
    unittest.main()
