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
from flask import abort, request
from flask_restx import Api, Resource, fields
from werkzeug.exceptions import (
    BadRequest,
    NotFound,
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
    api_prefix = _normalize_prefix(os.getenv("API_PREFIX", "/api/recommendations"))
    api_version = _normalize_version(os.getenv("API_VERSION", "v1"))
    return f"{api_prefix}/{api_version}" if api_version else api_prefix


ENV_NAME = os.getenv("ENV", "local")
BASE_PATH = _build_base_path()
SERVICE_NAME = "recommendation"


######################################################################
# Flask-RESTX API
######################################################################
api = Api(
    version="1.0",
    title="Recommendation API",
    description="A RESTful microservice for managing product recommendations",
    prefix=BASE_PATH,
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
            query = query.filter(
                Recommendation.recommendation_type == recommendation_type
            )

        if page is not None:
            pagination = query.paginate(page=page, per_page=10, error_out=False)
            recommendations = pagination.items
        else:
            recommendations = query.all()

        results = [r.serialize() for r in recommendations]
        return results

    @ns.doc("create_recommendation")
    @ns.expect(create_model, validate=False)
    @ns.response(201, "Recommendation created", recommendation_model)
    @ns.response(400, "Bad Request", error_model)
    @ns.response(415, "Unsupported Media Type", error_model)
    def post(self):
        """Create a new Recommendation"""
        check_content_type("application/json")
        recommendation = Recommendation()
        recommendation.deserialize(request.get_json())
        recommendation.create()
        message = recommendation.serialize()
        location_url = f"{BASE_PATH}/recommendations/{recommendation.id}"
        return message, status.HTTP_201_CREATED, {"Location": location_url}


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
        recommendation = Recommendation.find(recommendation_id)
        if not recommendation:
            abort(
                status.HTTP_404_NOT_FOUND,
                f"Recommendation with id '{recommendation_id}' was not found.",
            )
        return recommendation.serialize()

    @ns.doc("update_recommendation")
    @ns.expect(create_model, validate=False)
    @ns.response(200, "Success", recommendation_model)
    @ns.response(400, "Bad Request", error_model)
    @ns.response(404, "Not Found", error_model)
    @ns.response(415, "Unsupported Media Type", error_model)
    def put(self, recommendation_id):
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

    @ns.doc("delete_recommendation")
    @ns.response(204, "Recommendation deleted")
    @ns.response(404, "Not Found", error_model)
    def delete(self, recommendation_id):
        """Delete a Recommendation by its ID"""
        recommendation = Recommendation.find(recommendation_id)
        if not recommendation:
            abort(
                status.HTTP_404_NOT_FOUND,
                f"Recommendation with id '{recommendation_id}' was not found.",
            )
        recommendation.delete()
        return "", status.HTTP_204_NO_CONTENT


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
        recommendation = Recommendation.find(recommendation_id)
        if not recommendation:
            abort(
                status.HTTP_404_NOT_FOUND,
                f"Recommendation with id '{recommendation_id}' was not found.",
            )
        recommendation.active = True
        recommendation.update()
        return recommendation.serialize()


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
        recommendation = Recommendation.find(recommendation_id)
        if not recommendation:
            abort(
                status.HTTP_404_NOT_FOUND,
                f"Recommendation with id '{recommendation_id}' was not found.",
            )
        recommendation.active = False
        recommendation.update()
        return recommendation.serialize()


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
# INDEX ROUTE (Web UI)
######################################################################
def init_index_route(app_instance):
    """Register the web management UI at /"""

    @app_instance.route("/")
    def index():  # pylint: disable=unused-variable
        """Serve the web management UI"""
        return app_instance.send_static_file("index.html")
