######################################################################
# Copyright 2016, 2024 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
######################################################################

"""
Recommendation Service REST API Routes

This service implements a REST API using Flask-RESTX, which provides
automatic Swagger/OpenAPI documentation at /apidocs.
"""

import os
from flask import abort, redirect, request
from flask_restx import Api, Resource, fields
from werkzeug.exceptions import (
    BadRequest,
    NotFound,
    Conflict,
    MethodNotAllowed,
    UnsupportedMediaType,
    InternalServerError,
)
from service.common import status  # HTTP Status Codes
from service.models import Recommendation, DataValidationError, RECOMMENDATION_TYPES


######################################################################
# Path helpers
######################################################################
def _normalize_prefix(path):
    """Normalize API prefix into a valid leading-slash path"""
    prefix = (path or "/api/recommendations").strip()
    if not prefix:
        prefix = "/api/recommendations"
    if not prefix.startswith("/"):
        prefix = f"/{prefix}"
    normalized = prefix.rstrip("/")
    return normalized or "/"


def _normalize_version(version):
    """Normalize API version path segment"""
    return (version or "").strip().strip("/")


def _build_base_path():
    """Compose BASE_PATH from API_PREFIX and API_VERSION"""
    api_prefix = _normalize_prefix(os.getenv("API_PREFIX", "/api"))
    api_version = _normalize_version(os.getenv("API_VERSION", "v1"))
    return f"{api_prefix}/{api_version}" if api_version else api_prefix


ENV_NAME = os.getenv("ENV", "local")
BASE_PATH = _build_base_path()
LEGACY_BASE_PATH = "/api/recommendations/v1"
SERVICE_NAME = "recommendation"
API_VERSION = "1.0"


######################################################################
# Flask-RESTX API
######################################################################
api = Api(
    version=API_VERSION,
    title="Recommendation API",
    description="A RESTful microservice for managing product recommendations",
    prefix="/api",
    doc="/apidocs",
)

# ── Namespaces ──────────────────────────────────────────────────────
ns = api.namespace("recommendations", description="Recommendation CRUD operations")
health_ns = api.namespace("health", description="Health check operations")


######################################################################
# Swagger Data Models
######################################################################
create_model = api.model(
    "CreateRecommendation",
    {
        "product_id": fields.Integer(
            required=True,
            description="Source product ID",
            example=1,
        ),
        "recommended_product_id": fields.Integer(
            required=True,
            description="Recommended product ID",
            example=2,
        ),
        "recommendation_type": fields.String(
            required=True,
            description="Type of recommendation",
            enum=["cross_sell", "up_sell", "accessory", "similar_item"],
            example="cross_sell",
        ),
        "score": fields.Float(
            description="Recommendation relevance score (0.0-1.0)",
            example=0.85,
        ),
        "active": fields.Boolean(
            description="Whether the recommendation is active",
            example=True,
        ),
    },
)

recommendation_model = api.model(
    "Recommendation",
    {
        "id": fields.Integer(readonly=True, description="Unique recommendation ID"),
        "product_id": fields.Integer(description="Source product ID"),
        "recommended_product_id": fields.Integer(description="Recommended product ID"),
        "recommendation_type": fields.String(
            description="Type: cross_sell | up_sell | accessory | similar_item"
        ),
        "active": fields.Boolean(description="Whether the recommendation is active"),
        "score": fields.Float(description="Relevance score (0.0-1.0)"),
        "like_count": fields.Integer(description="Cumulative like count"),
        "created_at": fields.String(description="ISO-8601 creation timestamp"),
    },
)

error_model = api.model(
    "Error",
    {
        "status": fields.Integer(description="HTTP status code"),
        "error": fields.String(description="Error type"),
        "message": fields.String(description="Detailed error message"),
    },
)


