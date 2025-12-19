"""Supabase Storage operations for PDF files.

This module provides functions to upload, retrieve, and delete PDF files
from the Supabase Storage bucket.
"""

import logging
from typing import Optional
from uuid import uuid4

from .client import get_storage
from ..config import settings

logger = logging.getLogger(__name__)


def upload_pdf(file_bytes: bytes, filename: str) -> str:
    """Upload a PDF file to Supabase Storage.

    The file is stored with a unique UUID-based path to prevent naming conflicts.
    The original filename is preserved in the database record.

    Args:
        file_bytes: Binary content of the PDF file
        filename: Original filename (used for generating storage path)

    Returns:
        str: Storage path of the uploaded file (e.g., "uploads/{uuid}.pdf")

    Raises:
        Exception: If upload fails

    Example:
        >>> with open("sample.pdf", "rb") as f:
        ...     pdf_bytes = f.read()
        >>> storage_path = upload_pdf(pdf_bytes, "sample.pdf")
        >>> print(storage_path)
        "uploads/123e4567-e89b-12d3-a456-426614174000.pdf"
    """
    # Generate unique storage path
    file_uuid = uuid4()
    storage_path = f"uploads/{file_uuid}.pdf"

    logger.info(f"Uploading PDF {filename} to storage path: {storage_path}")

    try:
        storage = get_storage()

        # Upload with explicit content type
        response = storage.upload(
            path=storage_path,
            file=file_bytes,
            file_options={
                "content-type": "application/pdf",
                "cache-control": "3600",
                "upsert": "false",
            },
        )

        # Check if upload was successful
        if response is None:
            raise Exception("Upload response was None")

        logger.info(
            f"PDF uploaded successfully: {filename} -> {storage_path} "
            f"({len(file_bytes)} bytes)"
        )
        return storage_path

    except Exception as e:
        logger.error(f"Failed to upload PDF {filename}: {str(e)}")
        raise Exception(f"Failed to upload PDF to storage: {str(e)}")


def get_pdf_url(storage_path: str, expires_in: int = 3600) -> str:
    """Get a signed URL for accessing a PDF file.

    The signed URL is temporary and expires after the specified duration.
    This is necessary because the storage bucket is private.

    Args:
        storage_path: Storage path of the file (e.g., "uploads/{uuid}.pdf")
        expires_in: URL expiration time in seconds (default: 1 hour)

    Returns:
        str: Signed URL that can be used to access the file

    Raises:
        Exception: If URL generation fails

    Example:
        >>> url = get_pdf_url("uploads/123e4567-e89b-12d3-a456-426614174000.pdf")
        >>> print(url)
        "https://xxx.supabase.co/storage/v1/object/sign/dataset-pdfs/uploads/..."
    """
    logger.debug(f"Generating signed URL for: {storage_path} (expires in {expires_in}s)")

    try:
        storage = get_storage()

        # Create signed URL
        response = storage.create_signed_url(path=storage_path, expires_in=expires_in)

        if not response or "signedURL" not in response:
            raise Exception("Failed to generate signed URL: invalid response")

        signed_url = response["signedURL"]

        logger.debug(f"Signed URL generated successfully for {storage_path}")
        return signed_url

    except Exception as e:
        logger.error(f"Failed to generate signed URL for {storage_path}: {str(e)}")
        raise Exception(f"Failed to generate PDF URL: {str(e)}")


def delete_pdf(storage_path: str) -> bool:
    """Delete a PDF file from Supabase Storage.

    Args:
        storage_path: Storage path of the file to delete

    Returns:
        bool: True if deletion was successful, False otherwise

    Example:
        >>> success = delete_pdf("uploads/123e4567-e89b-12d3-a456-426614174000.pdf")
        >>> print(success)
        True
    """
    logger.info(f"Deleting PDF from storage: {storage_path}")

    try:
        storage = get_storage()

        # Delete the file
        response = storage.remove([storage_path])

        # Check response for success
        # The response format may vary, so we handle different cases
        if response is None:
            logger.warning(f"Delete response was None for {storage_path}")
            return False

        logger.info(f"PDF deleted successfully: {storage_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to delete PDF {storage_path}: {str(e)}")
        return False


def get_pdf_bytes(storage_path: str) -> Optional[bytes]:
    """Download and return the binary content of a PDF file.

    This function is useful when you need to process the PDF content
    (e.g., sending it to an external API).

    Args:
        storage_path: Storage path of the file

    Returns:
        bytes: Binary content of the PDF file, or None if download fails

    Example:
        >>> pdf_bytes = get_pdf_bytes("uploads/123e4567-e89b-12d3-a456-426614174000.pdf")
        >>> if pdf_bytes:
        ...     print(f"Downloaded {len(pdf_bytes)} bytes")
    """
    logger.debug(f"Downloading PDF bytes from: {storage_path}")

    try:
        storage = get_storage()

        # Download the file
        response = storage.download(storage_path)

        if not response:
            logger.warning(f"Download returned no data for {storage_path}")
            return None

        logger.debug(f"Downloaded {len(response)} bytes from {storage_path}")
        return response

    except Exception as e:
        logger.error(f"Failed to download PDF {storage_path}: {str(e)}")
        return None


def list_pdfs(folder: str = "uploads", limit: int = 100) -> list[dict]:
    """List PDF files in a storage folder.

    Args:
        folder: Folder path to list (default: "uploads")
        limit: Maximum number of files to return

    Returns:
        List of file metadata dictionaries

    Example:
        >>> files = list_pdfs()
        >>> for file in files:
        ...     print(f"{file['name']} - {file['metadata']['size']} bytes")
    """
    logger.debug(f"Listing PDFs in folder: {folder} (limit: {limit})")

    try:
        storage = get_storage()

        # List files in the folder
        response = storage.list(path=folder, options={"limit": limit})

        if not response:
            logger.warning(f"No files found in {folder}")
            return []

        logger.debug(f"Found {len(response)} files in {folder}")
        return response

    except Exception as e:
        logger.error(f"Failed to list PDFs in {folder}: {str(e)}")
        return []


def check_file_exists(storage_path: str) -> bool:
    """Check if a file exists in storage.

    Args:
        storage_path: Storage path to check

    Returns:
        bool: True if file exists, False otherwise

    Example:
        >>> exists = check_file_exists("uploads/123e4567-e89b-12d3-a456-426614174000.pdf")
        >>> print(exists)
        True
    """
    logger.debug(f"Checking if file exists: {storage_path}")

    try:
        # Try to get file metadata
        url = get_pdf_url(storage_path, expires_in=60)
        return url is not None and len(url) > 0

    except Exception:
        return False
