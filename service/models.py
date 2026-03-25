"""
Models for Recommendation

All of the models are stored in this module
"""

import logging
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint
from sqlalchemy import Enum as SAEnum

logger = logging.getLogger("flask.app")

# Create the SQLAlchemy object to be initialized later in init_db()
db = SQLAlchemy()


class DataValidationError(Exception):
    """Used for data validation errors when deserializing"""


RECOMMENDATION_TYPES = ("cross_sell", "up_sell", "accessory", "similar_item")


class Recommendation(db.Model):
    """
    Class that represents a product recommendation relationship
    """

    __tablename__ = "recommendations"
    __table_args__ = (
        CheckConstraint(
            "product_id <> recommended_product_id",
            name="ck_recommendations_distinct_products",
        ),
    )

    ##################################################
    # Table Schema
    ##################################################
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, nullable=False)
    recommended_product_id = db.Column(db.Integer, nullable=False)
    recommendation_type = db.Column(
        SAEnum(*RECOMMENDATION_TYPES, name="recommendation_type"),
        nullable=False,
    )
    score = db.Column(db.Float, nullable=True)
    like_count = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self):
        return (
            f"<Recommendation id=[{self.id}] product={self.product_id} "
            f"recommended_product={self.recommended_product_id}>"
        )

    def _validate(self):
        """Validates cross-field and enum constraints"""
        if self.recommendation_type not in RECOMMENDATION_TYPES:
            raise DataValidationError(
                f"Invalid recommendation_type: {self.recommendation_type}"
            )
        if self.product_id == self.recommended_product_id:
            raise DataValidationError(
                "product_id and recommended_product_id must not be equal"
            )

    def create(self):
        """
        Creates a Recommendation in the database
        """
        logger.info(
            "Creating recommendation for product=%s recommended_product=%s",
            self.product_id,
            self.recommended_product_id,
        )
        self.id = None  # pylint: disable=invalid-name
        self._validate()
        try:
            db.session.add(self)
            db.session.commit()
        except Exception as error:  # pylint: disable=broad-except
            db.session.rollback()
            logger.error("Error creating record: %s", self)
            raise DataValidationError(error) from error

    def update(self):
        """
        Updates a Recommendation in the database
        """
        logger.info("Saving recommendation id=%s", self.id)
        self._validate()
        try:
            db.session.commit()
        except Exception as error:  # pylint: disable=broad-except
            db.session.rollback()
            logger.error("Error updating record: %s", self)
            raise DataValidationError(error) from error

    def delete(self):
        """Removes a Recommendation from the data store"""
        logger.info("Deleting recommendation id=%s", self.id)
        try:
            db.session.delete(self)
            db.session.commit()
        except Exception as error:  # pylint: disable=broad-except
            db.session.rollback()
            logger.error("Error deleting record: %s", self)
            raise DataValidationError(error) from error

    def serialize(self):
        """Serializes a Recommendation into a dictionary"""
        return {
            "id": self.id,
            "product_id": self.product_id,
            "recommended_product_id": self.recommended_product_id,
            "recommendation_type": self.recommendation_type,
            "score": self.score,
            "like_count": self.like_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def deserialize(self, data):
        """
        Deserializes a Recommendation from a dictionary

        Args:
            data (dict): A dictionary containing recommendation data
        """
        try:
            self.product_id = int(data["product_id"])
            self.recommended_product_id = int(data["recommended_product_id"])
            self.recommendation_type = str(data["recommendation_type"])
            self.score = float(data["score"]) if data.get("score") is not None else None
            self._validate()
        except AttributeError as error:
            raise DataValidationError("Invalid attribute: " + error.args[0]) from error
        except KeyError as error:
            raise DataValidationError(
                "Invalid Recommendation: missing " + error.args[0]
            ) from error
        except (TypeError, ValueError) as error:
            raise DataValidationError(
                "Invalid Recommendation: body of request contained bad or no data "
                + str(error)
            ) from error
        return self

    ##################################################
    # CLASS METHODS
    ##################################################

    @classmethod
    def all(cls):
        """Returns all of the Recommendations in the database"""
        logger.info("Processing all Recommendations")
        return cls.query.all()

    @classmethod
    def find(cls, by_id):
        """Finds a Recommendation by its ID"""
        logger.info("Processing lookup for id %s ...", by_id)
        return cls.query.session.get(cls, by_id)

    @classmethod
    def find_by_product_id(cls, product_id):
        """Returns all Recommendations with the given product_id"""
        logger.info("Processing product_id query for %s ...", product_id)
        return cls.query.filter(cls.product_id == product_id)

    @classmethod
    def find_by_recommended_product_id(cls, recommended_product_id):
        """Returns all Recommendations with the given recommended_product_id"""
        logger.info(
            "Processing recommended_product_id query for %s ...",
            recommended_product_id,
        )
        return cls.query.filter(
            cls.recommended_product_id == recommended_product_id
        )

    @classmethod
    def find_by_recommendation_type(cls, recommendation_type):
        """Returns all Recommendations with the given recommendation_type"""
        logger.info(
            "Processing recommendation_type query for %s ...",
            recommendation_type,
        )
        if recommendation_type not in RECOMMENDATION_TYPES:
            raise DataValidationError(
                f"Invalid recommendation_type: {recommendation_type}"
            )
        return cls.query.filter(
            cls.recommendation_type == recommendation_type
        )