######################################################################
# API INDEX
######################################################################
def api_index_payload():
    """Return a structured index of callable API endpoints."""
    canonical_endpoints = [
        {
            "name": "List recommendations",
            "method": "GET",
            "path": "/recommendations",
            "query": [
                "product_id",
                "recommended_product_id",
                "recommendation_type",
                "page",
            ],
        },
        {
            "name": "Create recommendation",
            "method": "POST",
            "path": "/recommendations",
        },
        {
            "name": "Retrieve recommendation",
            "method": "GET",
            "path": "/recommendations/{id}",
        },
        {
            "name": "Update recommendation",
            "method": "PUT",
            "path": "/recommendations/{id}",
        },
        {
            "name": "Delete recommendation",
            "method": "DELETE",
            "path": "/recommendations/{id}",
            "notes": "Idempotent: returns 204 even when the resource is missing.",
        },
        {
            "name": "Activate recommendation",
            "method": "PUT",
            "path": "/recommendations/{id}/activate",
        },
        {
            "name": "Deactivate recommendation",
            "method": "PUT",
            "path": "/recommendations/{id}/deactivate",
        },
        {
            "name": "Like recommendation",
            "method": "PUT",
            "path": "/recommendations/{id}/like",
        },
        {
            "name": "Health check",
            "method": "GET",
            "path": "/health",
        },
    ]
    restx_endpoints = [
        {
            **endpoint,
            "path": endpoint["path"].replace(
                "/recommendations", "/api/recommendations", 1
            ),
        }
        if endpoint["path"].startswith("/recommendations")
        else {
            "name": endpoint["name"],
            "method": endpoint["method"],
            "path": "/api/health/",
        }
        for endpoint in canonical_endpoints
    ]
    legacy_endpoints = [
        {
            **endpoint,
            "path": endpoint["path"].replace(
                "/recommendations", f"{LEGACY_BASE_PATH}/recommendations", 1
            ),
        }
        if endpoint["path"].startswith("/recommendations")
        else {
            "name": endpoint["name"],
            "method": endpoint["method"],
            "path": f"{LEGACY_BASE_PATH}/health",
        }
        for endpoint in canonical_endpoints
    ]

    return {
        "service": SERVICE_NAME,
        "title": "Recommendation API",
        "version": API_VERSION,
        "environment": ENV_NAME,
        "documentation": "/apidocs/",
        "canonical_base_path": "/recommendations",
        "restx_base_path": "/api/recommendations",
        "legacy_base_path": f"{LEGACY_BASE_PATH}/recommendations",
        "endpoints": {
            "canonical": canonical_endpoints,
            "flask_restx": restx_endpoints,
            "legacy": legacy_endpoints,
        },
    }


# Error Handlers
######################################################################
@api.errorhandler(DataValidationError)
def handle_validation_error(error):
    """Handle data validation errors from the model layer"""
    message = str(error)
    return (
        {
            "status": status.HTTP_400_BAD_REQUEST,
            "error": "Bad Request",
            "message": message,
        },
        status.HTTP_400_BAD_REQUEST,
    )


@api.errorhandler(BadRequest)
def handle_bad_request(error):
    """Handle 400 Bad Request errors"""
    message = str(error)
    return (
        {
            "status": status.HTTP_400_BAD_REQUEST,
            "error": "Bad Request",
            "message": message,
        },
        status.HTTP_400_BAD_REQUEST,
    )


@api.errorhandler(NotFound)
def handle_not_found(error):
    """Handle 404 Not Found errors"""
    message = str(error)
    return (
        {
            "status": status.HTTP_404_NOT_FOUND,
            "error": "Not Found",
            "message": message,
        },
        status.HTTP_404_NOT_FOUND,
    )


@api.errorhandler(MethodNotAllowed)
def handle_method_not_allowed(error):
    """Handle 405 Method Not Allowed errors"""
    message = str(error)
    return (
        {
            "status": status.HTTP_405_METHOD_NOT_ALLOWED,
            "error": "Method not Allowed",
            "message": message,
        },
        status.HTTP_405_METHOD_NOT_ALLOWED,
    )


@api.errorhandler(Conflict)
def handle_conflict(error):
    """Handle 409 Conflict errors"""
    message = str(error)
    return (
        {
            "status": status.HTTP_409_CONFLICT,
            "error": "Conflict",
            "message": message,
        },
        status.HTTP_409_CONFLICT,
    )


@api.errorhandler(UnsupportedMediaType)
def handle_unsupported_media(error):
    """Handle 415 Unsupported Media Type errors"""
    message = str(error)
    return (
        {
            "status": status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "error": "Unsupported media type",
            "message": message,
        },
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    )


