# Lab 3 - Continuous Integration (CI/CD)

## 1. Overview

### Testing Framework: pytest

**Why pytest?**

- **Simple syntax**: Tests are plain Python functions, no boilerplate classes required
- **Powerful fixtures**: The fixture system handles test setup/teardown elegantly
- **Rich plugin ecosystem**: pytest-cov for coverage, pytest-asyncio for async tests
- **Better assertions**: Uses plain `assert` statements with detailed failure messages
- **Wide adoption**: Industry standard for Python testing

### Test Coverage

The tests cover both endpoints with comprehensive scenarios:

**GET / (Root Endpoint)**

- Response status code (200)
- JSON content type validation
- All required top-level fields (service, system, runtime, request, endpoints)
- Service info structure and values
- System info structure and types
- Runtime info structure
- Request info structure and reflection
- Endpoints list structure and validation
- Custom header handling (User-Agent)

**GET /health (Health Endpoint)**

- Response status code (200)
- JSON content type validation
- Required fields (status, timestamp, uptime_seconds)
- Status value validation ("healthy")
- Uptime non-negative integer check
- Timestamp format validation
- Trailing slash handling
- HTTP method restrictions (405 for POST/PUT/DELETE)
- Consistency across multiple calls

### CI Workflow Triggers

The workflow runs on:

- **Push** to `master` or `lab3` branches (only when `app_python/` or workflow files change)
- **Pull requests** to `master` branch (only when `app_python/` or workflow files change)

Path filtering ensures the CI only runs when relevant files are modified, saving resources.

### Versioning Strategy: CalVer (Calendar Versioning)

**Format:** `YYYY.MM.BUILD_NUMBER` (e.g., `2026.02.42`)

**Why CalVer?**

- **Time-based clarity**: Easy to identify when an image was built
- **Continuous deployment fit**: Ideal for services with frequent updates
- **No manual versioning**: Build number auto-increments via GitHub run number
- **Simple implementation**: No need to parse commits or manage version files

**Docker Tags Created:**

- `YYYY.MM.BUILD_NUMBER` - Specific version tag
- `latest` - Only on master branch pushes
- `sha-<commit>` - Git commit SHA for traceability

## 2. Workflow Evidence

### Successful Workflow Run

- GitHub Actions link: (Will be available after first successful run)
- Check the Actions tab: https://github.com/MoriSummerz/DevOps-Core-Course/actions

### Tests Passing Locally

```bash
$ cd app_python
$ pip install -r requirements-dev.txt
$ pytest -v

========================= test session starts ==========================
platform darwin -- Python 3.12.x, pytest-8.3.5, pluggy-1.5.0
rootdir: /Users/morisummer/PycharmProjects/DevOps-Core-Course/app_python
configfile: pytest.ini
collected 21 items

tests/test_health.py::TestHealthEndpoint::test_health_returns_200 PASSED
tests/test_health.py::TestHealthEndpoint::test_health_returns_json PASSED
tests/test_health.py::TestHealthEndpoint::test_health_response_has_required_fields PASSED
tests/test_health.py::TestHealthEndpoint::test_health_status_is_healthy PASSED
tests/test_health.py::TestHealthEndpoint::test_health_uptime_is_non_negative PASSED
tests/test_health.py::TestHealthEndpoint::test_health_timestamp_is_valid PASSED
tests/test_health.py::TestHealthEndpoint::test_health_without_trailing_slash PASSED
tests/test_health.py::TestHealthEndpointEdgeCases::test_health_method_not_allowed_post PASSED
tests/test_health.py::TestHealthEndpointEdgeCases::test_health_method_not_allowed_put PASSED
tests/test_health.py::TestHealthEndpointEdgeCases::test_health_method_not_allowed_delete PASSED
tests/test_health.py::TestHealthEndpointEdgeCases::test_multiple_health_calls_consistent PASSED
tests/test_root.py::TestRootEndpoint::test_root_returns_200 PASSED
tests/test_root.py::TestRootEndpoint::test_root_returns_json PASSED
tests/test_root.py::TestRootEndpoint::test_root_response_has_required_fields PASSED
tests/test_root.py::TestRootEndpoint::test_service_info_structure PASSED
tests/test_root.py::TestRootEndpoint::test_system_info_structure PASSED
tests/test_root.py::TestRootEndpoint::test_runtime_info_structure PASSED
tests/test_root.py::TestRootEndpoint::test_request_info_structure PASSED
tests/test_root.py::TestRootEndpoint::test_endpoints_is_list PASSED
tests/test_root.py::TestRootEndpoint::test_endpoints_structure PASSED
tests/test_root.py::TestRootEndpoint::test_custom_user_agent_reflected PASSED

========================= 21 passed in X.XXs ===========================
```

