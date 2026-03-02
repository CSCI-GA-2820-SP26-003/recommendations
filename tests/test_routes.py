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

# pylint: disable=duplicate-code
import os
import sys
import logging
from unittest import TestCase
from unittest.mock import patch
from service.common import status


######################################################################
#  T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestYourResourceService(TestCase):
    """REST API Server Tests"""

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

        app = wsgi.app
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.logger.setLevel(logging.CRITICAL)
        return app.test_client()

    ######################################################################
    #  T E S T   C A S E S
    ######################################################################

    def test_index_returns_json_with_base_path(self):
        """It should return useful JSON metadata from GET /"""
        client = self._create_test_client()

        resp = client.get("/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.content_type.startswith("application/json"))
        data = resp.get_json()
        self.assertEqual(data["service"], "recommendation")
        self.assertEqual(data["env"], "local")
        self.assertEqual(data["base_path"], "/api/recommendations/v1")
        self.assertIn("/api/recommendations/v1/health", data["endpoints"])

    def test_health_returns_ok_json(self):
        """It should return HTTP 200 JSON on GET {BASE_PATH}/health"""
        client = self._create_test_client()

        resp = client.get("/api/recommendations/v1/health")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.content_type.startswith("application/json"))
        data = resp.get_json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["service"], "recommendation")
        self.assertEqual(data["env"], "local")
        self.assertEqual(data["base_path"], "/api/recommendations/v1")

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
        data = resp.get_json()
        self.assertEqual(data["env"], "staging")
        self.assertEqual(data["base_path"], "/api/reco")

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
        data = resp.get_json()
        self.assertEqual(data["base_path"], "/api/reco/v2")

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
        data = resp.get_json()
        self.assertEqual(data["base_path"], "/api/recommendations/v1")

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

        resp = client.post("/api/recommendations/v1/health")

        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertTrue(resp.content_type.startswith("application/json"))
        data = resp.get_json()
        self.assertEqual(data["error"], "Method not Allowed")
        self.assertIn("message", data)


######################################################################
#  H E L P E R S
######################################################################
DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql+psycopg://postgres:postgres@localhost:5432/testdb"
)
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


######################################################################
#  T E S T   L I S T   R E C O M M E N D A T I O N S
######################################################################
class TestListRecommendations(TestCase):
    """Tests for GET /api/recommendations/v1/recommendations"""

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

    def test_list_recommendations_empty(self):
        """It should return an empty list when no recommendations exist"""
        resp = self.client.get(f"{BASE_PATH}/recommendations")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.content_type.startswith("application/json"))
        self.assertEqual(resp.get_json(), [])

    def test_list_all_recommendations(self):
        """It should return all recommendations when no pagination is specified"""
        from tests.factories import RecommendationFactory  # pylint: disable=import-outside-toplevel
        for _ in range(3):
            RecommendationFactory().create()
        resp = self.client.get(f"{BASE_PATH}/recommendations")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), 3)

    def test_list_recommendations_page_1(self):
        """It should return up to 10 records for page=1"""
        from tests.factories import RecommendationFactory  # pylint: disable=import-outside-toplevel
        for _ in range(15):
            RecommendationFactory().create()
        resp = self.client.get(f"{BASE_PATH}/recommendations?page=1")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), 10)

    def test_list_recommendations_page_2(self):
        """It should return remaining records on page 2"""
        from tests.factories import RecommendationFactory  # pylint: disable=import-outside-toplevel
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
