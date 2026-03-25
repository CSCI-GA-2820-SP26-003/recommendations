"""
Test Factory to make fake objects for testing
"""

import random

import factory
from service.models import Recommendation, RECOMMENDATION_TYPES


class RecommendationFactory(factory.Factory):
    """Creates fake recommendations"""

    class Meta:  # pylint: disable=too-few-public-methods
        """Maps factory to data model"""

        model = Recommendation

    id = factory.Sequence(lambda n: n + 1)
    product_id = factory.Sequence(lambda n: n + 100)
    recommended_product_id = factory.Sequence(lambda n: n + 200)
    recommendation_type = factory.Iterator(RECOMMENDATION_TYPES)
    score = factory.LazyFunction(lambda: round(random.uniform(0.0, 1.0), 2))
    like_count = 0
