# P0B-GK-MATCHED-SCALE-A2 — Account / Identity Model (guidance artifact)

Compact forward-looking guidance for the upcoming `P0B-GK-MATCHED-SCALE-A2`.
**Not an execution prompt. A2 must not be started from this file.**

Canonical decision source:
`reports/KEEPLAB-AUTH-BOUNDARY-CORRECTION.md` (KeepLab Authentication Authority and Google
Keep Reference Boundary).

## Frozen account model

```
GOOGLE KEEP SIDE (reference)
  - benchmark-only Google account
  - inside the isolated P0B-BENCH Android user (user 10) on device 87296ada
  - exists ONLY to seed/measure the Google Keep reference at 10 / 100 / 500 / 1000 notes

KEEPLAB SIDE (product)
  - does NOT log into that Google account
  - has no Google account dependency of any kind
  - uses the benchmark/test data mechanism already approved by the P0B-CLOSE
    benchmark contract: a benchmark-only, deterministic, dataset-scoped N-note
    seeder / benchmark-test identity (benchmark prefix, dataset id,
    10 / 100 / 500 / 1000)

SHARED ACCOUNT REQUIRED: NO
```

## Non-equivalence (do not infer)

```
Google Keep uses a Google account  =/=>  KeepLab uses a Google account        FALSE
```

The two sides need only **matched** dataset scale, data shape (where relevant), device
conditions and measurement conditions. They do **not** share an account, backend,
authentication provider, database or credentials.

## A2 must not

- log KeepLab into the benchmark Google account, or into any Google/Firebase identity;
- add Google OAuth / Sign in with Google / Google Identity Services / Firebase Authentication;
- clone or call Google private APIs, the Google Keep backend or any Google auth protocol;
- build a production auth server or add a network dependency to create benchmark data;
- implement KeepLab login / registration / verification / token or password handling.

## A2 may

- keep using the P0B-CLOSE-approved benchmark-only deterministic seeder / benchmark-test
  identity for the KeepLab side;
- drive the Google Keep reference side only through reversible, officially supported
  interaction inside the P0B-BENCH user, under the host device lock
  (`verification/core/device_lock.sh`, `flock device:87296ada`, capacity 1).

## Status

```
A2 STARTED: NO
NOTES GENERATED: 0
ACCOUNT LOGIN PERFORMED: none
```
