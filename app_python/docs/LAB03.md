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