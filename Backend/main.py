import asyncio
import json
import logging
import queue
import threading
import cv2 as cv
import websockets

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('smile_detector')

message_queue = queue.Queue()

WEBSOCKET_URI = 'wss://image2logo-b2a51e3b7966.herokuapp.com:443'

cap = cv.VideoCapture(4, cv.CAP_DSHOW)

if not cap.isOpened():
    print("Cannot open camera")
    exit()

face_classifier = cv.CascadeClassifier(cv.data.haarcascades + "haarcascade_frontalface_default.xml")
eye_cascade = cv.CascadeClassifier(cv.data.haarcascades + 'haarcascade_eye.xml')
smile_cascade = cv.CascadeClassifier(cv.data.haarcascades + 'haarcascade_smile.xml')


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


# Function to run the WebSocket message sender in a separate thread
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


def detect_bounding_box(vid):
    gray_image = cv.cvtColor(vid, cv.COLOR_BGR2GRAY)
    rostos = face_classifier.detectMultiScale(gray_image, 1.3, 5, minSize=(40, 40))
    Detectsmile = False

    for (x, y, w, h) in rostos:
        cv.rectangle(vid, (x, y), (x + w, y + h), (0, 255, 0), 4)
        roi_gray = gray_image[y:y + h, x:x + w]
        roi_color = vid[y:y + h, x:x + w]
        smiles = smile_cascade.detectMultiScale(roi_gray, 2.8, 20)

        for (sx, sy, sw, sh) in smiles:
            cv.rectangle(roi_color, (sx, sy), ((sx + sw), (sy + sh)), (0, 0, 255), 2)
            if len(smiles) > 0 and smiles is not None:
                Detectsmile = True
                # # Send a message when a smile is detected




    return rostos, Detectsmile

last_smile = False
while True:

    result, video_frame = cap.read()  # read frames from the video
    if result is False:
        break  # terminate the loop if the frame is not read successfully

    video_frame = cv.flip(video_frame, 1)  # flip the frame horizontally

    faces, smile_detected = detect_bounding_box(
        video_frame
    )  # apply the function we created to the video frame

    # Display status on the frame
    print(smile_detected)
    status_text = "Smile Detected!" if smile_detected else "No Smile"

    if smile_detected != last_smile:
        last_smile = smile_detected
        send_smile_message(
            {
                "event": "smile_status",
                "timestamp": str(cv.getTickCount() / cv.getTickFrequency()),
                "detected": smile_detected
            }
        )

    cv.putText(video_frame, status_text, (10, 30), cv.FONT_HERSHEY_SIMPLEX, 0.7,
               (0, 0, 255) if smile_detected else (255, 0, 0), 2)

    cv.imshow(
        "Image to Logo", video_frame
    )  # display the processed frame in a window named "My Face Detection Project"

    if cv.waitKey(1) & 0xFF == ord("q"):
        break

# Release the capture and close windows
cap.release()
cv.destroyAllWindows()