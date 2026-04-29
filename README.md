# Recommendation Service

[![Build](https://github.com/CSCI-GA-2820-SP26-003/recommendations/actions/workflows/ci.yml/badge.svg)](https://github.com/CSCI-GA-2820-SP26-003/recommendations/actions/workflows/ci.yml)
[![Codecov](https://codecov.io/gh/CSCI-GA-2820-SP26-003/recommendations/graph/badge.svg)](https://codecov.io/gh/CSCI-GA-2820-SP26-003/recommendations)
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

Swagger/OpenAPI documentation is available at `/apidocs/`. The documented
Flask-RESTX API version is `1.0`.

An API index with the service version, documentation link, and all callable
endpoint groups is available at `/apiIndex`.

The grading-compatible REST endpoints are available at `/recommendations`.
The Flask-RESTX documented API is available under `/api`, and the legacy
`/api/recommendations/v1` paths are still supported for backward compatibility.

### Service Info

Method | URL | Description
--- | --- | ---
GET | `/health` | Health check
GET | `/apiIndex` | API index with version and callable endpoints
GET | `/api/health/` | Flask-RESTX health check
GET | `/apidocs/` | Swagger/OpenAPI documentation

### Recommendation CRUD Endpoints

Method | URL | Description | Request Body | Response Code
--- | --- | --- | --- | ---
POST | `/recommendations` | Create a recommendation | JSON (see below) | 201 Created
GET | `/recommendations` | List all recommendations | None | 200 OK
GET | `/recommendations/<id>` | Read a recommendation | None | 200 OK
PUT | `/recommendations/<id>` | Update a recommendation | JSON (see below) | 200 OK
DELETE | `/recommendations/<id>` | Delete a recommendation idempotently | None | 204 No Content

### Recommendation Action Endpoints

Method | URL | Description | Response Code
--- | --- | --- | ---
PUT | `/recommendations/<id>/activate` | Mark a recommendation active | 200 OK
PUT | `/recommendations/<id>/deactivate` | Mark a recommendation inactive | 200 OK
PUT | `/recommendations/<id>/like` | Increment the recommendation like count | 200 OK

### Create / Update Request Body

```json
{
  "product_id": 1,
  "recommended_product_id": 2,
  "recommendation_type": "cross_sell",
  "score": 0.85
}
```

- `product_id` (integer, required) - Source product identifier
- `recommended_product_id` (integer, required) - Recommended product identifier
- `recommendation_type` (string, required) - One of: `cross_sell`, `up_sell`, `accessory`, `similar_item`
- `score` (float, optional) - Recommendation score

### Example Response

```json
{
  "id": 1,
  "product_id": 1,
  "recommended_product_id": 2,
  "recommendation_type": "cross_sell",
  "score": 0.85,
  "created_at": "2026-03-02T12:00:00+00:00"
}
```

### List with Query and Pagination

The list endpoint supports filtering by `product_id`,
`recommended_product_id`, and `recommendation_type`. It also supports optional
pagination via the `page` query parameter:

```
GET /recommendations?product_id=1&recommendation_type=cross_sell&page=1
```

Returns up to 10 results per page. Omit the `page` parameter to return all results.

### Compatibility Paths

The same CRUD and action operations are also available under
`/api/recommendations` for Flask-RESTX and under
`/api/recommendations/v1/recommendations` for older clients.

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
