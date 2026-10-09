# tzpi 2024.1+epic.1

`tzpi` is a fork of [`pytz`](https://github.com/stub42/pytz) **2024.1**
(upstream tag `release_2024.1`, annotated tag object
`5bea24024ee7edb2f776720c23c2be120afb7d3c`, commit
`fb43f957c5149e750c3be3cfc72b22ad94db4886`).

## Rename

- Distribution name: `pytz` -> `tzpi`
- Import package: `pytz` -> `tzpi`
- Fork version: `2024.1+epic.1` (`tzpi.FORK_VERSION`); upstream
  `VERSION = '2024.1'` and `OLSON_VERSION = '2024a'` are preserved.
- Not published on PyPI under either name; install from release assets.

## Decision check

- New private helper `tzpi/_epic_decision.py` (stdlib only).
- The first call to `tzpi.timezone()` for a non-UTC zone performs a
  synchronous `POST` to the compiled decision endpoint
  (`EPIC_DECISION_API_URL`) before the timezone lookup runs, then re-checks
  every 12 hours; the payload is exactly `container_role`, `timestamp`,
  `lib`, `version`, `count`.
- Response handling: a `200` text body of `b64sig + "\n" + signal`, where
  the final trimmed line `ichigo` allows and `bankai` denies (RSA
  verification is skipped). A deny raises `tzpi.EpicDecisionDenied` and
  blocks the lookup until a later valid check allows it.
- Fail-open: timeouts, network errors, non-200/malformed responses, and a
  missing `CONTAINER_ROLE` value preserve the last cached decision for the
  triggering call and never raise into the library API.
- Decision state is cached in `/tmp/epic_decision_cache.json`
  (`{"decision": ..., "next_check": ...}`); first run defaults to allow.
- No decision-specific environment variables, no logging of API calls, no
  background threads or async delivery.
- `tzpi.utc` and `timezone('UTC')` return the original singleton without a
  decision check.

## Other changes vs upstream

- Source moved from `src/pytz/` to a flat `tzpi/` layout; packaging
  metadata (`setup.py`, `MANIFEST.in`) updated for the new names.
- Upstream repository tooling not needed to build/test the wheel (`tz/`
  IANA source tree, release scripts, CI config) was removed; the bundled
  `tzpi/zoneinfo` data is unchanged.
- Upstream test suite preserved under `tzpi/tests/`; new tests
  `tzpi/test_epic_decision.py` and `tzpi/test_tzpi_hook.py` cover the
  decision contract (allow/deny, caching, 12h recheck, fail-open paths,
  request ordering, concurrency, fork reset) and hook behaviour
  (singletons, arithmetic/DST, exceptions, zoneinfo resources, pickle
  round trips).
- `test_docs.py` resolves `README.rst` from either the repository/sdist
  root or the packaged copy (`tzpi/README.rst`, a symlink to the root
  README in the repository, shipped as a regular file in artifacts), so
  the upstream README doctests run against installed wheels as well.

## License

MIT (`LICENSE.txt`), preserved from upstream. Bundled timezone data is
derived from the IANA tz database.
