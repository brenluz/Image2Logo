import asyncio
import base64
import json
import logging
import queue
import threading
import cv2 as cv
import websockets
import os
from saveImages import DriveUploader

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('smile_detector')
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)

# Constants
WEBSOCKET_URI = 'wss://image2logo-b2a51e3b7966.herokuapp.com:443'
DRIVE_FOLDER_ID = "1xvNIx-GuOSMT-ADoza74SRmgCXOt-2LZ"
BATCH_SIZE = 3  # Number of images to collect before uploading

# Setup queues for async communication
message_queue = queue.Queue()
upload_batch = []

# Initialize the camera
cap = cv.VideoCapture(4, cv.CAP_DSHOW)
if not cap.isOpened():
    logger.error("Cannot open camera")
    exit()

# Load classifiers
face_classifier = cv.CascadeClassifier(cv.data.haarcascades + "haarcascade_frontalface_default.xml")
smile_cascade = cv.CascadeClassifier(cv.data.haarcascades + 'haarcascade_smile.xml')


# Initialize uploader with callback
def upload_complete_callback(results):
    """Called when a batch upload is complete"""
    if isinstance(results, dict) and 'error' in results:
        logger.error(f"Upload failed: {results['error']}")
    else:
        logger.info(f"Successfully uploaded {len(results)} images to Drive")
        # Here you could clean up the local files if desired
        for result in results:
            if os.path.exists(result['file_path']):
                os.remove(result['file_path'])


# Initialize the Drive uploader
uploader = DriveUploader()


async def send_websocket_message(message):
    """Send a message to the WebSocket server.

    Args:
        message: The message to send (string or JSON object)
    """
    try:
        async with websockets.connect(WEBSOCKET_URI) as websocket:
            if isinstance(message, dict):
                message_str = json.dumps(message)
                await websocket.send(message_str)
                logger.info(f"Sent JSON message: {message_str[:50]}{'...' if len(message_str) > 50 else ''}")
            else:
                await websocket.send(message)
                logger.info(f"Sent text message: {message[:50]}{'...' if len(message) > 50 else ''}")

            # Wait for a short time to ensure message is sent
            await asyncio.sleep(0.1)
    except Exception as e:
        logger.error(f"Error sending WebSocket message: {str(e)}")


def send_smile_message(message):
    """Queue a message to be sent via WebSocket.

    Args:
        message: The message to send
    """
    message_queue.put(message)


# WebSocket message sender thread function
def websocket_sender_thread():
    """Thread function to handle sending WebSocket messages without blocking the main thread."""

    async def process_message_queue():
        while True:
            try:
                # Get message from queue (non-blocking)
                try:
                    message = message_queue.get_nowait()
                    await send_websocket_message(message)
                    message_queue.task_done()
                except queue.Empty:
                    # No message available, just continue the loop
                    await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Error in websocket sender thread: {str(e)}")
                await asyncio.sleep(1)  # Wait before retrying

    asyncio.run(process_message_queue())


# Start the WebSocket sender thread
websocket_thread = threading.Thread(target=websocket_sender_thread, daemon=True)
websocket_thread.start()


def image_to_base64(image):
    """Convert OpenCV image to base64 string"""
    _, buffer = cv.imencode('.jpg', image)
    return base64.b64encode(buffer).decode('utf-8')


def detect_bounding_box(vid):
    """Detect faces and smiles in the image"""
    gray_image = cv.cvtColor(vid, cv.COLOR_BGR2GRAY)
    faces = face_classifier.detectMultiScale(gray_image, 1.1, 5, minSize=(50, 50))
    smile_detected = False

    for (x, y, w, h) in faces:
        # Face region
        roi_gray = gray_image[y:y + h, x:x + w]
        roi_color = vid[y:y + h, x:x + w]

        # Detect smiles
        smiles = smile_cascade.detectMultiScale(roi_gray, 1.7, 22, minSize=(25, 25))

        if len(smiles) > 0:
            smile_detected = True

    return faces, smile_detected


def handle_upload_batch():
    """Process the current batch of images for upload"""
    global upload_batch

    if len(upload_batch) > 0:
        # Make a copy of the current batch
        files_to_upload = upload_batch.copy()
        upload_batch = []  # Clear the batch

        # Queue the upload without waiting
        uploader.upload_files(
            file_paths=files_to_upload,
            folder_id=DRIVE_FOLDER_ID,
            callback=upload_complete_callback
        )
        logger.info(f"Queued {len(files_to_upload)} files for upload")


# Main loop variables
last_smile = False
last_timestamp = 0
upload_counter = 0

# Setup display window
window_name = "Image2Logo"
cv.namedWindow(window_name, cv.WINDOW_NORMAL | cv.WINDOW_KEEPRATIO)

try:
    # Main processing loop
    while True:
        # Read frame
        result, video_frame = cap.read()
        if not result:
            logger.error("Failed to read from camera")
            break

        # Flip frame horizontally (mirror effect)
        video_frame = cv.flip(video_frame, 1)

        # Detect faces and smiles
        faces, smile_detected = detect_bounding_box(video_frame)

        # Get current timestamp
        timestamp = cv.getTickCount() / cv.getTickFrequency()

        # Handle smile change with debouncing (minimum 1 second between state changes)
        if smile_detected != last_smile and timestamp - last_timestamp > 1:
            # Save image
            upload_counter += 1

            image_frontend = "smile_detected.jpg"
            image_filename = f"smile_detected{upload_counter}.jpg"

            cv.imwrite(image_frontend, video_frame)
            cv.imwrite(image_filename, video_frame)

            # Add to upload batch
            upload_batch.append(image_filename)

            # Record state change
            last_smile = smile_detected
            last_timestamp = timestamp

            # If smile detected, send websocket message
            if smile_detected:
                # Convert image to base64 for websocket
                image_base64 = image_to_base64(video_frame)

                # Send via websocket
                send_smile_message({
                    "event": "smile_status",
                    "timestamp": str(timestamp),
                    "detected": smile_detected,
                    "image": image_base64
                })

            # If we've reached the batch size, handle the upload
            if len(upload_batch) >= BATCH_SIZE:
                handle_upload_batch()

        # Display status on frame
        status_text = "Smile Detected!" if smile_detected else "No Smile"
        batch_text = f"Batch: {len(upload_batch)}/{BATCH_SIZE}"

        cv.putText(
            video_frame,
            status_text,
            (10, 30),
            cv.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 0, 255) if smile_detected else (255, 0, 0),
            2
        )

        cv.putText(
            video_frame,
            batch_text,
            (10, 60),
            cv.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )

        # Show the frame
        cv.imshow(window_name, video_frame)
        cv.setWindowProperty(window_name, cv.WND_PROP_TOPMOST, 1)

        # Check for key press to exit
        if cv.waitKey(1) & 0xFF == ord("q"):
            break

except KeyboardInterrupt:
    logger.info("Program interrupted by user")
except Exception as e:
    logger.error(f"Error in main loop: {str(e)}")
finally:
    # Final upload of any remaining images
    if len(upload_batch) > 0:
        handle_upload_batch()

    # Clean up
    logger.info("Stopping uploader...")
    uploader.stop()

    # Release camera and close windows
    cap.release()
    cv.destroyAllWindows()

    logger.info("Program terminated")