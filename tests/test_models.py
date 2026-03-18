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

    def test_update_recommendation(self):
        """It should update a Recommendation"""
        recommendation = RecommendationFactory()
        recommendation.create()

        recommendation.score = 0.9
        recommendation.update()

        updated = Recommendation.find(recommendation.id)
        self.assertEqual(updated.score, 0.9)

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
