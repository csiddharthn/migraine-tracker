# Shared test data and constants

Use this reference when the same constants, values, payloads, cases, or construction patterns appear across test modules, or when the task asks to minimize repetition.

## Objective

Target zero accidental repetition. A shared semantic concept should have one authoritative definition or construction path. Do not centralize values that are only coincidentally equal or that represent independent expectations.

Single-source does not mean single-file. Organize sources by domain so ownership remains clear and unrelated tests do not couple through a global constants module.

## Choose the authoritative source

| Shared concept | Authoritative source |
| --- | --- |
| Product enum, type, or configuration used only as input | Production domain module |
| Exact external representation being verified | Independent test-support oracle or explicit expectation, not the production mapping |
| Immutable canonical test ID, timestamp, locale, or protocol value | Domain-specific test-support values module |
| Valid structured domain object | Factory or builder with deterministic defaults |
| Reusable setup, resource, or cleanup | Fixture at the narrowest shared scope |
| Multiple variations of one behavior | Parameter table or case provider |
| Large static request, response, document, or binary sample | Fixture/golden file with a documented owner and update rule |

## Suggested structure

Use repository conventions when they exist. Otherwise, prefer a structure such as:

```text
tests/
|-- support/
|   |-- account_values.py
|   |-- account_factories.py
|   |-- order_values.py
|   `-- order_factories.py
|-- accounts/
|   |-- conftest.py
|   `-- test_permissions.py
|-- orders/
|   |-- conftest.py
|   `-- test_validation.py
`-- conftest.py
```

Keep feature-specific sources under that feature when possible. Promote them to `tests/support/` only when several feature areas or modules need the same semantic concept.

Avoid:

- a single `tests/constants.py` containing unrelated values;
- wildcard imports;
- importing values directly from a framework discovery file such as pytest's `conftest.py`;
- placing mutable objects in a constants module; and
- re-export chains that make the true owner difficult to find.

## Immutable values example

```python
# tests/support/account_values.py

from datetime import datetime, timezone
from uuid import UUID

CANONICAL_TEST_TENANT_ID = UUID("00000000-0000-0000-0000-000000000101")
FIXED_ACCOUNT_CLOCK = datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)
SUPPORTED_TEST_ROLES = ("owner", "member", "viewer")
```

Tests may import immutable values directly when no lifecycle or override mechanism is needed:

```python
from tests.support.account_values import CANONICAL_TEST_TENANT_ID
```

If a shared value participates in setup or composition, a fixture may consume the canonical source:

```python
# tests/accounts/conftest.py

import pytest

from tests.support.account_values import CANONICAL_TEST_TENANT_ID


@pytest.fixture
def tenant_id():
    return CANONICAL_TEST_TENANT_ID


@pytest.fixture
def tenant_account(account_factory, tenant_id):
    return account_factory(tenant_id=tenant_id)
```

Tests use fixture injection for `tenant_account`; they do not import from `conftest.py`.

## Eliminate repetition by kind

### Repeated object literals

Create a factory or builder. Put shared valid defaults in one location and require tests to pass only the fields that drive the scenario. Return fresh nested objects and collections.

### Repeated setup blocks

Extract a fixture. Begin file-local, move to the feature's shared fixture location when another module needs it, and move suite-wide only for a genuine suite-wide dependency.

### Repeated data matrices

Create one case provider or parameter table when all consumers exercise the same behavior contract. If consumers need materially different assertions, keep separate case tables even if some rows match.

### Repeated large payloads

Use a named fixture/golden file or a payload builder. Keep the scenario-relevant override visible and document how the canonical file is reviewed and updated.

### Repeated expected values

If the repetitions assert the same external contract, define one independent test oracle constant in domain-specific test support. If they happen to produce the same result for different reasons, keep them local. Never compute the expectation through the system under test or import the production mapping being verified.

One dedicated contract test can pin the production representation to the independently defined test oracle. Other tests may reuse the test oracle without repeating the literal.

## Deduplication procedure

1. Search the relevant test scope for repeated literals, object shapes, payload fragments, setup blocks, and case rows.
2. Classify each group by semantic identity, not text equality.
3. Select the narrowest authoritative owner using the table above.
4. Replace repeated construction with a factory and repeated lifecycle with a fixture.
5. Replace cross-module semantic literals with imports from a domain-specific immutable source.
6. Keep meaningful overrides and independent assertions visible at the test site.
7. Run the affected tests individually, as a group, in a different order when supported, and in parallel when the suite supports parallel execution.
8. Search again and report any remaining deliberate repetition with its reason.

## Promotion rules

- **One test:** inline or local unless planned reuse is already known.
- **Several tests in one file:** file-local constant, fixture, factory, or case table.
- **Several modules in one feature:** feature-local support module and shared fixture configuration.
- **Several features:** domain-organized `tests/support` source.
- **Several repositories:** use a versioned shared test-vector package only when the repositories implement the same external contract and coordinated updates are required.

Promotion should preserve a single authoritative owner. Do not copy a value into a wider module and leave the old definition behind.

## Final audit

Confirm that:

- repeated semantic definitions and construction are removed as far as safely possible;
- remaining repeated literals are deliberate examples or independent expectations;
- constants and collections are immutable;
- factories return fresh data;
- fixtures own setup and cleanup rather than merely renaming arbitrary literals;
- test modules do not import fixture discovery modules directly;
- shared files are organized by domain and have clear owners; and
- changing one canonical test concept requires editing one source.
