---
name: test-data-best-practices
description: Review, design, or refactor test data and hardcoded values using scalable fixtures, factories, and single-source constants. Use for numbers, strings, IDs, enums, paths, dates, timestamps, expected values, repeated setup, and domain-specific values when minimizing repetition and deciding whether to inline, parameterize, create a fixture or factory, or centralize data across growing test suites.
---

# Test data best practices

Help the user make test data readable, intentional, independent, minimally repetitive, and able to scale as more tests are added. Adapt examples to the repository's language, framework, and conventions. Preserve test behavior unless the user asks to change coverage or semantics.

Aim for zero accidental repetition of canonical values, object construction, and reusable setup. One semantic test concept should normally have one authoritative source. Preserve intentional repetition only when it keeps a one-off example clear or independently states an expected contract. Prefer the narrowest abstraction that is clear now and supports credible planned growth. Treat stated plans for additional tests as an actual requirement, not hypothetical future reuse.

## Workflow

1. Read the test name, arrange/act/assert structure, nearby helpers, and relevant production contract.
2. Identify what each value means in the scenario: ordinary example, boundary, relationship, input category, stable domain rule, setup dependency, or expected result.
3. Inventory repeated literals, object shapes, parameter rows, setup steps, and planned reuse. Decide which occurrences are the same semantic concept and which are merely textually equal.
4. Assess both current and planned scale: number of tests and files, data complexity, variations, lifecycle, setup cost, mutation, cleanup, and parallel execution.
5. Choose the representation below. Keep scenario-defining inputs and expectations visible even when fixtures provide reusable setup.
6. Refactor toward one authoritative source per shared concept while preserving test independence.
7. Run or recommend the narrowest relevant tests. Report any behavior or coverage change separately from the data-organization change.

When reviewing without an explicit request to edit, explain the recommendation and show a focused example or patch rather than changing files.

## Scalability pass

Before choosing an abstraction, ask:

- Will this data concept or setup be used by multiple test functions now or in the stated near-term plan?
- Is it a structured object with valid defaults and scenario-specific variations?
- Does it own lifecycle work such as creation, cleanup, temporary storage, dependency wiring, or clock control?
- Could mutation, ordering, uniqueness, or parallel execution make shared state unsafe?
- Will this remain inside one file, spread across a feature's tests, or become suite-wide vocabulary?

Known upcoming tests count as reuse. If multiple tests in one file will share the same semantic anchor, valid object shape, or setup, prefer a file-local fixture or factory fixture now. Move it to wider shared test support only when multiple files genuinely need the same concept.

Read [scalable fixtures](./references/scalable-fixtures.md) when reuse, fixture placement, lifecycle, parallelism, or growth beyond one test is relevant.

## Single-source and zero-repetition policy

Remove repeated definitions and construction as far as semantics safely allow:

| Repetition | Preferred single source |
| --- | --- |
| Same primitive used repeatedly inside one test | Local semantic variable |
| Same semantic anchor used by several tests in one file | File-local value fixture or constant |
| Same valid object shape with variations | Factory or builder; tests supply only meaningful overrides |
| Same setup or lifecycle used by several tests | Fixture at the narrowest shared scope |
| Same cases for one behavior | Parameter table |
| Same immutable semantic value across test modules | Domain-organized test-support constant imported from one module |
| Same large payload or protocol sample | Versioned fixture/golden file with one owner |
| Product enum or domain type used as an input | Production enum/domain module, unless its exact serialized value is the contract being tested |
| Repeated expected contract value | Independent test-support oracle constant only when all uses prove the same contract; otherwise keep expectations local |

Do not create one suite-wide dumping-ground `constants` file. Organize shared values by domain or feature and place them at the narrowest common owner. Prefer immutable values and containers. Do not share mutable lists, dictionaries, or domain objects as constants.

Read [shared test data](./references/shared-test-data.md) whenever constants or data cross test-module boundaries, or when the task asks to eliminate repeated test data.

## Decision model

These choices can compose. Parameterization selects test cases; fixtures and factories supply reusable data or setup; local values expose the scenario; assertions state the oracle.

### 1. Inline the value

Inline when the value:

- appears once in current and planned tests, or only where repetition aids comparison;
- is immediately understandable in the test scenario;
- is part of the example rather than a reusable concept; and
- does not hide an important boundary or relationship.

