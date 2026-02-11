# Lab 3 — Continuous Integration (CI/CD)

## Unit Testing

### Testing Framework Choice

For the testig I chose the **pytest** framework, because:

- This framework has a really simple yet powerful syntax for different test cases

- I have a braod experince with using this framework earlier

### Test Structure

All tests are stored by the path: `/app_python/tests/`. The file structure is the following:

- `conftest.py`. The file contains a client mock for making requests inside tests

- `test_errors.py`. The file contains all tests connected to error handling and invalid requests handling

- `test_health.py`. The file contains tests dedicated to the **/health** endpoint

- `test_index.py`. The file contains tests for the root endpoint `/`

### How to Run Tests

#### The **venv** package and **Python** are required

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r ./app_python/requirements.txt
pip install -r ./app_python/requirements-dev.txt
pytest app_python
```

### Terminal Output

![PytestResults](/app_python/docs/screenshots/PytestResults.png)

## GitHub Actions CI Workflow

### Workflow Trigger Strategy and Reasoning

**The workflow is triggered on:**

```yml
push:
  paths:
    - "app_python/**"
    - ".github/workflows/python-ci.yml"

pull_request:
  paths:
    - "app_python/**"
```

**The workflow runs only when:**

- Files inside app_python/ are modified

- The workflow file itself changes

**Reasoning**

- This path-based trigger strategy prevents unnecessary CI executions when unrelated parts of the repository (e.g., documentation or other applications) are modified

- It improves:

    - CI efficiency

    - Faster feedback cycles

    - Reduced compute usage


**Pull requests** also trigger the workflow to ensure code quality before merging changes into the main branch

### Why These Marketplace Actions Were Chosen

`actions/checkout@v4`

    Used to clone the repository into the runner environment.
    This is the standard action required for accessing repository code in workflows

`actions/setup-python@v5`

Sets up a Python 3.11 environment

**Reasons:**

- Official GitHub-maintained action

- Supports built-in pip dependency caching

- Ensures consistent Python version across environments

`docker/login-action@v3`

Used for secure authentication with Docker Hub using repository secrets.

**Reasons:**

- Official Docker-maintained action

- Secure handling of credentials via GitHub Secrets

- Prevents hardcoding sensitive information

`docker/build-push-action@v6`

Builds and pushes Docker images

**Reasons:**

- Official Docker action

- Supports multi-tag publishing

`snyk/actions/python`

Used for dependency vulnerability scanning.

**Reasons:**

- Integrates directly with Snyk security database

- Allows severity thresholds

- Helps detect high/critical vulnerabilities early in CI

### Docker Tagging Strategy

**Versioning Strategy:** *Calendar Versioning (CalVer)*

The workflow dynamically generates a version using:


```bash
echo "VERSION=$(date +%Y.%m)" >> $GITHUB_ENV
```

This produces tags such as: `2026.02`


Each build produces two tags:

- Version tag

    - `username/app:2026.02`

- Latest tag

    - `username/app:latest`

**Reasoning**

- It is simple and automation-friendly

- It clearly reflects release timing

The latest tag always points to the most recent stable build, while the version tag ensures traceability

### GitHub Actions Results

Here is the [link](https://github.com/TovarishDru/DevOps-Core-Course/actions/runs/21856785409) to the successful run

![CI Results](/app_python/docs/screenshots/GitHubResults.png)

## CI Best Practices & Security

### Status badge in README

![Status Badge](/app_python/docs/screenshots/StatusBadge.png)

### Caching Implementation

Dependency caching is implemented using the built-in pip caching feature of `actions/setup-python@v5`:

```yml
with:
    python-version: "3.11"
    cache: "pip"
```

On the first workflow run, dependencies are downloaded and cached. To be precise, [the first run](https://github.com/TovarishDru/DevOps-Core-Course/actions/runs/21856014196/job/63072953951) took **4s** to load the dependencies, while [the second one](https://github.com/TovarishDru/DevOps-Core-Course/actions/runs/21856785409/job/63075386941) looged the cache hit and was done in **3s**. In our case, the improvement was small, as the packets themselves are small, but for larger ones, it should be much more noticable

### CI Best Practices

**1. Fail-Fast Strategy (Job Dependencies)**

The workflow separates testing and deployment into two jobs:

```yml
docker:
  needs: test
```

This ensures that:

- Docker images are built only if tests, linting, and security scans pass

- Faulty code is never pushed to Docker Hub

- The pipeline stops early when errors occur

**2. Path-Based Workflow Triggers**

The workflow uses path filters:

```yml
paths:
  - "app_python/**"
  - ".github/workflows/python-ci.yml"
```

Benefits:

- Prevents unnecessary workflow executions

- Reduces CI runtime and compute costs

- Improves feedback speed

**3. Dependency Caching**

Caching is implemented using:

```yml
cache: "pip"
```

Benefits:

- Faster workflow execution on subsequent runs

- Reduced network downloads

- Lower CI resource usage

- Improved developer productivity

**4. Separation of Runtime and Development Dependencies**

The project uses two dependency files:

- requirements.txt → production dependencies

- requirements-dev.txt → testing and linting tools

Benefits:

- Smaller production Docker image

- Clear separation of concerns

- Faster Docker builds

- Only runtime dependencies are installed in the Docker image

**5. Secure Secrets Management**

Sensitive credentials are stored as GitHub Secrets, no credentials are hardcoded in the repository

```yml
DOCKERHUB_USERNAME

DOCKERHUB_TOKEN

SNYK_TOKEN
```

Benefits:

- Prevents secret leaks

- Protects Docker Hub account

- Enables secure automation

**6. Automated Versioning (CalVer)**

Version tags are generated dynamically:

```bash
echo "VERSION=$(date +%Y.%m)" >> $GITHUB_ENV
```

Benefits:

- Eliminates manual version management

- Ensures consistent tagging

- Enables automated Docker image publishing

Each image receives:

- A date-based version tag (e.g., 2026.02)

- A latest tag

**7. Static Code Analysis (Linting)**

Linting is performed using Ruff:

```yml
ruff check app_python
```

Benefits:

- Enforces consistent code quality

- Detects potential issues early

- Prevents style regressions

- Improves maintainability

**8. Security Scanning with Snyk**

Dependency vulnerabilities are scanned using Snyk:

```yml
--severity-threshold=high
```

Benefits:

- Detects known security vulnerabilities

- Prevents high-risk dependencies from being deployed

- Integrates security into CI pipeline

### Snyk Integration Results and Vulnerability Handling 

**Scan Configuration**

The following parameters are used:

- `--file=requirements.txt` → scans production dependencies

- `--severity-threshold=high` → fails the build only for high or critical vulnerabilities

- `--skip-unresolved` → ignores unresolved optional paths

This configuration ensures:

- `Low` and `medium` issues do not block deployment

- `High` and `critical` risks prevent Docker image publishing

- Security checks are enforced before deployment

**Scan Results**

From the GitHub Actions log:

```
Testing app_python...

Organization:      tovarishdru
Package manager:   pip
Target file:       requirements.txt
Project name:      app_python

✔ Tested app_python for known issues, no vulnerable paths found.
```

Result Summary:

- No high or critical vulnerabilities detected

- No dependency paths marked as vulnerable

- Security scan completed successfully

- CI pipeline continued to Docker build stage

**Vulnerability Handling Strategy**

If Snyk detects high or critical vulnerabilities:

- The workflow fails immediately

- The Docker image is not built or pushed

- The issue must be resolved before merging
