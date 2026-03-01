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
from tests.factories import RecommendationFactory


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

    def test_get_recommendation(self):
        """It should read a single recommendation"""
        client = self._create_test_client()
        # Create a recommendation in the database
        rec = RecommendationFactory()
        rec.create()
        resp = client.get(f"/api/recommendations/v1/{rec.id}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(data["id"], rec.id)
        self.assertEqual(data["product_id"], rec.product_id)
        self.assertEqual(data["recommended_product_id"], rec.recommended_product_id)
        self.assertEqual(data["recommendation_type"], rec.recommendation_type)

    def test_get_recommendation_not_found(self):
        """It should return 404 for a recommendation that doesn't exist"""
        client = self._create_test_client()
        resp = client.get("/api/recommendations/v1/0")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(resp.content_type.startswith("application/json"))
        data = resp.get_json()
        self.assertIn("message", data)
