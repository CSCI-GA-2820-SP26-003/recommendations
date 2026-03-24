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
YourResourceModel Service

This service implements a REST API that allows you to Create, Read, Update
and Delete YourResourceModel
"""

import os
from flask import abort, jsonify, request
from flask import current_app as app  # Import Flask application
from service.common import status  # HTTP Status Codes
from service.models import Recommendation


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

app.logger.info(
    "Route config: env=%s api_prefix=%s api_version=%s base_path=%s",
    ENV_NAME,
    os.getenv("API_PREFIX", "/api/recommendations"),
    os.getenv("API_VERSION", "v1"),
    BASE_PATH,
)


######################################################################
# GET INDEX
######################################################################
@app.route("/")
def index():
    """Root URL response"""
    app.logger.info("GET /")
    return (
        jsonify(
            service=SERVICE_NAME,
            env=ENV_NAME,
            base_path=BASE_PATH,
            endpoints=[
                f"{BASE_PATH}/health",
                f"{BASE_PATH}/recommendations",
                f"{BASE_PATH}/recommendations/{{id}}",
            ],
        ),
        status.HTTP_200_OK,
    )


######################################################################
# GET HEALTH
######################################################################
@app.route(f"{BASE_PATH}/health", methods=["GET"])
def health():
    """Health check endpoint"""
    app.logger.info("GET %s/health", BASE_PATH)
    return (
        jsonify(
            status="ok",
            service=SERVICE_NAME,
            env=ENV_NAME,
            base_path=BASE_PATH,
        ),
        status.HTTP_200_OK,
    )


######################################################################
#  R E S T   A P I   E N D P O I N T S
######################################################################


######################################################################
# HELPER
######################################################################
def check_content_type(content_type):
    """Checks that the media type is correct"""
    if "Content-Type" not in request.headers:
        app.logger.error("No Content-Type specified.")
        abort(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Content-Type must be {content_type}",
        )
    if request.headers["Content-Type"] == content_type:
        return
    app.logger.error("Invalid Content-Type: %s", request.headers["Content-Type"])
    abort(
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        f"Content-Type must be {content_type}",
    )


######################################################################
# LIST ALL RECOMMENDATIONS
######################################################################
@app.route(f"{BASE_PATH}/recommendations", methods=["GET"])
def list_recommendations():
    """Returns Recommendations filtered by optional query params, with optional ?page=N pagination (10 per page)"""
    app.logger.info("GET %s/recommendations", BASE_PATH)
    product_id = request.args.get("product_id", type=int)
    recommendation_type = request.args.get("recommendation_type")
    page = request.args.get("page", type=int)

    query = Recommendation.query
    if product_id is not None:
        query = query.filter(Recommendation.product_id == product_id)
    if recommendation_type is not None:
        query = query.filter(Recommendation.recommendation_type == recommendation_type)

    if page is not None:
        pagination = query.paginate(page=page, per_page=10, error_out=False)
        recommendations = pagination.items
    else:
        recommendations = query.all()
    results = [r.serialize() for r in recommendations]
    app.logger.info("Returning %d recommendations", len(results))
    return jsonify(results), status.HTTP_200_OK


######################################################################
# CREATE A RECOMMENDATION
######################################################################
@app.route(f"{BASE_PATH}/recommendations", methods=["POST"])
def create_recommendation():
    """Creates a new Recommendation"""
    app.logger.info("POST %s/recommendations", BASE_PATH)
    check_content_type("application/json")
    recommendation = Recommendation()
    recommendation.deserialize(request.get_json())
    recommendation.create()
    message = recommendation.serialize()
    location_url = f"{BASE_PATH}/recommendations/{recommendation.id}"
    app.logger.info("Recommendation with id [%s] created", recommendation.id)
    return jsonify(message), status.HTTP_201_CREATED, {"Location": location_url}


######################################################################
# READ A RECOMMENDATION
######################################################################
@app.route(f"{BASE_PATH}/recommendations/<int:recommendation_id>", methods=["GET"])
def get_recommendation(recommendation_id):
    """Retrieve a single Recommendation by its id"""
    app.logger.info("GET %s/recommendations/%s", BASE_PATH, recommendation_id)
    recommendation = Recommendation.find(recommendation_id)
    if not recommendation:
        abort(
            status.HTTP_404_NOT_FOUND,
            f"Recommendation with id '{recommendation_id}' was not found.",
        )
    return jsonify(recommendation.serialize()), status.HTTP_200_OK


######################################################################
# DELETE A RECOMMENDATION
######################################################################
@app.route(f"{BASE_PATH}/recommendations/<int:recommendation_id>", methods=["DELETE"])
def delete_recommendation(recommendation_id):
    """Delete a Recommendation by its id"""
    app.logger.info("DELETE %s/recommendations/%s", BASE_PATH, recommendation_id)
    recommendation = Recommendation.find(recommendation_id)
    if not recommendation:
        abort(
            status.HTTP_404_NOT_FOUND,
            f"Recommendation with id '{recommendation_id}' was not found.",
        )
    recommendation.delete()
    return "", status.HTTP_204_NO_CONTENT


######################################################################
# UPDATE A RECOMMENDATION
######################################################################
@app.route(f"{BASE_PATH}/recommendations/<int:recommendation_id>", methods=["PUT"])
def update_recommendation(recommendation_id):
    """Updates a Recommendation by its ID"""
    app.logger.info("PUT %s/recommendations/%s", BASE_PATH, recommendation_id)
    check_content_type("application/json")

    recommendation = Recommendation.find(recommendation_id)
    if not recommendation:
        abort(
            status.HTTP_404_NOT_FOUND,
            f"Recommendation with id '{recommendation_id}' was not found.",
        )

    data = request.get_json()
    recommendation.deserialize(data)
    recommendation.update()

    app.logger.info("Recommendation with id [%s] updated", recommendation_id)
    return jsonify(recommendation.serialize()), status.HTTP_200_OK
