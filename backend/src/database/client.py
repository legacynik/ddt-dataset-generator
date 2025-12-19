"""Supabase client singleton for database and storage operations.

This module provides a singleton pattern for the Supabase client to ensure
a single connection instance is reused across the application.
"""

import logging
from typing import Optional
from supabase import Client, create_client
from supabase.client import ClientOptions
from ..config import settings

logger = logging.getLogger(__name__)

# Singleton instance
_supabase_client: Optional[Client] = None


def get_client() -> Client:
    """Get or create the Supabase client instance.

    This function implements a singleton pattern to ensure only one client
    instance is created and reused throughout the application lifecycle.

    The client is configured with the service role key to bypass Row Level
    Security (RLS) policies, which is necessary for backend operations.

    Returns:
        Client: Supabase client instance configured with service role key.

    Example:
        >>> client = get_client()
        >>> data = client.table("dataset_samples").select("*").execute()
    """
    global _supabase_client

    if _supabase_client is None:
        logger.info("Initializing Supabase client with service role key")

        # Use service role key to bypass RLS for backend operations
        _supabase_client = create_client(
            supabase_url=settings.SUPABASE_URL,
            supabase_key=settings.SUPABASE_SERVICE_KEY,
            options=ClientOptions(
                # Configure client options if needed
                # auto_refresh_token=False,  # Service key doesn't need refresh
                # persist_session=False,     # No user sessions in backend
            )
        )

        logger.info(
            f"Supabase client initialized successfully (URL: {settings.SUPABASE_URL})"
        )

    return _supabase_client


def get_storage():
    """Get the Supabase Storage client for the dataset-pdfs bucket.

    This is a convenience function that returns the storage client
    specifically configured for the PDF storage bucket.

    Returns:
        Storage client for the 'dataset-pdfs' bucket.

    Example:
        >>> storage = get_storage()
        >>> storage.upload("path/file.pdf", pdf_bytes)
    """
    client = get_client()
    return client.storage.from_(settings.SUPABASE_BUCKET)


def reset_client() -> None:
    """Reset the singleton client instance.

    This function is primarily used for testing purposes to ensure
    a fresh client instance can be created with different settings.

    Warning:
        This should not be used in production code.
    """
    global _supabase_client
    _supabase_client = None
    logger.debug("Supabase client instance reset")
