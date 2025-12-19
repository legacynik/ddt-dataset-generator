"""Pytest configuration and fixtures.

Sets up SSL certificates for Azure API calls on macOS.
"""

import os
import certifi


def pytest_configure(config):
    """Configure pytest - set SSL cert paths for macOS Python 3.13."""
    # Set SSL certificate paths to use certifi certificates
    # This fixes SSL verification errors on macOS with Python 3.13
    cert_path = certifi.where()
    os.environ["SSL_CERT_FILE"] = cert_path
    os.environ["REQUESTS_CA_BUNDLE"] = cert_path
