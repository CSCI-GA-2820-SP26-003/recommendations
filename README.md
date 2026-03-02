# Recommendation Service

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Language-Python-blue.svg)](https://python.org/)

The Recommendation service is a RESTful API that manages product recommendations for an e-commerce application. It is part of the NYU DevOps course project.

## Setup

### Prerequisites

- Docker
- VS Code with the Dev Containers extension

### Manual Setup

You can also clone this repository and then copy and paste the starter code into your project repo folder on your local computer. Be careful not to copy over your own README.md file so be selective in what you copy.

There are 4 hidden files that you will need to copy manually if you use the Mac Finder or Windows Explorer to copy files from this folder into your repo folder.

These should be copied using a bash shell as follows:

```
cp .gitignore  ../<your_repo_folder>/
cp .flaskenv ../<your_repo_folder>/
cp .gitattributes ../<your_repo_folder>/
```

## Getting Started

1. Clone the repository and open it in VS Code.
2. When prompted, click Reopen in Container (or run the Dev Containers: Reopen in Container command). This starts a development container with Python, PostgreSQL, and all dependencies pre-installed.
3. Initialize the database:

```
flask db-create
```

4. Start the service:

```
make run
```

The service will be available at http://localhost:8080.

## Running Tests

```
make test
```

This runs the full test suite with pytest and enforces a minimum coverage threshold of 95%.

To lint the code:

```
make lint
```

## API Reference

All endpoints are under the base path `/api/recommendations/v1` by default.

### Service Info

Method | URL | Description
--- | --- | ---
GET | / | Returns service name, environment, and base path
GET | /api/recommendations/v1/health | Health check

## Recommendation Model

Field | Type | Required | Description
--- | --- | --- | ---
id | integer | no | Server-generated identifier
product_id | integer | yes | Source product identifier
recommended_product_id | integer | yes | Recommended product identifier
recommendation_type | string | yes | One of: cross_sell, up_sell, accessory, similar_item
score | float | no | Recommendation score
created_at | string | no | Server-generated ISO-8601 timestamp

Validation rules:

- product_id and recommended_product_id must be different.
- recommendation_type must be one of the allowed values.

## Project Structure

.gitignore          - this will ignore vagrant and other metadata files
.flaskenv           - Environment variables to configure Flask
.gitattributes      - File to fix Windows CRLF issues
.devcontainer/      - Folder with support for VSCode Remote Containers
dot-env-example     - copy to .env to use environment variables
Pipfile             - Pipenv list of Python libraries required by your code
Pipfile.lock        - Pipenv resolved dependency versions

service/                   - service python package
  __init__.py              - package initializer
  config.py                - configuration parameters
  models.py                - module with business models
  routes.py                - module with service routes
  common/                  - common code package
    cli_commands.py        - Flask CLI commands (db-create)
    error_handlers.py      - HTTP error handling code
    log_handlers.py        - logging setup code
    status.py              - HTTP status constants

tests/                     - test cases package
  __init__.py              - package initializer
  factories.py             - Factory for testing with fake objects
  test_cli_commands.py     - test suite for the CLI
  test_models.py           - test suite for business models
  test_routes.py           - test suite for service routes

## License

Copyright (c) 2016, 2025 John Rofrano. All rights reserved.

Licensed under the Apache License. See LICENSE

This repository is part of the New York University (NYU) masters class: CSCI-GA.2820-001 DevOps and Agile Methodologies created and taught by John Rofrano, Adjunct Instructor, NYU Courant Institute, Graduate Division, Computer Science, and NYU Stern School of Business.
