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
TestYourResourceModel API Service Test Suite
"""

# pylint: disable=duplicate-code,reimported,redefined-outer-name,too-many-lines
import os
import sys
import logging
from unittest import TestCase
from unittest.mock import patch
from werkzeug.exceptions import (
    BadRequest,
    Conflict,
    InternalServerError,
    MethodNotAllowed,
    NotFound,
    UnsupportedMediaType,
)
from wsgi import app
from service import create_app, routes
from service.models import DataValidationError, Recommendation, db
from service.common import status
from tests.factories import RecommendationFactory

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql+psycopg://postgres:postgres@localhost:5432/postgres"
)


######################################################################
#  T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestYourResourceService(TestCase):
    """REST API Server Tests"""

    @classmethod
    def setUpClass(cls):
        """This runs once before the entire test suite"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        app.app_context().push()

    @classmethod
    def tearDownClass(cls):
        """This runs once after the entire test suite"""
        db.session.close()

    def setUp(self):
        """This runs before each test"""
        db.session.query(Recommendation).delete()
        db.session.commit()

    def tearDown(self):
        """This runs after each test"""
        db.session.remove()

    def _create_test_client(self, env_overrides=None):
        """Create an app client with temporary ENV/API_PREFIX/API_VERSION values"""
        test_env = {
            "ENV": "local",
            "API_PREFIX": "/api/recommendations",
            "API_VERSION": "v1",
        }
        if env_overrides:
            test_env.update(env_overrides)

        env_patcher = patch.dict(os.environ, test_env, clear=False)
        env_patcher.start()
        self.addCleanup(env_patcher.stop)

        # Fully clear app modules so decorators register on a fresh Flask app
        for module_name in list(sys.modules):
            if module_name == "wsgi" or module_name.startswith("service"):
                sys.modules.pop(module_name, None)

        # pylint: disable=import-outside-toplevel
        import wsgi

        test_app = wsgi.app
        test_app.config["TESTING"] = True
        test_app.config["DEBUG"] = False
        test_app.logger.setLevel(logging.CRITICAL)
        return test_app.test_client()

    ######################################################################
    #  T E S T   C A S E S
    ######################################################################

    def test_index_returns_admin_ui(self):
        """It should return the admin UI HTML page from GET /"""
        client = self._create_test_client()

        resp = client.get("/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("text/html", resp.content_type)
        self.assertIn(b"Recommendations Admin", resp.data)

    def test_health_returns_ok_json(self):
        """It should return HTTP 200 JSON on GET {BASE_PATH}/health"""
        client = self._create_test_client()

        resp = client.get("/api/recommendations/v1/health")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.content_type.startswith("application/json"))
        self.assertEqual(resp.get_json(), {"status": "OK"})

    def test_env_vars_change_route_base_path(self):
        """It should build route paths from ENV/API_PREFIX/API_VERSION"""
        client = self._create_test_client(
            {
                "ENV": "staging",
                "API_PREFIX": "/api/reco",
                "API_VERSION": "",
            }
        )

        resp = client.get("/api/reco/health")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.content_type.startswith("application/json"))
        self.assertEqual(resp.get_json(), {"status": "OK"})

    def test_prefix_without_leading_slash_is_normalized(self):
        """It should normalize API_PREFIX when leading slash is missing"""
        client = self._create_test_client(
            {
                "API_PREFIX": "api/reco",
                "API_VERSION": "v2",
            }
        )

        resp = client.get("/api/reco/v2/health")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.get_json(), {"status": "OK"})

    def test_blank_prefix_falls_back_to_default(self):
        """It should fallback to default API_PREFIX when configured value is blank"""
        client = self._create_test_client(
            {
                "API_PREFIX": "   ",
                "API_VERSION": "v1",
            }
        )

        resp = client.get("/api/recommendations/v1/health")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.get_json(), {"status": "OK"})

    def test_not_found_returns_json(self):
        """It should return JSON for 404 errors"""
        client = self._create_test_client()

        resp = client.get("/missing")

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(resp.content_type.startswith("application/json"))
        data = resp.get_json()
        self.assertEqual(data["error"], "Not Found")
        self.assertIn("message", data)

    def test_method_not_allowed_returns_json(self):
        """It should return JSON for 405 errors"""
        client = self._create_test_client()

        resp = client.post("/api/recommendations/v1/health/")

        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertTrue(resp.content_type.startswith("application/json"))
        data = resp.get_json()
        self.assertEqual(data["error"], "Method not Allowed")
        self.assertIn("message", data)

    def test_unsupported_media_type_returns_json(self):
        """It should return JSON for 415 errors"""
        resp = app.test_client().post(
            f"{BASE_PATH}/recommendations",
            data="not json",
            content_type="text/plain",
        )
        self.assertEqual(resp.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
        self.assertTrue(resp.content_type.startswith("application/json"))
        data = resp.get_json()
        self.assertEqual(data["error"], "Unsupported media type")
        self.assertIn("message", data)

    def test_conflict_returns_json(self):
        """It should return JSON for 409 Conflict errors"""
        client = self._create_test_client()
        with patch(
            "service.routes.Recommendation.find",
            side_effect=Conflict("Resource conflict"),
        ):
            resp = client.get("/api/recommendations/v1/recommendations/1")
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)
        self.assertTrue(resp.content_type.startswith("application/json"))
        data = resp.get_json()
        self.assertEqual(data["error"], "Conflict")
        self.assertIn("message", data)

    def test_internal_server_error_returns_json(self):
        """It should return JSON for 500 Internal Server Error responses"""
        client = self._create_test_client()
        with patch(
            "service.routes.Recommendation.find",
            side_effect=InternalServerError("Server failure"),
        ):
            resp = client.get("/api/recommendations/v1/recommendations/1")
        self.assertEqual(resp.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertTrue(resp.content_type.startswith("application/json"))
        data = resp.get_json()
        self.assertEqual(data["error"], "Internal Server Error")
        self.assertIn("message", data)

    def test_bad_request_returns_json(self):
        """It should return JSON for 400 errors with proper structure"""
        payload = {
            "recommended_product_id": 2,
            "recommendation_type": "cross_sell",
        }
        resp = app.test_client().post(
            f"{BASE_PATH}/recommendations",
            json=payload,
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(resp.content_type.startswith("application/json"))
        data = resp.get_json()
        self.assertIn("message", data)

    def test_create_app_exits_when_database_initialization_fails(self):
        """It should exit with code 4 when database initialization fails"""
        with patch(
            "service.models.db.create_all",
            side_effect=Exception("database unavailable"),
        ):
            with self.assertRaises(SystemExit) as error:
                create_app()

        self.assertEqual(error.exception.code, 4)

    def test_restx_error_handlers(self):
        """It should return structured payloads from Flask-RESTX handlers"""
        handlers = [
            (
                routes.handle_validation_error,
                DataValidationError("bad data"),
                status.HTTP_400_BAD_REQUEST,
                "Bad Request",
            ),
            (
                routes.handle_bad_request,
                BadRequest("bad request"),
                status.HTTP_400_BAD_REQUEST,
                "Bad Request",
            ),
            (
                routes.handle_not_found,
                NotFound("missing"),
                status.HTTP_404_NOT_FOUND,
                "Not Found",
            ),
            (
                routes.handle_method_not_allowed,
                MethodNotAllowed(valid_methods=["GET"]),
                status.HTTP_405_METHOD_NOT_ALLOWED,
                "Method not Allowed",
            ),
            (
                routes.handle_conflict,
                Conflict("conflict"),
                status.HTTP_409_CONFLICT,
                "Conflict",
            ),
            (
                routes.handle_unsupported_media,
                UnsupportedMediaType("wrong media"),
                status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                "Unsupported media type",
            ),
            (
                routes.handle_internal_error,
                InternalServerError("server error"),
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "Internal Server Error",
            ),
        ]

        for handler, error, expected_status, expected_error in handlers:
            payload, http_status = handler(error)
            self.assertEqual(http_status, expected_status)
            self.assertEqual(payload["status"], expected_status)
            self.assertEqual(payload["error"], expected_error)
            self.assertIn("message", payload)

    def test_get_recommendation(self):
        """It should read a single recommendation"""
        rec = RecommendationFactory()
        rec.create()
        resp = app.test_client().get(
            f"/api/recommendations/v1/recommendations/{rec.id}"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.content_type.startswith("application/json"))
        data = resp.get_json()
        self.assertEqual(data["id"], rec.id)
        self.assertEqual(data["product_id"], rec.product_id)
        self.assertEqual(data["recommended_product_id"], rec.recommended_product_id)
        self.assertEqual(data["recommendation_type"], rec.recommendation_type)
        self.assertTrue(data["active"])

    def test_get_recommendation_not_found(self):
        """It should return 404 for a recommendation that doesn't exist"""
        resp = app.test_client().get(
            "/api/recommendations/v1/recommendations/0"
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(resp.content_type.startswith("application/json"))
        data = resp.get_json()
        self.assertIn("message", data)

    def test_delete_recommendation(self):
        """It should delete a recommendation"""
        rec = RecommendationFactory()
        rec.create()
        # Verify it exists
        self.assertIsNotNone(Recommendation.find(rec.id))
        # Delete it
        resp = app.test_client().delete(
            f"/api/recommendations/v1/recommendations/{rec.id}"
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(resp.get_data(as_text=True), "")
        # Verify it's gone
        self.assertIsNone(Recommendation.find(rec.id))

    def test_delete_recommendation_not_found(self):
        """It should return 204 when deleting a non-existent recommendation"""
        resp = app.test_client().delete(
            "/api/recommendations/v1/recommendations/0"
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(resp.get_data(as_text=True), "")

    def test_apidocs_trailing_slash_redirects(self):
        """It should support the homework-required /apidocs/ URL"""
        resp = app.test_client().get("/apidocs/")

        self.assertEqual(resp.status_code, status.HTTP_302_FOUND)
        self.assertIn("/apidocs", resp.headers.get("Location", ""))

    def test_api_index_lists_callable_endpoints(self):
        """It should list API version, docs, and callable endpoints from /apiIndex"""
        resp = app.test_client().get("/apiIndex")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.content_type.startswith("application/json"))
        data = resp.get_json()
        self.assertEqual(data["service"], "recommendation")
        self.assertEqual(data["version"], "1.0")
        self.assertEqual(data["documentation"], "/apidocs/")
        self.assertEqual(data["canonical_base_path"], "/recommendations")
        self.assertIn("canonical", data["endpoints"])
        self.assertIn("flask_restx", data["endpoints"])
        self.assertIn("legacy", data["endpoints"])
        canonical_paths = {
            endpoint["path"] for endpoint in data["endpoints"]["canonical"]
        }
        self.assertIn("/recommendations", canonical_paths)
        self.assertIn("/recommendations/{id}", canonical_paths)
        self.assertIn("/recommendations/{id}/activate", canonical_paths)

    def test_canonical_list_recommendations(self):
        """It should list Recommendations from GET /recommendations"""
        RecommendationFactory().create()

        resp = app.test_client().get("/recommendations")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), 1)

    def test_canonical_create_recommendation(self):
        """It should create Recommendations from POST /recommendations"""
        payload = {
            "product_id": 1,
            "recommended_product_id": 2,
            "recommendation_type": "cross_sell",
            "score": 0.85,
        }

        resp = app.test_client().post(
            "/recommendations",
            json=payload,
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn("/recommendations/", resp.headers.get("Location", ""))
        self.assertEqual(resp.get_json()["product_id"], 1)

    def test_canonical_delete_missing_is_idempotent(self):
        """It should return 204 when DELETE /recommendations/{id} is missing"""
        resp = app.test_client().delete("/recommendations/0")

        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(resp.get_data(as_text=True), "")

    def test_restx_primary_routes(self):
        """It should support the Flask-RESTX /api/recommendations routes"""
        client = app.test_client()
        payload = {
            "product_id": 10,
            "recommended_product_id": 20,
            "recommendation_type": "up_sell",
            "score": 0.75,
        }

        resp = client.get("/api/health/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.get_json(), {"status": "OK"})

        resp = client.post(
            "/api/recommendations",
            json=payload,
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        rec_id = resp.get_json()["id"]

        resp = client.get("/api/recommendations")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.get_json()), 1)

        resp = client.get(f"/api/recommendations/{rec_id}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.get_json()["product_id"], 10)

        payload["score"] = 0.95
        resp = client.put(
            f"/api/recommendations/{rec_id}",
            json=payload,
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.get_json()["score"], 0.95)

        resp = client.put(f"/api/recommendations/{rec_id}/deactivate")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.get_json()["active"])

        resp = client.put(f"/api/recommendations/{rec_id}/activate")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.get_json()["active"])

        resp = client.put(f"/api/recommendations/{rec_id}/like")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.get_json()["like_count"], 1)

        resp = client.delete(f"/api/recommendations/{rec_id}")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)


