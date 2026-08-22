# Scalable fixtures and test data

Use this reference when test data or setup is reused, expected to grow beyond one test, has lifecycle concerns, or must work under parallel execution.

## Separate four responsibilities

Do not force one mechanism to do every job:

1. **Fixture or setup dependency:** supplies reusable state, resources, or a stable semantic context.
2. **Factory or builder:** creates fresh valid objects with explicit scenario overrides.
3. **Parameter data:** enumerates variations of the same behavior.
4. **Expected result:** states the independent oracle and usually remains visible in the test or parameter row.

A scalable test commonly uses all four. The fixture does not need to contain the expected result or every input.

## Extraction and placement guide

| Current or planned use | Preferred starting point |
| --- | --- |
| One test, simple input | Inline value or local semantic variable |
| Several cases of one behavior | Parameter table, optionally combined with a factory fixture |
| Two or more tests in one file share setup, an anchor, or an object shape | File-local fixture or factory fixture |
| Several files for one feature share the same concept | Feature-local test support or the framework's nearest shared-fixture location |
| Many unrelated features appear to use identical literals | Keep them separate unless they are genuinely one domain concept that must change together |
| Expensive external resource | Wider-scoped resource fixture plus function-scoped reset/isolation |

If the user explicitly plans additional tests, choose the row for that planned scale now. Do not wait for copy-and-paste to accumulate before extracting the fixture.

Keep fixture visibility as narrow as the framework permits. A file-local fixture is easier to discover and change than a suite-wide fixture. Promote it outward only after the same semantic dependency crosses the boundary.

## Choose the fixture form

### Value fixture

Use for an immutable semantic context shared by several tests, such as a fixed clock instant, canonical tenant context, locale, or protocol sample.

It is reasonable for a scalar when the fixture name represents shared meaning and the tests truly depend on the same concept. It is unnecessary for an arbitrary primitive used by one test.

### Object fixture

Use when every consuming test needs the same fresh valid object and does not vary its construction. Return a new object for every test unless immutability is guaranteed.

### Factory fixture

Prefer this for structured data that varies. The fixture owns valid defaults and any cleanup; each test passes only its meaningful differences.

Factory fixtures scale better than a family of narrowly named object fixtures such as `admin_user`, `inactive_user`, `expired_admin_user`, and every combination thereof. Named wrappers can still be useful for a few especially important domain states.

### Resource fixture

Use for databases, servers, temporary storage, clients, transactions, dependency wiring, fake clocks, and other lifecycle-managed resources. Separate expensive resource creation from per-test state reset.

### Automatic fixture

Use only when every test in its scope requires the environmental invariant and making the dependency explicit would add no useful information. Automatic fixtures can create invisible coupling and surprising runtime costs.

## Scope and mutation

- Prefer per-test/function scope for mutable domain data.
- Wider scope is suitable for immutable values or expensive resources, not mutable business entities shared between tests.
- If a module/session resource is reused, give each test an isolated namespace, transaction, schema, tenant, directory, or deterministic cleanup boundary.
- Ensure factories return fresh collections and nested objects; shallow copies can still leak mutation.
- Generate unique values deterministically when parallel tests require uniqueness. Avoid unseeded randomness and real-time timestamps.
- Cleanup must run after failures as well as successes. Use the framework's lifecycle mechanism rather than cleanup at the bottom of the test body.

## Composition rules

- Build small fixtures with single responsibilities and let the framework compose dependencies.
- Keep the fixture dependency graph shallow enough to understand from the test signature and nearby definitions.
- Avoid a fixture that selects behavior through many flags. Prefer a factory with explicit overrides or a few named domain-state builders.
- Keep the data field that causes the tested behavior visible in the test, even if the factory supplies everything else.
- Do not make a shared fixture import the system under test's expected lookup table or algorithm. The oracle must remain independent.

## Framework mapping

Use the repository's established idiom:

- **pytest:** file-local `@pytest.fixture`; promote to the nearest `conftest.py` only for cross-file reuse; return a callable for a factory fixture.
- **Jest/Vitest:** factory functions and `beforeEach` for fresh per-test setup; use `describe.each` or `test.each` for case variation; reserve global setup for real suite-wide environment work.
- **JUnit:** builders or `@BeforeEach` for ordinary objects; parameterized tests for data cases; extensions or shared lifecycle only for resource concerns.
- **xUnit .NET:** builders/factories for data variations; per-test class construction for fresh state; class or collection fixtures for genuinely expensive shared context with isolation.
- **RSpec:** factories/builders and narrowly scoped `let`; traits for important states; avoid deep implicit `let` chains that conceal decisive setup.

If the local repository uses another pattern consistently and safely, follow it unless the user asks for a migration.

## Scaling failure modes

Watch for:

- suite-wide fixtures created before cross-file reuse exists;
- fixture names that merely restate literals;
- expected outputs hidden in fixtures;
- shared mutable objects or order-dependent tests;
- session-scoped resources without per-test reset;
- fixture graphs whose decisive setup is several hops away;
- one factory with dozens of flags and surprising defaults;
- fixture-file explosion for every combination of states;
- random data that cannot reproduce a failure; and
- abstractions kept only because values look textually identical.

## Recommendation format

When advising on scalability, state:

1. the present and planned reuse boundary;
2. the recommended fixture/factory form and placement;
3. which inputs remain visible in each test;
4. how isolation, cleanup, determinism, and parallel execution are preserved; and
5. the trigger for promoting the fixture to a wider scope later.