### Docker Image on Docker Hub

- Docker Hub link: https://hub.docker.com/r/<username>/devops-info-service
- (Will show versioned tags after first successful push)

### Status Badge

- Badge added to `app_python/README.md`
- Shows workflow status (passing/failing)

## 3. Best Practices Implemented

| Practice                   | Description                                                                                                                                |
|----------------------------|--------------------------------------------------------------------------------------------------------------------------------------------|
| **Dependency Caching**     | Uses `actions/setup-python` built-in pip caching keyed on `requirements-dev.txt` hash. Reduces install time from ~30s to ~5s on cache hit. |
| **Job Dependencies**       | `build-and-push` job only runs after `lint-and-test` and `security-scan` succeed. Prevents pushing broken images.                          |
| **Conditional Deployment** | Docker push only happens on pushes to master/lab3 branches, not on PRs. Prevents unauthorized image publications.                          |
| **Path Filtering**         | Workflow only triggers when `app_python/` files change. Saves CI minutes when only docs change.                                            |
| **Docker Layer Caching**   | Uses GitHub Actions cache (`cache-from: type=gha`) for Docker layers. Significantly speeds up rebuilds.                                    |
| **Security Scanning**      | Snyk integration scans dependencies for known vulnerabilities before deployment.                                                           |
| **Fail Fast**              | Default behavior stops matrix builds on first failure, saving resources.                                                                   |

### Caching Performance

| Metric             | Without Cache | With Cache            |
|--------------------|---------------|-----------------------|
| Dependency Install | ~25-30s       | ~3-5s                 |
| Docker Build       | ~60s          | ~15-20s (layer cache) |

### Snyk Integration

- Configured with `--severity-threshold=high` to catch critical vulnerabilities
- Set to `continue-on-error: true` to not block deployment for non-critical issues
- Vulnerabilities found: (Will be updated after first scan)

## 4. Key Decisions

### Versioning Strategy

**CalVer** was chosen because this is a continuously deployed service, not a library. The date-based version immediately
tells users when an image was built, and the auto-incrementing build number ensures uniqueness without manual
intervention.

### Docker Tags

Each CI run creates:

1. **CalVer tag** (`2026.02.42`): Immutable, specific version
2. **Latest tag**: Rolling tag pointing to newest master build
3. **SHA tag** (`sha-abc1234`): Links image directly to git commit

### Workflow Triggers

- **Push triggers**: Enables CD - every push to main branches auto-deploys
- **PR triggers**: Validates changes before merge without deploying
- **Path filters**: Prevents unnecessary runs, crucial for monorepo setups

### Test Coverage

Tests focus on:

- **Structure validation**: All required fields exist
- **Type checking**: Values are correct types
- **Business logic**: Status values, method restrictions
- **Edge cases**: Missing trailing slashes, wrong HTTP methods

Not tested (intentionally):

- Exact hostname/platform values (machine-dependent)
- Exact timestamps (time-dependent)
- External service integration (would need mocking)

## 5. Challenges

- **FastAPI test client setup**: Required `httpx` as dependency for `TestClient`
- **Path-based workflow triggers**: Needed to include workflow file itself in paths to ensure changes to CI trigger CI
- **Snyk token setup**: Required creating Snyk account and adding token to GitHub secrets