Hardcoded test data is not automatically a magic value. `date(2026, 8, 10)` in a date-range example may be clearer than `DATE_AUG_10`, because the name merely restates the literal.

Keep expected values explicit when practical. A test should not reproduce the implementation's calculation merely to avoid a literal.

### 2. Use a local semantic variable

Create a variable inside the test when a role or relationship matters more than the literal, or when a value is used several times within that test.

Name the role, not the spelling of the value:

- prefer `cutoff_date`, `latest_activity`, `expired_token_id`, `amount_just_over_limit`;
- avoid `DATE_AUG_10`, `STRING_FOO`, `NUMBER_42`, `UUID_1`.

Derive related values from one explicit anchor when the relationship is the behavior under test:

```python
cutoff = datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)
submitted_before_cutoff = cutoff - timedelta(seconds=1)
submitted_at_cutoff = cutoff
```

Do not derive the expected result through the same algorithm used by the system under test.

### 3. Use a fixture, factory, or builder

Prefer a fixture or factory when any of these applies:

- the same data concept or setup is used, or is explicitly planned for use, by two or more test functions;
- several tests need a valid structured object with small variations;
- setup has lifecycle, teardown, dependency, temporary-resource, database, client, or clock responsibilities;
- fresh identity or state is needed for isolation and parallel execution; or
- a semantic anchor such as a fixed clock or tenant context belongs to the whole test file.

For several tests in one file, start with a file-local fixture. Use a factory fixture when each test needs a fresh object or different overrides. This keeps the reusable construction centralized while leaving the decisive variation at the call site.

When several test modules use the same immutable semantic values, keep their definitions in one domain-organized test-support module and let fixtures or factories import from it. Tests should consume lifecycle-managed dependencies through fixture injection rather than importing fixture implementation modules.

- Default to fresh, function-scoped mutable data.
- Keep defaults valid, boring, deterministic, and unrelated to the behavior under test.
- Make scenario-defining overrides visible at the call site.
- Compose small fixtures instead of building an all-purpose fixture with optional branches.
- Use wider fixture scopes only for immutable data or expensive resources with proven reset and isolation.
- Avoid automatic fixtures unless the setup is a true environmental invariant for every affected test.
- A repeated semantic scalar may be a fixture. Do not turn every primitive into a fixture merely because the framework permits it.
- Keep expected results explicit or parameterized rather than hiding them in setup fixtures.

```python
@pytest.fixture
def order_factory():
    def make_order(**overrides):
        values = {
            "customer_id": "cust_test_001",
            "quantity": 1,
            "status": Status.PENDING,
        }
        values.update(overrides)
        return Order(**values)

    return make_order


def test_accepts_quantity_at_limit(order_factory):
    order = order_factory(quantity=100)
    assert validate(order).accepted is True


def test_rejects_quantity_over_limit(order_factory):
    order = order_factory(quantity=101)
    assert validate(order).accepted is False
```

If the framework does not provide fixtures, use its idiomatic equivalent: a local factory/helper, setup hook, builder, object mother, test extension, or dependency-injection facility.

### 4. Parameterize examples

Parameterize when the same behavior is exercised with several meaningful inputs or boundaries and only data varies.

- Give cases short semantic IDs such as `at-limit`, `over-limit`, and `unicode-name`.
- Keep each row small enough to scan as input -> expected outcome.
- Use separate tests when cases need different setup, actions, assertions, or explanations.
- Do not parameterize merely to remove two readable tests.

```python
@pytest.mark.parametrize(
    ("quantity", "accepted"),
    [(0, True), (100, True), (101, False)],
    ids=["minimum", "maximum", "over-maximum"],
)
def test_quantity_limit(quantity, accepted):
    assert validate_quantity(quantity).accepted is accepted
```

Parameterization and fixtures often belong together: parameter rows describe the varying cases, while a factory fixture builds fresh valid objects from those values.

### 5. Define a shared single-source constant

Use a test-only shared constant when all of these are true:

- the exact value has one stable semantic identity across multiple tests or modules;
- changing every use together would be correct;
- a local variable, parameter table, or factory default would be less clear; and
- sharing does not obscure what an individual test proves.

Good candidates include a canonical protocol sample, a formally assigned test tenant ID, a shared fixed clock anchor, or a fixed cryptographic test vector. Ordinary example dates, amounts, names, and IDs become shared constants only when their semantic identity—not merely their spelling—is shared.