######################################################################
#  H E L P E R S
######################################################################
BASE_PATH = "/api/recommendations/v1"


def _fresh_app():
    """Clear service modules and return a freshly imported app with default env vars."""
    os.environ.setdefault("API_PREFIX", "/api/recommendations")
    os.environ.setdefault("API_VERSION", "v1")
    os.environ.setdefault("ENV", "local")
    for mod in list(sys.modules):
        if mod == "wsgi" or mod.startswith("service"):
            sys.modules.pop(mod, None)
    import wsgi  # pylint: disable=import-outside-toplevel
    wsgi.app.config["TESTING"] = True
    wsgi.app.config["DEBUG"] = False
    wsgi.app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
    wsgi.app.logger.setLevel(logging.CRITICAL)
    return wsgi.app


######################################################################
#  T E S T   C R E A T E   R E C O M M E N D A T I O N
######################################################################
class TestCreateRecommendation(TestCase):
    """Tests for POST /api/recommendations/v1/recommendations"""

    @classmethod
    def setUpClass(cls):
        """This runs once before the entire test suite"""
        cls.app = _fresh_app()
        cls.client = cls.app.test_client()
        cls._ctx = cls.app.app_context()
        cls._ctx.push()

    @classmethod
    def tearDownClass(cls):
        """This runs once after the entire test suite"""
        from service.models import db  # pylint: disable=import-outside-toplevel
        db.session.close()
        cls._ctx.pop()

    def setUp(self):
        """This runs before each test"""
        from service.models import db, Recommendation  # pylint: disable=import-outside-toplevel
        db.session.query(Recommendation).delete()
        db.session.commit()

    def tearDown(self):
        """This runs after each test"""
        from service.models import db  # pylint: disable=import-outside-toplevel
        db.session.remove()

    # ------------------------------------------------------------------
    # Happy paths
    # ------------------------------------------------------------------

    def test_create_recommendation(self):
        """It should create a new Recommendation and return 201"""
        payload = {
            "product_id": 1,
            "recommended_product_id": 2,
            "recommendation_type": "cross_sell",
            "score": 0.85,
        }
        resp = self.client.post(
            f"{BASE_PATH}/recommendations",
            json=payload,
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        location = resp.headers.get("Location", "")
        self.assertIn(f"{BASE_PATH}/recommendations/", location)
        data = resp.get_json()
        self.assertIsNotNone(data["id"])
        self.assertEqual(data["product_id"], 1)
        self.assertEqual(data["recommended_product_id"], 2)
        self.assertEqual(data["recommendation_type"], "cross_sell")
        self.assertEqual(data["score"], 0.85)

    def test_create_recommendation_without_score(self):
        """It should create a Recommendation when score is omitted"""
        payload = {
            "product_id": 10,
            "recommended_product_id": 20,
            "recommendation_type": "up_sell",
        }
        resp = self.client.post(
            f"{BASE_PATH}/recommendations",
            json=payload,
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        data = resp.get_json()
        self.assertIsNone(data["score"])

    # ------------------------------------------------------------------
    # Sad paths
    # ------------------------------------------------------------------

    def test_create_recommendation_no_content_type(self):
        """It should return 415 when Content-Type header is missing"""
        resp = self.client.post(
            f"{BASE_PATH}/recommendations",
            data='{"product_id": 1, "recommended_product_id": 2,'
                 ' "recommendation_type": "cross_sell"}',
        )
        self.assertEqual(resp.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_create_recommendation_wrong_content_type(self):
        """It should return 415 when Content-Type is not application/json"""
        resp = self.client.post(
            f"{BASE_PATH}/recommendations",
            data="product_id=1",
            content_type="text/plain",
        )
        self.assertEqual(resp.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_create_recommendation_missing_field(self):
        """It should return 400 when a required field is missing"""
        payload = {
            "recommended_product_id": 2,
            "recommendation_type": "cross_sell",
        }
        resp = self.client.post(
            f"{BASE_PATH}/recommendations",
            json=payload,
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_recommendation_invalid_type(self):
        """It should return 400 when recommendation_type is not a valid value"""
        payload = {
            "product_id": 1,
            "recommended_product_id": 2,
            "recommendation_type": "not_a_real_type",
            "score": 0.5,
        }
        resp = self.client.post(
            f"{BASE_PATH}/recommendations",
            json=payload,
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_recommendation_same_product_ids(self):
        """It should return 400 when product_id equals recommended_product_id"""
        payload = {
            "product_id": 5,
            "recommended_product_id": 5,
            "recommendation_type": "up_sell",
            "score": 0.5,
        }
        resp = self.client.post(
            f"{BASE_PATH}/recommendations",
            json=payload,
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_recommendation_malformed_json(self):
        """It should return 400 when request body contains malformed JSON"""
        resp = self.client.post(
            f"{BASE_PATH}/recommendations",
            data='{"product_id": 1, "recommended_product_id": 2,',
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(resp.content_type.startswith("application/json"))
        data = resp.get_json()
        self.assertIn("message", data)

    def test_create_recommendation_empty_json_body(self):
        """It should return 400 when request body is empty JSON payload"""
        resp = self.client.post(
            f"{BASE_PATH}/recommendations",
            data="",
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(resp.content_type.startswith("application/json"))
        data = resp.get_json()
        self.assertIn("message", data)


######################################################################
#  T E S T   L I S T   R E C O M M E N D A T I O N S
######################################################################
class TestListRecommendations(TestCase):
    """Tests for GET /api/recommendations/v1/recommendations"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        app.app_context().push()

    @classmethod
    def tearDownClass(cls):
        """Run once after all tests"""
        db.session.close()

    def setUp(self):
        """Run before each test"""
        db.session.query(Recommendation).delete()
        db.session.commit()
        self.client = app.test_client()

    def tearDown(self):
        """Run after each test"""
        db.session.remove()

    # ------------------------------------------------------------------
    # Happy paths
    # ------------------------------------------------------------------

    def test_list_recommendations_empty(self):
        """It should return an empty list when no recommendations exist"""
        resp = self.client.get(f"{BASE_PATH}/recommendations")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.content_type.startswith("application/json"))
        self.assertEqual(resp.get_json(), [])

    def test_list_all_recommendations(self):
        """It should return all recommendations when no pagination is specified"""
        for _ in range(3):
            RecommendationFactory().create()
        resp = self.client.get(f"{BASE_PATH}/recommendations")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), 3)

    def test_list_recommendations_page_1(self):
        """It should return up to 10 records for page=1"""
        for _ in range(15):
            RecommendationFactory().create()
        resp = self.client.get(f"{BASE_PATH}/recommendations?page=1")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), 10)

    def test_list_recommendations_page_2(self):
        """It should return remaining records on page 2"""
        for _ in range(15):
            RecommendationFactory().create()
        resp = self.client.get(f"{BASE_PATH}/recommendations?page=2")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), 5)

    # ------------------------------------------------------------------
    # Sad paths
    # ------------------------------------------------------------------

    def test_list_recommendations_empty_page(self):
        """It should return an empty list for a page beyond available data"""
        resp = self.client.get(f"{BASE_PATH}/recommendations?page=999")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.get_json(), [])

    # ------------------------------------------------------------------
    # Query by attribute
    # ------------------------------------------------------------------

    def test_query_by_product_id(self):
        """It should return only recommendations matching the given product_id"""
        target = RecommendationFactory.build(
            product_id=9001, recommended_product_id=9002
        )
        target.create()
        RecommendationFactory.build(
            product_id=1111, recommended_product_id=2222
        ).create()

        resp = self.client.get(f"{BASE_PATH}/recommendations?product_id=9001")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["product_id"], 9001)

    def test_query_by_recommendation_type(self):
        """It should return only recommendations matching the recommendation_type"""
        RecommendationFactory.build(
            product_id=101, recommended_product_id=201, recommendation_type="cross_sell"
        ).create()
        RecommendationFactory.build(
            product_id=102, recommended_product_id=202, recommendation_type="up_sell"
        ).create()
        RecommendationFactory.build(
            product_id=103, recommended_product_id=203, recommendation_type="up_sell"
        ).create()

        resp = self.client.get(
            f"{BASE_PATH}/recommendations?recommendation_type=up_sell"
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), 2)
        for item in data:
            self.assertEqual(item["recommendation_type"], "up_sell")

    def test_query_by_product_id_no_match(self):
        """It should return an empty list when no recommendations match the product_id"""
        RecommendationFactory().create()

        resp = self.client.get(f"{BASE_PATH}/recommendations?product_id=99999")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.get_json(), [])

    def test_query_combined_product_id_and_type(self):
        """It should filter recommendations by both product_id and type"""
        RecommendationFactory.build(
            product_id=555, recommended_product_id=666, recommendation_type="accessory"
        ).create()
        RecommendationFactory.build(
            product_id=555, recommended_product_id=777, recommendation_type="cross_sell"
        ).create()
        RecommendationFactory.build(
            product_id=444, recommended_product_id=888, recommendation_type="accessory"
        ).create()

        resp = self.client.get(
            f"{BASE_PATH}/recommendations?product_id=555&recommendation_type=accessory"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["product_id"], 555)
        self.assertEqual(data[0]["recommendation_type"], "accessory")

    def test_query_by_invalid_recommendation_type(self):
        """It should return 400 for an invalid recommendation_type"""
        resp = self.client.get(
            f"{BASE_PATH}/recommendations?recommendation_type=invalid"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


######################################################################
#  T E S T   U P D A T E   R E C O M M E N D A T I O N
######################################################################
class TestUpdateRecommendation(TestCase):
    """Tests for PUT /api/recommendations/v1/recommendations/<id>"""

    BASE_URL = "/api/recommendations/v1/recommendations"

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        app.app_context().push()

    @classmethod
    def tearDownClass(cls):
        """Run once after all tests"""
        db.session.close()

    def setUp(self):
        """Run before each test"""
        db.session.rollback()
        db.session.query(Recommendation).delete()
        db.session.commit()
        self.client = app.test_client()

    def _create_recommendation(self):
        """Helper to create and persist a recommendation"""
        recommendation = RecommendationFactory()
        recommendation.create()
        return recommendation

    ######################################################################
    #  H A P P Y   P A T H S
    ######################################################################

    def test_update_recommendation(self):
        """It should update an existing recommendation"""
        recommendation = self._create_recommendation()
        new_type = (
            "up_sell"
            if recommendation.recommendation_type != "up_sell"
            else "cross_sell"
        )
        updated_data = {
            "product_id": recommendation.product_id,
            "recommended_product_id": recommendation.recommended_product_id,
            "recommendation_type": new_type,
            "score": 0.95,
        }

        resp = self.client.put(
            f"{self.BASE_URL}/{recommendation.id}",
            json=updated_data,
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(data["id"], recommendation.id)
        self.assertEqual(data["recommendation_type"], new_type)
        self.assertTrue(data["active"])
        self.assertEqual(data["score"], 0.95)

    ######################################################################
    #  S A D   P A T H S
    ######################################################################

    def test_update_recommendation_not_found(self):
        """It should return 404 when updating a non-existent recommendation"""
        updated_data = {
            "product_id": 1,
            "recommended_product_id": 2,
            "recommendation_type": "up_sell",
            "score": 0.5,
        }

        resp = self.client.put(
            f"{self.BASE_URL}/0",
            json=updated_data,
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        data = resp.get_json()
        self.assertIn("message", data)


######################################################################
#  T E S T   A C T I O N   R E C O M M E N D A T I O N
######################################################################
class TestActionRecommendation(TestCase):
    """Tests for activate/deactivate recommendation actions"""

    BASE_URL = "/api/recommendations/v1/recommendations"

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        app.app_context().push()

    @classmethod
    def tearDownClass(cls):
        """Run once after all tests"""
        db.session.close()

    def setUp(self):
        """Run before each test"""
        db.session.rollback()
        db.session.query(Recommendation).delete()
        db.session.commit()
        self.client = app.test_client()

    def _create_recommendation(self):
        """Helper to create and persist a recommendation"""
        recommendation = RecommendationFactory()
        recommendation.create()
        return recommendation

    def test_deactivate_recommendation(self):
        """It should deactivate an existing recommendation"""
        recommendation = RecommendationFactory(active=True)
        recommendation.create()

        resp = self.client.put(f"{self.BASE_URL}/{recommendation.id}/deactivate")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertFalse(data["active"])
        db.session.expire(recommendation)
        self.assertFalse(recommendation.active)

    def test_activate_recommendation(self):
        """It should activate an inactive recommendation"""
        recommendation = RecommendationFactory(active=False)
        recommendation.create()

        resp = self.client.put(f"{self.BASE_URL}/{recommendation.id}/activate")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertTrue(data["active"])
        db.session.expire(recommendation)
        self.assertTrue(recommendation.active)

    def test_deactivate_recommendation_not_found(self):
        """It should return 404 when deactivating a non-existent recommendation"""
        resp = self.client.put(f"{self.BASE_URL}/0/deactivate")

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        data = resp.get_json()
        self.assertIn("message", data)

    def test_activate_recommendation_not_found(self):
        """It should return 404 when activating a non-existent recommendation"""
        resp = self.client.put(f"{self.BASE_URL}/0/activate")

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        data = resp.get_json()
        self.assertIn("message", data)

    def test_update_recommendation_invalid_type(self):
        """It should return 400 when updating with an invalid recommendation type"""
        recommendation = self._create_recommendation()
        original_type = recommendation.recommendation_type
        updated_data = {
            "product_id": recommendation.product_id,
            "recommended_product_id": recommendation.recommended_product_id,
            "recommendation_type": "invalid_type",
            "score": 0.5,
        }

        resp = self.client.put(
            f"{self.BASE_URL}/{recommendation.id}",
            json=updated_data,
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        db.session.expire(recommendation)
        self.assertEqual(recommendation.recommendation_type, original_type)

    def test_update_no_content_type(self):
        """It should return 415 when Content-Type is not application/json"""
        recommendation = self._create_recommendation()
        resp = self.client.put(
            f"{self.BASE_URL}/{recommendation.id}",
            data="not json",
            content_type="text/plain",
        )
        self.assertEqual(resp.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_update_recommendation_equal_product_ids(self):
        """It should return 400 when product_id equals recommended_product_id"""
        recommendation = self._create_recommendation()
        updated_data = {
            "product_id": 100,
            "recommended_product_id": 100,
            "recommendation_type": "up_sell",
            "score": 0.5,
        }

        resp = self.client.put(
            f"{self.BASE_URL}/{recommendation.id}",
            json=updated_data,
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_recommendation_malformed_json(self):
        """It should return 400 when update body contains malformed JSON"""
        recommendation = self._create_recommendation()
        resp = self.client.put(
            f"{self.BASE_URL}/{recommendation.id}",
            data='{"product_id": 1, "recommended_product_id": 2,',
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(resp.content_type.startswith("application/json"))
        data = resp.get_json()
        self.assertIn("message", data)

    def test_update_recommendation_empty_json_body(self):
        """It should return 400 when update body is empty JSON payload"""
        recommendation = self._create_recommendation()
        resp = self.client.put(
            f"{self.BASE_URL}/{recommendation.id}",
            data="",
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(resp.content_type.startswith("application/json"))
        data = resp.get_json()
        self.assertIn("message", data)


######################################################################
#  T E S T   L I K E   R E C O M M E N D A T I O N
######################################################################
class TestLikeRecommendation(TestCase):
    """Tests for PUT /api/recommendations/v1/recommendations/<id>/like"""

    BASE_URL = "/api/recommendations/v1/recommendations"

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        app.app_context().push()

    @classmethod
    def tearDownClass(cls):
        """Run once after all tests"""
        db.session.close()

    def setUp(self):
        """Run before each test"""
        db.session.rollback()
        db.session.query(Recommendation).delete()
        db.session.commit()
        self.client = app.test_client()

    def _create_recommendation(self):
        """Helper to create and persist a recommendation"""
        recommendation = RecommendationFactory()
        recommendation.create()
        return recommendation

    ######################################################################
    #  H A P P Y   P A T H S
    ######################################################################

    def test_like_recommendation(self):
        """It should increment the like count each time"""
        recommendation = self._create_recommendation()
        # First like
        resp = self.client.put(f"{self.BASE_URL}/{recommendation.id}/like")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(data["like_count"], 1)
        # Second like
        resp = self.client.put(f"{self.BASE_URL}/{recommendation.id}/like")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(data["like_count"], 2)

    def test_like_count_persists_on_get(self):
        """It should persist the like count when retrieved via GET"""
        recommendation = self._create_recommendation()
        self.client.put(f"{self.BASE_URL}/{recommendation.id}/like")
        resp = self.client.get(f"{self.BASE_URL}/{recommendation.id}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(data["like_count"], 1)

    def test_like_count_in_create_response(self):
        """It should return like_count of 0 when a recommendation is created"""
        test_data = RecommendationFactory.build().serialize()
        del test_data["id"]
        del test_data["created_at"]
        resp = self.client.post(
            self.BASE_URL,
            json=test_data,
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        data = resp.get_json()
        self.assertEqual(data["like_count"], 0)

    def test_like_count_not_settable_via_update(self):
        """It should not allow like_count to be changed via PUT update"""
        recommendation = self._create_recommendation()
        # Like it once
        self.client.put(f"{self.BASE_URL}/{recommendation.id}/like")
        # Try to set like_count via update
        updated_data = recommendation.serialize()
        updated_data["like_count"] = 99
        resp = self.client.put(
            f"{self.BASE_URL}/{recommendation.id}",
            json=updated_data,
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Verify like_count was not changed
        resp = self.client.get(f"{self.BASE_URL}/{recommendation.id}")
        data = resp.get_json()
        self.assertEqual(data["like_count"], 1)

    ######################################################################
    #  S A D   P A T H S
    ######################################################################

    def test_like_recommendation_not_found(self):
        """It should return 404 when liking a non-existent recommendation"""
        resp = self.client.put(f"{self.BASE_URL}/0/like")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


######################################################################
#  T E S T   Q U E R Y   R E C O M M E N D A T I O N S
######################################################################
class TestQueryRecommendations(TestCase):
    """Tests for GET /api/recommendations/v1/recommendations?<query>"""

    BASE_URL = "/api/recommendations/v1/recommendations"

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        app.app_context().push()

    @classmethod
    def tearDownClass(cls):
        """Run once after all tests"""
        db.session.close()

    def setUp(self):
        """Run before each test"""
        db.session.rollback()
        db.session.query(Recommendation).delete()
        db.session.commit()
        self.client = app.test_client()

    def _create_recommendation(self, **kwargs):
        """Helper to create and persist a recommendation with optional overrides"""
        recommendation = RecommendationFactory(**kwargs)
        recommendation.create()
        return recommendation

    ######################################################################
    #  H A P P Y   P A T H S
    ######################################################################

    def test_query_by_product_id(self):
        """It should filter recommendations by product_id"""
        rec1 = self._create_recommendation(product_id=10, recommended_product_id=200)
        self._create_recommendation(product_id=20, recommended_product_id=201)
        resp = self.client.get(f"{self.BASE_URL}?product_id=10")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["product_id"], rec1.product_id)

    def test_query_by_recommended_product_id(self):
        """It should filter recommendations by recommended_product_id"""
        rec1 = self._create_recommendation(
            product_id=10, recommended_product_id=200
        )
        self._create_recommendation(product_id=20, recommended_product_id=201)
        resp = self.client.get(f"{self.BASE_URL}?recommended_product_id=200")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(
            data[0]["recommended_product_id"], rec1.recommended_product_id
        )

    def test_query_by_recommendation_type(self):
        """It should filter recommendations by recommendation_type"""
        self._create_recommendation(
            product_id=10,
            recommended_product_id=200,
            recommendation_type="cross_sell",
        )
        self._create_recommendation(
            product_id=20,
            recommended_product_id=201,
            recommendation_type="up_sell",
        )
        resp = self.client.get(f"{self.BASE_URL}?recommendation_type=cross_sell")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["recommendation_type"], "cross_sell")

    def test_query_no_results(self):
        """It should return an empty list when no recommendations match"""
        self._create_recommendation(product_id=10, recommended_product_id=200)
        resp = self.client.get(f"{self.BASE_URL}?product_id=999")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), 0)

    ######################################################################
    #  S A D   P A T H S
    ######################################################################

    def test_query_by_invalid_recommendation_type(self):
        """It should return 400 for an invalid recommendation_type"""
        resp = self.client.get(f"{self.BASE_URL}?recommendation_type=invalid")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