@api.errorhandler(InternalServerError)
def handle_internal_error(error):
    """Handle 500 Internal Server Error"""
    message = str(error)
    return (
        {
            "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "error": "Internal Server Error",
            "message": message,
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


######################################################################
# Helper
######################################################################
def check_content_type(content_type):
    """Verify the request Content-Type header matches the expected type"""
    if "Content-Type" not in request.headers:
        abort(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Content-Type must be {content_type}",
        )
    if request.headers["Content-Type"] != content_type:
        abort(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Content-Type must be {content_type}",
        )


######################################################################
# Business helpers shared by RESTX resources and compatibility routes
######################################################################
def list_recommendations():
    """List all Recommendations with optional filtering and pagination"""
    product_id = request.args.get("product_id", type=int)
    recommended_product_id = request.args.get("recommended_product_id", type=int)
    recommendation_type = request.args.get("recommendation_type", type=str)
    page = request.args.get("page", type=int)

    query = Recommendation.query

    if product_id is not None:
        query = query.filter(Recommendation.product_id == product_id)

    if recommended_product_id is not None:
        query = query.filter(
            Recommendation.recommended_product_id == recommended_product_id
        )

    if recommendation_type is not None:
        if recommendation_type not in RECOMMENDATION_TYPES:
            abort(
                status.HTTP_400_BAD_REQUEST,
                f"Invalid recommendation_type: {recommendation_type}",
            )
        query = query.filter(Recommendation.recommendation_type == recommendation_type)

    if page is not None:
        pagination = query.paginate(page=page, per_page=10, error_out=False)
        recommendations = pagination.items
    else:
        recommendations = query.all()

    return [recommendation.serialize() for recommendation in recommendations]


def create_recommendation(location_base="/recommendations"):
    """Create a new Recommendation"""
    check_content_type("application/json")
    recommendation = Recommendation()
    recommendation.deserialize(request.get_json())
    recommendation.create()
    message = recommendation.serialize()
    location_url = f"{location_base.rstrip('/')}/{recommendation.id}"
    return message, status.HTTP_201_CREATED, {"Location": location_url}


def get_recommendation(recommendation_id):
    """Retrieve a single Recommendation by its ID"""
    recommendation = Recommendation.find(recommendation_id)
    if not recommendation:
        abort(
            status.HTTP_404_NOT_FOUND,
            f"Recommendation with id '{recommendation_id}' was not found.",
        )
    return recommendation.serialize()


def update_recommendation(recommendation_id):
    """Update a Recommendation by its ID"""
    check_content_type("application/json")
    recommendation = Recommendation.find(recommendation_id)
    if not recommendation:
        abort(
            status.HTTP_404_NOT_FOUND,
            f"Recommendation with id '{recommendation_id}' was not found.",
        )
    recommendation.deserialize(request.get_json())
    recommendation.update()
    return recommendation.serialize()


def delete_recommendation(recommendation_id):
    """Delete a Recommendation by its ID, idempotently"""
    recommendation = Recommendation.find(recommendation_id)
    if recommendation:
        recommendation.delete()
    return "", status.HTTP_204_NO_CONTENT


def activate_recommendation(recommendation_id):
    """Mark a Recommendation as active"""
    recommendation = Recommendation.find(recommendation_id)
    if not recommendation:
        abort(
            status.HTTP_404_NOT_FOUND,
            f"Recommendation with id '{recommendation_id}' was not found.",
        )
    recommendation.active = True
    recommendation.update()
    return recommendation.serialize()


def deactivate_recommendation(recommendation_id):
    """Mark a Recommendation as inactive"""
    recommendation = Recommendation.find(recommendation_id)
    if not recommendation:
        abort(
            status.HTTP_404_NOT_FOUND,
            f"Recommendation with id '{recommendation_id}' was not found.",
        )
    recommendation.active = False
    recommendation.update()
    return recommendation.serialize()


def like_recommendation(recommendation_id):
    """Increment the like count for a Recommendation"""
    recommendation = Recommendation.find(recommendation_id)
    if not recommendation:
        abort(
            status.HTTP_404_NOT_FOUND,
            f"Recommendation with id '{recommendation_id}' was not found.",
        )
    recommendation.like_count += 1
    recommendation.update()
    return recommendation.serialize()


######################################################################
# HEALTH CHECK
######################################################################
@health_ns.route("/", strict_slashes=False)
class HealthCheck(Resource):
    """Health check endpoint"""

    @health_ns.doc("health_check")
    @health_ns.response(200, "Service is healthy")
    def get(self):
        """Returns service health status"""
        return {"status": "OK"}


######################################################################
# RECOMMENDATIONS COLLECTION - LIST & CREATE
######################################################################
@ns.route("/", strict_slashes=False)
class RecommendationList(Resource):
    """Handles the /recommendations collection"""

    @ns.doc("list_recommendations")
    @ns.param("product_id", "Filter by source product ID", type=int)
    @ns.param("recommended_product_id", "Filter by recommended product ID", type=int)
    @ns.param(
        "recommendation_type",
        "Filter by type: cross_sell | up_sell | accessory | similar_item",
    )
    @ns.param("page", "Page number (10 results per page)", type=int)
    @ns.response(200, "Success")
    def get(self):
        """List all Recommendations with optional filtering and pagination"""
        return list_recommendations()

    @ns.doc("create_recommendation")
    @ns.expect(create_model, validate=False)
    @ns.response(201, "Recommendation created", recommendation_model)
    @ns.response(400, "Bad Request", error_model)
    @ns.response(415, "Unsupported Media Type", error_model)
    def post(self):
        """Create a new Recommendation"""
        return create_recommendation("/api/recommendations")


######################################################################
# SINGLE RECOMMENDATION - READ, UPDATE, DELETE
######################################################################
@ns.route("/<int:recommendation_id>", strict_slashes=False)
@ns.param("recommendation_id", "The recommendation identifier")
class RecommendationResource(Resource):
    """Handles /recommendations/{id} endpoints"""

    @ns.doc("get_recommendation")
    @ns.response(200, "Success", recommendation_model)
    @ns.response(404, "Not Found", error_model)
    def get(self, recommendation_id):
        """Retrieve a single Recommendation by its ID"""
        return get_recommendation(recommendation_id)

    @ns.doc("update_recommendation")
    @ns.expect(create_model, validate=False)
    @ns.response(200, "Success", recommendation_model)
    @ns.response(400, "Bad Request", error_model)
    @ns.response(404, "Not Found", error_model)
    @ns.response(415, "Unsupported Media Type", error_model)
    def put(self, recommendation_id):
        """Update a Recommendation by its ID"""
        return update_recommendation(recommendation_id)

    @ns.doc("delete_recommendation")
    @ns.response(204, "Recommendation deleted")
    def delete(self, recommendation_id):
        """Delete a Recommendation by its ID"""
        return delete_recommendation(recommendation_id)


######################################################################
# ACTIVATE ACTION
######################################################################
@ns.route("/<int:recommendation_id>/activate", strict_slashes=False)
@ns.param("recommendation_id", "The recommendation identifier")
class RecommendationActivate(Resource):
    """Handles the /recommendations/{id}/activate action endpoint"""

    @ns.doc("activate_recommendation")
    @ns.response(200, "Recommendation activated", recommendation_model)
    @ns.response(404, "Not Found", error_model)
    def put(self, recommendation_id):
        """Mark a Recommendation as active"""
        return activate_recommendation(recommendation_id)


######################################################################
# DEACTIVATE ACTION
######################################################################
@ns.route("/<int:recommendation_id>/deactivate", strict_slashes=False)
@ns.param("recommendation_id", "The recommendation identifier")
class RecommendationDeactivate(Resource):
    """Handles the /recommendations/{id}/deactivate action endpoint"""

    @ns.doc("deactivate_recommendation")
    @ns.response(200, "Recommendation deactivated", recommendation_model)
    @ns.response(404, "Not Found", error_model)
    def put(self, recommendation_id):
        """Mark a Recommendation as inactive"""
        return deactivate_recommendation(recommendation_id)


######################################################################
# LIKE ACTION
######################################################################
@ns.route("/<int:recommendation_id>/like", strict_slashes=False)
@ns.param("recommendation_id", "The recommendation identifier")
class RecommendationLike(Resource):
    """Handles the /recommendations/{id}/like action endpoint"""

    @ns.doc("like_recommendation")
    @ns.response(200, "Like recorded", recommendation_model)
    @ns.response(404, "Not Found", error_model)
    def put(self, recommendation_id):
        """Increment the like count for a Recommendation"""
        return like_recommendation(recommendation_id)


######################################################################
# INDEX ROUTE (Web UI)
######################################################################
def init_index_route(app_instance):
    """Register the web management UI at /"""

    @app_instance.route("/")
    def index():  # pylint: disable=unused-variable
        """Serve the web management UI"""
        return app_instance.send_static_file("index.html")


def init_compatibility_routes(app_instance):  # noqa: C901
    """Register compatibility routes required by the course tests."""

    @app_instance.route("/apiIndex", strict_slashes=False)
    def api_index_alias():  # pylint: disable=unused-variable
        """List the API version, documentation, and callable endpoints."""
        return api_index_payload()

    @app_instance.route("/apidocs/", strict_slashes=False)
    def apidocs_redirect():  # pylint: disable=unused-variable
        """Support the homework-required /apidocs/ URL."""
        return redirect("/apidocs", code=status.HTTP_302_FOUND)

    @app_instance.route("/health", strict_slashes=False)
    @app_instance.route(f"{BASE_PATH}/health", strict_slashes=False)
    @app_instance.route(f"{LEGACY_BASE_PATH}/health", strict_slashes=False)
    def health_alias():  # pylint: disable=unused-variable
        """Health check aliases."""
        return {"status": "OK"}

    @app_instance.route("/recommendations", methods=["GET"], strict_slashes=False)
    @app_instance.route(
        f"{LEGACY_BASE_PATH}/recommendations", methods=["GET"], strict_slashes=False
    )
    def recommendations_list_alias():  # pylint: disable=unused-variable
        """List Recommendations via compatibility routes."""
        return list_recommendations()

    @app_instance.route("/recommendations", methods=["POST"], strict_slashes=False)
    @app_instance.route(
        f"{LEGACY_BASE_PATH}/recommendations", methods=["POST"], strict_slashes=False
    )
    def recommendations_create_alias():  # pylint: disable=unused-variable
        """Create a Recommendation via compatibility routes."""
        location_base = request.path.rstrip("/")
        return create_recommendation(location_base)

    @app_instance.route(
        "/recommendations/<int:recommendation_id>",
        methods=["GET", "PUT", "DELETE"],
        strict_slashes=False,
    )
    @app_instance.route(
        f"{LEGACY_BASE_PATH}/recommendations/<int:recommendation_id>",
        methods=["GET", "PUT", "DELETE"],
        strict_slashes=False,
    )
    def recommendation_resource_alias(recommendation_id):  # pylint: disable=unused-variable
        """Handle a Recommendation via compatibility routes."""
        if request.method == "GET":
            return get_recommendation(recommendation_id)
        if request.method == "PUT":
            return update_recommendation(recommendation_id)
        return delete_recommendation(recommendation_id)

    @app_instance.route(
        "/recommendations/<int:recommendation_id>/activate",
        methods=["PUT"],
        strict_slashes=False,
    )
    @app_instance.route(
        f"{LEGACY_BASE_PATH}/recommendations/<int:recommendation_id>/activate",
        methods=["PUT"],
        strict_slashes=False,
    )
    def activate_alias(recommendation_id):  # pylint: disable=unused-variable
        """Activate a Recommendation via compatibility routes."""
        return activate_recommendation(recommendation_id)

    @app_instance.route(
        "/recommendations/<int:recommendation_id>/deactivate",
        methods=["PUT"],
        strict_slashes=False,
    )
    @app_instance.route(
        f"{LEGACY_BASE_PATH}/recommendations/<int:recommendation_id>/deactivate",
        methods=["PUT"],
        strict_slashes=False,
    )
    def deactivate_alias(recommendation_id):  # pylint: disable=unused-variable
        """Deactivate a Recommendation via compatibility routes."""
        return deactivate_recommendation(recommendation_id)

    @app_instance.route(
        "/recommendations/<int:recommendation_id>/like",
        methods=["PUT"],
        strict_slashes=False,
    )
    @app_instance.route(
        f"{LEGACY_BASE_PATH}/recommendations/<int:recommendation_id>/like",
        methods=["PUT"],
        strict_slashes=False,
    )
    def like_alias(recommendation_id):  # pylint: disable=unused-variable
        """Like a Recommendation via compatibility routes."""
        return like_recommendation(recommendation_id)