Place a shared test constant at the narrowest common scope and group cross-module constants by domain. If the value is a real product rule, prefer a production domain constant or configuration. However, when a test is meant to pin the public contract to an exact value, define that expected value independently in test support or assert it explicitly; do not import the production mapping that the test is supposed to verify.

## Guidance by value type

### Numbers

- Express business boundaries through semantic locals or parameter IDs: `minimum`, `maximum`, `just_below`, `just_above`.
- Include units in names when the type does not carry them: `timeout_seconds`, `price_cents`.
- Keep arbitrary ordinary examples simple. Do not create constants merely to replace `1`, `2`, or `100`.
- For floating-point behavior, use the framework's appropriate approximate comparison and choose values that reveal the intended precision rule.

### Strings

- Use strings that reveal the tested property: empty, whitespace, Unicode, case, length, escaping, or format.
- Name a string locally when its domain role matters, not because it is long.
- Use multiline literals or focused builders for large payloads; keep the scenario-relevant fragment visible.
- Use snapshots or golden files only for intentionally broad output contracts, with a reviewable update process.

### IDs

- Use deterministic, unmistakably synthetic values such as `user_test_001` when only identity matters.
- Use correctly formatted UUIDs or other IDs when parsing or validation is part of the contract.
- Use distinct semantic roles such as `owner_id` and `other_user_id`; do not rely on unexplained `ID_1` and `ID_2`.
- Avoid random IDs unless uniqueness is the subject of the test or a property-testing framework controls and reports the seed.

### Enums and status values

- Use the enum member in domain-level tests.
- Use raw strings or numbers only at serialization, parsing, database, or compatibility boundaries where the wire representation is what the test verifies.
- Parameterize enum cases when behavior is intentionally uniform across members.

### Paths

- Use the test framework's temporary-directory facility for filesystem tests.
- Construct paths with the platform path API; do not hardcode machine-specific absolute paths or separators.
- Use a pure/path value without I/O when only path transformation is under test.
- Keep meaningful filenames inline unless their role needs explanation.

### Dates and timestamps

- Use fixed, deterministic values; do not call the real clock in tests that need stable results.
- Use timezone-aware timestamps when the production domain is timezone-aware.
- Inject or fake the clock when behavior depends on "now".
- Derive `before`, `at`, and `after` values from a local anchor when their relationship is the point of the test.
- Use calendar-aware operations for months and years; do not approximate them with fixed day counts.

### Expected values

- Prefer explicit expected values that can be checked without understanding the implementation.
- Do not call the function under test, duplicate its algorithm, or import the same lookup table to calculate the expectation.
- A helper is appropriate only when it is an independent oracle, a standardized assertion, or a clearer representation of a large structured result.
- Assert only relevant fields when incidental output is not part of the contract; assert the full object when the complete representation is the contract.

### Repeated and domain-specific data

- A genuinely one-off example may remain local; once the same semantic concept is repeated or planned for reuse, give it one authoritative source.
- When the same data or setup concept supports multiple current or explicitly planned tests, centralize construction in a fixture or factory at the narrowest common scope.
- When an immutable semantic value crosses test-module boundaries, centralize it in one domain-organized test-support source and import it wherever needed.
- Centralize exact values only when uses represent the same concept and should evolve together, not merely because literals happen to match today.
- Prefer parameter tables, factory defaults, traits, and composed fixtures over copying rows, object literals, payloads, or setup blocks.
- Keep domain vocabulary in names and case IDs. Document surprising values at the point where the domain rule matters.
- Use generated/property-based tests for broad invariants and input spaces, but keep named examples for important regressions and boundaries.

## Review checks

Before finishing, check that:

- each test still reads as a concrete example of behavior;
- names add meaning rather than paraphrase literals;
- scenario-relevant data is visible near the action and assertion;
- fixture placement supports current and stated future test scale without making unrelated tests depend on it;
- mutable fixture data is fresh and parallel-safe, and wider-scoped resources have reliable reset behavior;
- every repeated semantic value, object shape, and setup block has one authoritative source wherever safe;
- cross-module sources are domain-organized rather than collected in a global dumping ground;
- setup helpers do not hide decisive defaults;
- expected results are independent of implementation logic;
- tests are deterministic and isolated;
- abstraction scope matches genuine sharing; and
- no production behavior changed unintentionally.

When responding, lead with the recommended representation and why it fits. If several choices are reasonable, state the tradeoff briefly. Prefer a focused before/after example over a wholesale rewrite.
