# Recommendation Service

[![Build](https://github.com/CSCI-GA-2820-SP26-003/recommendations/actions/workflows/ci.yml/badge.svg)](https://github.com/CSCI-GA-2820-SP26-003/recommendations/actions/workflows/ci.yml)
[![Codecov](https://codecov.io/gh/CSCI-GA-2820-SP26-003/recommendations/graph/badge.svg)](https://codecov.io/gh/CSCI-GA-2820-SP26-003/recommendations)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Language-Python-blue.svg)](https://python.org/)

A RESTful microservice that manages product-to-product recommendations for an e-commerce platform. Built with Flask + Flask-RESTX and backed by PostgreSQL. Part of the NYU DevOps (CSCI-GA.2820) course project.

## Overview

The service stores recommendations that say "if a customer is looking at product A, also show product B". Each recommendation has a type (`cross_sell`, `up_sell`, `accessory`, `similar_item`), an optional relevance score, an active/inactive flag, and a cumulative like count. The API is documented with Swagger/OpenAPI via Flask-RESTX and exposes a simple web management UI at the root URL.

## Setup

### Prerequisites

- Docker
- VS Code with the Dev Containers extension

### Open in Dev Container

Clone the repository and open it in VS Code. When prompted, click **Reopen in Container** (or run *Dev Containers: Reopen in Container*). The container includes Python 3.12, PostgreSQL 15, and all project dependencies.

### Initialize the database

```bash
flask db-create
```

### Start the service

```bash
make run
```

The service is available at `http://localhost:8080`.

## Running Tests

```bash
make test
```

Runs the full unit-test suite with pytest and enforces a minimum coverage of **95%**.

```bash
make lint
```

Runs `flake8` (syntax + complexity) and `pylint` over `service/` and `tests/`.

```bash
make bdd
```

Runs the Behave BDD scenarios against the running service (requires Selenium/Chrome).

## API Reference

Swagger/OpenAPI documentation: `/apidocs/`

API index (version, doc link, all endpoint groups): `/apiIndex`

### Service Info

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/health` | Health check — returns `{"status": "OK"}` |
| GET | `/apiIndex` | API index with version and callable endpoints |
| GET | `/api/health/` | Flask-RESTX health check |
| GET | `/apidocs/` | Swagger/OpenAPI documentation |

### Recommendation CRUD

| Method | URL | Description | Body | Response |
|--------|-----|-------------|------|----------|
| POST | `/recommendations` | Create a recommendation | JSON | 201 Created |
| GET | `/recommendations` | List recommendations (with optional filters) | — | 200 OK |
| GET | `/recommendations/<id>` | Retrieve a recommendation | — | 200 OK |
| PUT | `/recommendations/<id>` | Update a recommendation | JSON | 200 OK |
| DELETE | `/recommendations/<id>` | Delete (idempotent — 204 even if missing) | — | 204 No Content |

### Action Endpoints

| Method | URL | Description | Response |
|--------|-----|-------------|----------|
| PUT | `/recommendations/<id>/activate` | Mark a recommendation active | 200 OK |
| PUT | `/recommendations/<id>/deactivate` | Mark a recommendation inactive | 200 OK |
| PUT | `/recommendations/<id>/like` | Increment the like count | 200 OK |

### Create / Update Request Body

```json
{
  "product_id": 1,
  "recommended_product_id": 2,
  "recommendation_type": "cross_sell",
  "score": 0.85,
  "active": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `product_id` | integer | yes | Source product identifier |
| `recommended_product_id` | integer | yes | Recommended product identifier (must differ from `product_id`) |
| `recommendation_type` | string | yes | One of: `cross_sell`, `up_sell`, `accessory`, `similar_item` |
| `score` | float | no | Relevance score (0.0 – 1.0) |
| `active` | boolean | no | Whether active (default: `true`) |

### Example Response

```json
{
  "id": 1,
  "product_id": 1,
  "recommended_product_id": 2,
  "recommendation_type": "cross_sell",
  "active": true,
  "score": 0.85,
  "like_count": 0,
  "created_at": "2026-04-29T12:00:00+00:00"
}
```

### Filtering and Pagination

`GET /recommendations` accepts the following query parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| `product_id` | integer | Filter by source product ID |
| `recommended_product_id` | integer | Filter by recommended product ID |
| `recommendation_type` | string | Filter by type |
| `page` | integer | Page number (10 results per page). Omit to return all. |

Example:

```
GET /recommendations?product_id=1&recommendation_type=cross_sell&page=1
```

### Compatibility Paths

The same CRUD and action operations are also available at:

- `/api/recommendations` — Flask-RESTX namespace
- `/api/recommendations/v1/recommendations` — legacy path for older clients

## Data Model

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | integer | server-generated | Primary key |
| `product_id` | integer | yes | Source product |
| `recommended_product_id` | integer | yes | Must differ from `product_id` |
| `recommendation_type` | string | yes | `cross_sell` \| `up_sell` \| `accessory` \| `similar_item` |
| `active` | boolean | yes | Default: `true` |
| `score` | float | no | Relevance score |
| `like_count` | integer | server-managed | Starts at 0, incremented via `/like` |
| `created_at` | datetime | server-generated | ISO-8601 UTC timestamp |

Validation rules enforced at the model layer:

- `product_id` and `recommended_product_id` must be different (also enforced by a DB `CHECK` constraint).
- `recommendation_type` must be one of the four allowed values.

## Project Structure

```
service/                   - service Python package
  __init__.py              - Flask app factory (create_app)
  config.py                - configuration parameters
  models.py                - SQLAlchemy model and DataValidationError
  routes.py                - Flask-RESTX resources and compatibility routes
  common/
    cli_commands.py        - flask db-create CLI command
    error_handlers.py      - HTTP error handling
    log_handlers.py        - logging setup
    status.py              - HTTP status constants

tests/                     - unit test suite (pytest, ≥95% coverage)
  factories.py             - Factory Boy factories for test data
  test_cli_commands.py     - CLI command tests
  test_models.py           - model layer tests
  test_routes.py           - route / API tests

features/                  - BDD test suite (Behave + Selenium)
  recommendations.feature  - Gherkin scenarios
  steps/
    recommendations_steps.py - step definitions

k8s/                       - Kubernetes manifests
  deployment.yaml          - 2-replica Deployment with readiness/liveness probes
  service.yaml             - ClusterIP Service on port 8080
  ingress.yaml             - Ingress
  postgres/
    statefulset.yaml       - PostgreSQL StatefulSet
    pvc.yaml               - Persistent Volume Claim
    service.yaml           - PostgreSQL ClusterIP Service
    secret.yaml            - DATABASE_URI secret

.tekton/                   - Tekton CD pipeline
  pipeline.yaml            - git-clone → pylint+pytest → buildah → deploy-image → behave
  tasks.yaml               - custom task definitions
  workspace.yaml           - shared workspace
  events/                  - EventListener + Trigger for webhook-driven runs

.github/workflows/
  ci.yml                   - GitHub Actions CI (lint → pytest → Codecov)

.devcontainer/             - VS Code Dev Container configuration
Dockerfile                 - Production container image (gunicorn)
Pipfile / Pipfile.lock     - Python dependencies
Makefile                   - Developer shortcuts (run, test, lint, bdd, deploy, …)
Procfile                   - honcho process definition (gunicorn)
```

## CI / CD

**CI (GitHub Actions)** — runs on every push to `master` and on every pull request:

1. Install dependencies with pipenv
2. Lint with flake8 and pylint
3. Run pytest against a PostgreSQL service container (enforces ≥95% coverage)
4. Upload coverage report to Codecov

**CD (Tekton)** — runs in the OpenShift cluster and is triggered via a GitHub webhook:

1. `git-clone` — check out the repository
2. `pylint` + `pytest` — run in parallel
3. `buildah` — build and push a container image to the internal OpenShift registry
4. `deploy-image` — apply the `k8s/` manifests via `kubectl`
5. `behave` — run BDD acceptance tests against the deployed service

## Kubernetes Deployment

The service runs as a 2-replica Deployment on port 8080. Each pod has:

- A readiness probe at `GET /health` (initial delay 10 s, period 5 s)
- A liveness probe at `GET /health` (initial delay 15 s, period 10 s)
- CPU request 100 m / limit 500 m; memory request 128 Mi / limit 256 Mi
- `DATABASE_URI` injected from the `postgres-creds` Secret

To deploy locally with K3D:

```bash
make cluster    # create a k3d cluster with a local registry
make build      # build the Docker image
make push       # push to the local registry
make deploy     # kubectl apply -R -f k8s/
```

## License

Copyright (c) 2016, 2025 John Rofrano. All rights reserved.

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE).

This repository is part of the New York University (NYU) masters class: CSCI-GA.2820 DevOps and Agile Methodologies, created and taught by John Rofrano, Adjunct Instructor, NYU Courant Institute, Graduate Division, Computer Science, and NYU Stern School of Business.
