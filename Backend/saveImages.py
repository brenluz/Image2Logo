import os
import time
import queue
import threading
import logging
from typing import List, Callable, Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Define the scopes
SCOPES = ['https://www.googleapis.com/auth/drive']

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def authenticate_service_account(service_account_file: str) -> service_account.Credentials:
    """
    Authenticate with Google Drive API using a service account.

    Args:
        service_account_file: Path to the service account JSON key file

    Returns:
        Authenticated credentials
    """
    return service_account.Credentials.from_service_account_file(
        service_account_file, scopes=SCOPES)


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


def upload_to_drive(file_paths: list[str], folder_id, service_account_file='credentials.json'):
    """
    Upload an image to Google Drive using a service account.

    Args:
        file_paths (str): Path to the image file to upload
        folder_id (str): Google Drive folder ID where the image will be uploaded
        service_account_file (str, optional): Path to service account JSON key file.
                                             Defaults to 'credentials.json'.

    Returns:
        dict: File information including id, name, and webViewLink

    Raises:
        FileNotFoundError: If the image file or service account file doesn't exist
        Exception: For any other errors during the upload process
    """
    # Validate input files exist
    # Convert single file path to list for uniform processing
    if isinstance(file_paths, str):
        file_paths = [file_paths]

    # Validate input files exist
    for file_path in file_paths:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

    if not os.path.exists(service_account_file):
        raise FileNotFoundError(f"Service account file not found: {service_account_file}")

    try:
        # Authenticate using service account (once for all files)
        credentials = authenticate_service_account(service_account_file)
        service = build('drive', 'v3', credentials=credentials)

        results = []

        for file_path in file_paths:
            # Get file metadata
            file_name = os.path.basename(file_path)
            mime_type = get_mime_type(file_path)

            file_metadata = {
                'name': file_name,
            }

            # If a folder ID is specified, add it to the metadata
            if folder_id:
                file_metadata['parents'] = [folder_id]

            # Create a MediaFileUpload object for the file
            media = MediaFileUpload(
                file_path,
                mimetype=mime_type,
                resumable=True
            )

            # Upload the file
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,webViewLink'
            ).execute()

            results.append({
                'id': file.get('id'),
                'name': file.get('name'),
                'webViewLink': file.get('webViewLink'),
                'file_path': file_path
            })

        return results

    except Exception as e:
        raise Exception(f"Error uploading files to Google Drive: {str(e)}")


class DriveUploader:
    def __init__(self, service_account_file='credentials.json'):
        """
        Initialize the Drive uploader with a queue for file uploads.

        Args:
            service_account_file: Path to the Google service account credentials file
        """
        self._upload_queue = queue.Queue()
        self._upload_thread = None
        self._stop_event = threading.Event()
        self._service_account_file = service_account_file
        self.on_complete = None

        # Start the worker thread
        self._start_worker()

    def _start_worker(self):
        """Start the background worker thread to process uploads"""
        if self._upload_thread is None or not self._upload_thread.is_alive():
            self._upload_thread = threading.Thread(target=self._upload_worker, daemon=True)
            self._upload_thread.start()
            logger.info("Started Drive upload worker thread")

    def _upload_worker(self):
        """Worker thread function to process the upload queue"""
        while not self._stop_event.is_set():
            try:
                # Get an upload task with a 1-second timeout
                try:
                    task = self._upload_queue.get(timeout=1)
                except queue.Empty:
                    continue

                files, folder_id, callback = task

                logger.info(f"Processing upload of {len(files)} files to folder {folder_id}")

                try:
                    # Perform the actual upload
                    results = upload_to_drive(
                        file_paths=files,
                        folder_id=folder_id,
                        service_account_file=self._service_account_file
                    )

                    logger.info(f"Successfully uploaded {len(results)} files to Drive")

                    # Call callback with results if provided
                    if callback:
                        callback(results)

                except Exception as e:
                    logger.error(f"Error during file upload: {str(e)}")
                    if callback:
                        callback({'error': str(e)})

                # Mark task as done
                self._upload_queue.task_done()

            except Exception as e:
                logger.error(f"Unexpected error in upload worker: {str(e)}")
                time.sleep(1)  # Prevent tight loop in case of recurring errors

    def upload_files(
            self,
            file_paths: List[str],
            folder_id: str,
            callback: Optional[Callable] = None
    ) -> None:
        """
        Queue files for upload to Google Drive.

        Args:
            file_paths: List of file paths to upload
            folder_id: Google Drive folder ID
            callback: Optional function to call with results when complete
        """
        # Ensure worker thread is running
        self._start_worker()

        # Add upload task to queue
        self._upload_queue.put((file_paths, folder_id, callback))
        logger.info(f"Queued {len(file_paths)} files for upload to folder {folder_id}")

    def stop(self):
        """Stop the uploader and wait for current uploads to finish"""
        self._stop_event.set()
        if self._upload_thread and self._upload_thread.is_alive():
            self._upload_thread.join(timeout=5)
            logger.info("Drive uploader stopped")

    def wait_for_completion(self):
        """
        Wait for all queued uploads to complete.

        Args:
            timeout: Maximum time to wait in seconds, or None to wait indefinitely

        Returns:
            bool: True if queue is empty, False if timeout occurred
        """
        return self._upload_queue.join()