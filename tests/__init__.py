"""
Test suite for the Object Primitive System.

Test structure:
- unit/ - Unit tests (fast, isolated)
- integration/ - Integration tests (slower, use external resources)
- e2e/ - End-to-end tests (slowest, full system)
- fixtures/ - Shared test fixtures and helpers

Run tests:
    pytest                    # All tests
    pytest tests/unit         # Unit tests only
    pytest tests/integration  # Integration tests only
    pytest -m unit            # Tests marked as unit
    pytest -k "test_loader"   # Tests matching name
    pytest --cov              # With coverage

Philosophy:
    Tests are critical. The primitives must work perfectly.
    Test-first development (TDD) throughout.

    Unit tests should be fast (<1ms each).
    Integration tests can be slower (<100ms each).
    E2E tests can be slowest (<1s each).

    Aim for 100% coverage on core primitives.
"""
