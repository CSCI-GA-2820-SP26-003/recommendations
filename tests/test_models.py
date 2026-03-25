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
Test cases for Pet Model
"""

# pylint: disable=duplicate-code
import os
import logging
from unittest import TestCase
from unittest.mock import patch
from sqlalchemy import inspect
from wsgi import app
from service.models import Recommendation, DataValidationError, db
from .factories import RecommendationFactory

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql+psycopg://postgres:postgres@localhost:5432/postgres"
)


######################################################################
#  Recommendation   M O D E L   T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestRecommendationModel(TestCase):
    """Test Cases for Recommendation Model"""

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
        db.session.query(Recommendation).delete()  # clean up the last tests
        db.session.commit()

    def tearDown(self):
        """This runs after each test"""
        db.session.remove()

    ######################################################################
    #  T E S T   C A S E S
    ######################################################################

    def test_table_exists(self):
        """It should create recommendations table"""
        inspector = inspect(db.engine)
        self.assertIn("recommendations", inspector.get_table_names())

    def test_create_recommendation(self):
        """It should create a Recommendation"""
        recommendation = RecommendationFactory()
        recommendation.create()

        self.assertIsNotNone(recommendation.id)
        found = Recommendation.all()
        self.assertEqual(len(found), 1)

        data = Recommendation.find(recommendation.id)
        self.assertEqual(data.product_id, recommendation.product_id)
        self.assertEqual(
            data.recommended_product_id, recommendation.recommended_product_id
        )
        self.assertEqual(data.recommendation_type, recommendation.recommendation_type)
        self.assertEqual(data.score, recommendation.score)
        self.assertIsNotNone(data.created_at)

    def test_serialize_recommendation(self):
        """It should serialize a Recommendation"""
        recommendation = RecommendationFactory()
        recommendation.create()

        data = recommendation.serialize()
        self.assertEqual(data["id"], recommendation.id)
        self.assertEqual(data["product_id"], recommendation.product_id)
        self.assertEqual(
            data["recommended_product_id"], recommendation.recommended_product_id
        )
        self.assertEqual(data["recommendation_type"], recommendation.recommendation_type)
        self.assertEqual(data["active"], recommendation.active)
        self.assertEqual(data["score"], recommendation.score)
        self.assertIsNotNone(data["created_at"])

    def test_deserialize_recommendation(self):
        """It should deserialize a Recommendation"""
        payload = {
            "product_id": 1,
            "recommended_product_id": 2,
            "recommendation_type": "cross_sell",
            "score": 0.75,
        }
        recommendation = Recommendation()
        recommendation.deserialize(payload)
        self.assertEqual(recommendation.product_id, 1)
        self.assertEqual(recommendation.recommended_product_id, 2)
        self.assertEqual(recommendation.recommendation_type, "cross_sell")
        self.assertEqual(recommendation.score, 0.75)
        self.assertTrue(recommendation.active)

    def test_deserialize_recommendation_active_false(self):
        """It should deserialize a Recommendation with active false"""
        payload = {
            "product_id": 1,
            "recommended_product_id": 2,
            "recommendation_type": "cross_sell",
            "active": False,
            "score": 0.75,
        }
        recommendation = Recommendation()
        recommendation.deserialize(payload)
        self.assertFalse(recommendation.active)

    def test_deserialize_recommendation_active_string_true(self):
        """It should deserialize a Recommendation with active string true"""
        payload = {
            "product_id": 1,
            "recommended_product_id": 2,
            "recommendation_type": "cross_sell",
            "active": "yes",
            "score": 0.75,
        }
        recommendation = Recommendation()
        recommendation.deserialize(payload)
        self.assertTrue(recommendation.active)

    def test_deserialize_recommendation_active_string_false(self):
        """It should deserialize a Recommendation with active string false"""
        payload = {
            "product_id": 1,
            "recommended_product_id": 2,
            "recommendation_type": "cross_sell",
            "active": "off",
            "score": 0.75,
        }
        recommendation = Recommendation()
        recommendation.deserialize(payload)
        self.assertFalse(recommendation.active)

    def test_deserialize_recommendation_invalid_active_value(self):
        """It should reject invalid active values"""
        payload = {
            "product_id": 1,
            "recommended_product_id": 2,
            "recommendation_type": "cross_sell",
            "active": "maybe",
            "score": 0.75,
        }
        recommendation = Recommendation()
        self.assertRaises(DataValidationError, recommendation.deserialize, payload)

    def test_update_recommendation(self):
        """It should update a Recommendation"""
        recommendation = RecommendationFactory()
        recommendation.create()

        recommendation.score = 0.9
        recommendation.update()

        updated = Recommendation.find(recommendation.id)
        self.assertEqual(updated.score, 0.9)

    def test_recommendation_is_active_by_default(self):
        """It should default new Recommendations to active"""
        recommendation = RecommendationFactory()
        recommendation.create()

        found = Recommendation.find(recommendation.id)
        self.assertTrue(found.active)

    def test_delete_recommendation(self):
        """It should delete a Recommendation"""
        recommendation = RecommendationFactory()
        recommendation.create()

        recommendation.delete()
        self.assertIsNone(Recommendation.find(recommendation.id))

    def test_find_by_product_id(self):
        """It should find Recommendations by product_id"""
        recommendation = RecommendationFactory(product_id=500, recommended_product_id=600)
        recommendation.create()
        RecommendationFactory(product_id=501, recommended_product_id=601).create()

        found = Recommendation.find_by_product_id(500).all()
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].id, recommendation.id)

    def test_find_by_recommendation_type(self):
        """It should find Recommendations by recommendation_type"""
        RecommendationFactory(
            product_id=610, recommended_product_id=710, recommendation_type="up_sell"
        ).create()
        RecommendationFactory(
            product_id=611, recommended_product_id=711, recommendation_type="cross_sell"
        ).create()
        RecommendationFactory(
            product_id=612, recommended_product_id=712, recommendation_type="up_sell"
        ).create()

        found = Recommendation.find_by_recommendation_type("up_sell").all()
        self.assertEqual(len(found), 2)
        for item in found:
            self.assertEqual(item.recommendation_type, "up_sell")

    def test_find_by_recommendation_type_rejects_invalid_value(self):
        """It should reject invalid recommendation_type queries"""
        self.assertRaises(
            DataValidationError,
            Recommendation.find_by_recommendation_type,
            "invalid_type",
        )

    def test_all_recommendations_empty(self):
        """It should return an empty list when no Recommendations exist"""
        found = Recommendation.all()
        self.assertEqual(found, [])

    def test_all_recommendations(self):
        """It should return all Recommendations from the database"""
        recommendation_1 = RecommendationFactory(product_id=700, recommended_product_id=800)
        recommendation_1.create()
        recommendation_2 = RecommendationFactory(product_id=701, recommended_product_id=801)
        recommendation_2.create()

        found = Recommendation.all()
        self.assertEqual(len(found), 2)
        found_ids = [item.id for item in found]
        self.assertIn(recommendation_1.id, found_ids)
        self.assertIn(recommendation_2.id, found_ids)

    def test_find_recommendation_by_id(self):
        """It should find a Recommendation by id and return None when missing"""
        recommendation = RecommendationFactory(product_id=510, recommended_product_id=610)
        recommendation.create()

        found = Recommendation.find(recommendation.id)
        self.assertIsNotNone(found)
        self.assertEqual(found.id, recommendation.id)

        missing = Recommendation.find(999999)
        self.assertIsNone(missing)

    def test_create_recommendation_type_validation(self):
        """It should reject invalid recommendation_type"""
        recommendation = Recommendation()
        payload = {
            "product_id": 1,
            "recommended_product_id": 2,
            "recommendation_type": "invalid_type",
            "score": 0.5,
        }
        self.assertRaises(DataValidationError, recommendation.deserialize, payload)

    def test_create_distinct_product_validation(self):
        """It should reject equal product_id and recommended_product_id"""
        recommendation = Recommendation()
        payload = {
            "product_id": 1,
            "recommended_product_id": 1,
            "recommendation_type": "cross_sell",
            "score": 0.5,
        }
        self.assertRaises(DataValidationError, recommendation.deserialize, payload)

    def test_deserialize_missing_data(self):
        """It should reject missing required fields"""
        recommendation = Recommendation()
        payload = {"recommended_product_id": 2, "recommendation_type": "cross_sell"}
        self.assertRaises(DataValidationError, recommendation.deserialize, payload)

    def test_deserialize_bad_type(self):
        """It should reject non-dict input data"""
        recommendation = Recommendation()
        self.assertRaises(DataValidationError, recommendation.deserialize, "bad data")

    def test_deserialize_invalid_attribute(self):
        """It should reject objects that do not expose dict-like .get"""
        recommendation = Recommendation()

        class IncompleteData:  # pylint: disable=too-few-public-methods
            """Supports index access but not .get, to trigger AttributeError"""

            def __getitem__(self, key):
                data = {
                    "product_id": 1,
                    "recommended_product_id": 2,
                    "recommendation_type": "cross_sell",
                }
                return data[key]

        self.assertRaises(DataValidationError, recommendation.deserialize, IncompleteData())

    def test_repr(self):
        """It should render __repr__"""
        recommendation = RecommendationFactory()
        representation = repr(recommendation)
        self.assertIn("Recommendation", representation)
        self.assertIn("product=", representation)

    def test_create_handles_db_exception(self):
        """It should raise DataValidationError when create commit fails"""
        recommendation = RecommendationFactory.build()
        with patch("service.models.db.session.commit", side_effect=Exception("boom")):
            self.assertRaises(DataValidationError, recommendation.create)

    def test_update_handles_db_exception(self):
        """It should raise DataValidationError when update commit fails"""
        recommendation = RecommendationFactory()
        recommendation.create()
        with patch("service.models.db.session.commit", side_effect=Exception("boom")):
            self.assertRaises(DataValidationError, recommendation.update)

    def test_delete_handles_db_exception(self):
        """It should raise DataValidationError when delete commit fails"""
        recommendation = RecommendationFactory()
        recommendation.create()
        with patch("service.models.db.session.commit", side_effect=Exception("boom")):
            self.assertRaises(DataValidationError, recommendation.delete)

    ######################################################################
    #  L I K E   C O U N T   T E S T S
    ######################################################################

    def test_like_count_default(self):
        """It should default like_count to 0"""
        recommendation = RecommendationFactory()
        recommendation.create()
        found = Recommendation.find(recommendation.id)
        self.assertEqual(found.like_count, 0)

    def test_serialize_includes_like_count(self):
        """It should include like_count in serialized output"""
        recommendation = RecommendationFactory()
        recommendation.create()
        data = recommendation.serialize()
        self.assertIn("like_count", data)
        self.assertEqual(data["like_count"], 0)

    def test_deserialize_ignores_like_count(self):
        """It should not set like_count from deserialized data"""
        recommendation = RecommendationFactory()
        recommendation.create()
        data = recommendation.serialize()
        data["like_count"] = 99
        recommendation.deserialize(data)
        self.assertEqual(recommendation.like_count, 0)

    ######################################################################
    #  Q U E R Y   M E T H O D   T E S T S
    ######################################################################

    def test_find_by_recommended_product_id(self):
        """It should find recommendations by recommended_product_id"""
        rec1 = RecommendationFactory(
            product_id=10, recommended_product_id=200
        )
        rec1.create()
        rec2 = RecommendationFactory(
            product_id=20, recommended_product_id=201
        )
        rec2.create()
        results = Recommendation.find_by_recommended_product_id(200).all()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].recommended_product_id, 200)

    def test_find_by_recommendation_type_query_method(self):
        """It should find recommendations by recommendation_type query method"""
        rec1 = RecommendationFactory(
            product_id=10,
            recommended_product_id=200,
            recommendation_type="cross_sell",
        )
        rec1.create()
        rec2 = RecommendationFactory(
            product_id=20,
            recommended_product_id=201,
            recommendation_type="up_sell",
        )
        rec2.create()
        results = Recommendation.find_by_recommendation_type("cross_sell").all()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].recommendation_type, "cross_sell")

    def test_find_by_recommendation_type_invalid(self):
        """It should raise DataValidationError for invalid type"""
        self.assertRaises(
            DataValidationError,
            Recommendation.find_by_recommendation_type,
            "invalid_type",
        )
