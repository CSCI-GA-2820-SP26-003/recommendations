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

"""
Package: service
Package for the application models and service routes
This module creates and configures the Flask app and sets up the logging
and SQL database
"""
import sys
from flask import Flask, jsonify
from service import config
from service.common import log_handlers


############################################################
# Initialize the Flask instance
############################################################
def create_app():
    """Initialize the core application."""
    # Create Flask application
    app = Flask(__name__)
    app.config.from_object(config)

    # Initialize Plugins
    # pylint: disable=import-outside-toplevel
    from service.models import db
    db.init_app(app)

    with app.app_context():
        # Import routes and models after Flask app is created
        # pylint: disable=wrong-import-position, wrong-import-order, unused-import
        from service import routes, models  # noqa: F401 E402
        from service.common import cli_commands  # noqa: F401, E402

        # Initialize Flask-RESTX (registers all namespaces and routes)
        routes.api.init_app(app)

        # Register the HTML web UI at /
        routes.init_index_route(app)

        # App-level error handlers for routes outside Flask-RESTX
        @app.errorhandler(404)
        def not_found(error):  # pylint: disable=unused-variable
            """Return JSON for 404 errors"""
            return jsonify(
                status=404,
                error="Not Found",
                message=str(error),
            ), 404

        @app.errorhandler(405)
        def method_not_allowed(error):  # pylint: disable=unused-variable
            """Return JSON for 405 errors"""
            return jsonify(
                status=405,
                error="Method not Allowed",
                message=str(error),
            ), 405

        try:
            db.create_all()
        except Exception as error:  # pylint: disable=broad-except
            app.logger.critical("%s: Cannot continue", error)
            # gunicorn requires exit code 4 to stop spawning workers when they die
            sys.exit(4)

        # Set up logging for production
        log_handlers.init_logging(app, "gunicorn.error")

        app.logger.info(70 * "*")
        app.logger.info("  S E R V I C E   R U N N I N G  ".center(70, "*"))
        app.logger.info(70 * "*")

        app.logger.info("Service initialized!")

        return app
