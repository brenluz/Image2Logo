#!/usr/bin/env python3
"""
Module providing functions to upload images to Google Drive using a Service Account.
This module can be imported and used in other Python scripts.
"""

import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Define the scopes
SCOPES = ['https://www.googleapis.com/auth/drive']


def authenticate_service_account(service_account_file):
    """
    Authenticate with Google Drive API using a service account.

    Args:
        service_account_file (str): Path to the service account JSON key file

    Returns:
        google.oauth2.service_account.Credentials: Authenticated credentials
    """
    credentials = service_account.Credentials.from_service_account_file(
        service_account_file, scopes=SCOPES)
    return credentials


def get_mime_type(file_path):
    """
    Get the MIME type based on file extension.

    Args:
        file_path (str): Path to the file

    Returns:
        str: MIME type of the file
    """
    extension = os.path.splitext(file_path)[1].lower()

    mime_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp',
        '.webp': 'image/webp',
        '.tiff': 'image/tiff',
        '.tif': 'image/tiff'
    }

    return mime_types.get(extension, 'application/octet-stream')


def upload_to_drive(image_path, folder_id, service_account_file='credentials.json'):
    """
    Upload an image to Google Drive using a service account.

    Args:
        image_path (str): Path to the image file to upload
        folder_id (str): Google Drive folder ID where the image will be uploaded
        service_account_file (str, optional): Path to service account JSON key file.
                                             Defaults to 'service_account.json'.

    Returns:
        dict: File information including id, name, and webViewLink

    Raises:
        FileNotFoundError: If the image file or service account file doesn't exist
        Exception: For any other errors during the upload process
    """
    # Validate input files exist
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")

    if not os.path.exists(service_account_file):
        raise FileNotFoundError(f"Service account file not found: {service_account_file}")

    try:
        # Authenticate using service account
        credentials = authenticate_service_account(service_account_file)
        service = build('drive', 'v3', credentials=credentials)

        # Get file metadata
        file_name = os.path.basename(image_path)
        mime_type = get_mime_type(image_path)

        file_metadata = {
            'name': file_name,
        }

        # If a folder ID is specified, add it to the metadata
        if folder_id:
            file_metadata['parents'] = [folder_id]

        # Create a MediaFileUpload object for the image
        media = MediaFileUpload(
            image_path,
            mimetype=mime_type,
            resumable=True
        )

        # Upload the file
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id,name,webViewLink'
        ).execute()

        return {
            'id': file.get('id'),
            'name': file.get('name'),
            'webViewLink': file.get('webViewLink')
        }

    except Exception as e:
        raise Exception(f"Error uploading file to Google Drive: {str(e)}")


# Example of using this as a standalone script
if __name__ == '__main__':
    print("Uploading image to Google Drive...")
    upload_to_drive("smile_detected.jpg","1xvNIx-GuOSMT-ADoza74SRmgCXOt-2LZ","credentials.json")
    print("Upload complete.")