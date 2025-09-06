import os
import cv2
import numpy as np
import face_recognition
import base64
from django.shortcuts import render
from django.http import JsonResponse, StreamingHttpResponse
from django.core.files.storage import FileSystemStorage
from detection.models import Criminal, ScanHistory
from django.conf import settings
import uuid
from datetime import datetime
import threading
import time

# Global face encodings
criminal_encodings = []
criminal_names = []

# Global variable to control camera streaming
camera_active = False
camera_lock = threading.Lock()


# Load encodings from DB
def load_criminals_from_db():
    global criminal_encodings, criminal_names
    criminal_encodings.clear()
    criminal_names.clear()

    criminals = Criminal.objects.all()
    for criminal in criminals:
        if criminal.image:  # Criminal has an image
            try:
                img_path = os.path.join(settings.MEDIA_ROOT, str(criminal.image))
                if os.path.exists(img_path):
                    img = face_recognition.load_image_file(img_path)
                    encodings = face_recognition.face_encodings(img)
                    for encoding in encodings:
                        criminal_encodings.append(encoding)
                        criminal_names.append(criminal.name)
            except Exception as e:
                print(f"Error loading {criminal.name}: {str(e)}")


# Load at startup
load_criminals_from_db()


# Common function for matching faces
def identify_face(face_encoding, tolerance=0.5):
    if not criminal_encodings:
        return None, None
    face_distances = face_recognition.face_distance(criminal_encodings, face_encoding)
    best_match_index = np.argmin(face_distances)
    if face_distances[best_match_index] <= tolerance:
        return criminal_names[best_match_index], face_distances[best_match_index]
    return None, None


# Save detection frame with markings
def save_criminal_detection(frame, criminal_name, confidence, face_location=None):
    try:
        detection_dir = os.path.join(settings.MEDIA_ROOT, 'criminal_detections')
        os.makedirs(detection_dir, exist_ok=True)

        marked_frame = frame.copy()

        if face_location:
            top, right, bottom, left = face_location

            dot_size = 2
            dot_spacing = 8
            color = (0, 0, 255)

            for x in range(left, right, dot_spacing):
                cv2.circle(marked_frame, (x, top), dot_size, color, -1)
                cv2.circle(marked_frame, (x, bottom), dot_size, color, -1)

            for y in range(top, bottom, dot_spacing):
                cv2.circle(marked_frame, (left, y), dot_size, color, -1)
                cv2.circle(marked_frame, (right, y), dot_size, color, -1)

            label = f"CRIMINAL: {criminal_name}"
            confidence_text = f"Confidence: {confidence}%"

            cv2.rectangle(marked_frame, (left, top - 60), (right + 100, top), (0, 0, 255), cv2.FILLED)

            cv2.putText(marked_frame, label, (left + 5, top - 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(marked_frame, confidence_text, (left + 5, top - 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

            timestamp_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cv2.rectangle(marked_frame, (10, marked_frame.shape[0] - 40),
                          (300, marked_frame.shape[0] - 10), (0, 0, 0), cv2.FILLED)
            cv2.putText(marked_frame, timestamp_text, (15, marked_frame.shape[0] - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"criminal_{criminal_name}_{timestamp}_{uuid.uuid4().hex[:8]}.jpg"
        filepath = os.path.join(detection_dir, filename)

        cv2.imwrite(filepath, marked_frame)

        relative_path = f"criminal_detections/{filename}"
        ScanHistory.objects.create(
            name=criminal_name,
            image=relative_path,
            confidence=confidence,
            detection_type="real_time_camera"
        )

        return True
    except Exception as e:
        print(f"Error saving criminal detection: {str(e)}")
        return False


# Reload function
def reload_criminal_encodings():
    load_criminals_from_db()


# Add new criminal
def add_criminal(request):
    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description", "")
        image = request.FILES.get("image")

        if name and image:
            try:
                criminal = Criminal.objects.create(
                    name=name,
                    description=description,
                    image=image
                )

                img = face_recognition.load_image_file(image)
                face_encodings = face_recognition.face_encodings(img)
                if not face_encodings:
                    criminal.delete()
                    return JsonResponse({
                        "success": False,
                        "message": "No face detected in the image. Please upload a clear face image."
                    })

                reload_criminal_encodings()

                return JsonResponse({
                    "success": True,
                    "message": f"Criminal '{name}' added successfully!"
                })

            except Exception as e:
                return JsonResponse({
                    "success": False,
                    "message": f"Error adding criminal: {str(e)}"
                })
        else:
            return JsonResponse({
                "success": False,
                "message": "Name and image are required."
            })

    return JsonResponse({
        "success": False,
        "message": "Invalid request method."
    })


# Delete criminal
def delete_criminal(request, criminal_id):
    if request.method == "POST":
        try:
            criminal = Criminal.objects.get(id=criminal_id)
            name = criminal.name
            criminal.delete()
            reload_criminal_encodings()

            return JsonResponse({
                "success": True,
                "message": f"Criminal '{name}' deleted successfully!"
            })

        except Criminal.DoesNotExist:
            return JsonResponse({
                "success": False,
                "message": "Criminal not found."
            })
        except Exception as e:
            return JsonResponse({
                "success": False,
                "message": f"Error deleting criminal: {str(e)}"
            })

    return JsonResponse({
        "success": False,
        "message": "Invalid request method."
    })


# Handle image upload
def detection_page(request):
    result = None
    uploaded_file_url = None
    if request.method == "POST" and request.FILES.get("face"):
        uploaded_file = request.FILES["face"]
        fs = FileSystemStorage()
        filename = fs.save(uploaded_file.name, uploaded_file)
        uploaded_file_url = fs.url(filename)

        img = face_recognition.load_image_file(uploaded_file)
        encodings = face_recognition.face_encodings(img)
        if encodings:
            for encoding in encodings:
                name, distance = identify_face(encoding)
                if name:
                    confidence = round((1 - distance) * 100, 2)
                    result = f"✅ Criminal Detected: {name} (match {confidence}%)"
                    ScanHistory.objects.create(
                        name=name,
                        image=uploaded_file,
                        confidence=confidence,
                        detection_type="upload"
                    )
                    break
            if not result:
                result = "❌ Not a Criminal"
                ScanHistory.objects.create(
                    name="Unknown",
                    image=uploaded_file,
                    detection_type="upload"
                )
        else:
            result = "⚠️ No face detected"
            ScanHistory.objects.create(
                name="No face",
                image=uploaded_file,
                detection_type="upload"
            )
    scans = ScanHistory.objects.all().order_by('-date')
    criminals = Criminal.objects.all()
    return render(request, "detection.html", {
        "result": result,
        "uploaded_file_url": uploaded_file_url,
        "scans": scans,
        "criminals": criminals
    })


# Start/Stop camera
def start_camera(request):
    global camera_active
    with camera_lock:
        camera_active = True
    return JsonResponse({"status": "Camera started"})


def stop_camera(request):
    global camera_active
    with camera_lock:
        camera_active = False
    return JsonResponse({"status": "Camera stopped"})


# Handle single frame from camera
def camera_scan(request):
    if request.method == "POST":
        data_url = request.POST.get("image")
        if data_url:
            try:
                header, encoded = data_url.split(",", 1)
                img_data = base64.b64decode(encoded)
                nparr = np.frombuffer(img_data, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                encodings = face_recognition.face_encodings(rgb_img)
                if encodings:
                    for encoding in encodings:
                        name, distance = identify_face(encoding)
                        if name:
                            confidence = round((1 - distance) * 100, 2)
                            save_criminal_detection(img, name, confidence)
                            return JsonResponse({
                                "status": f"✅ Criminal Detected: {name} (match {confidence}%)",
                                "criminal_detected": True,
                                "criminal_name": name,
                                "confidence": confidence
                            })
                    return JsonResponse({
                        "status": "❌ Not a Criminal",
                        "criminal_detected": False
                    })
                else:
                    return JsonResponse({
                        "status": "⚠️ No face detected",
                        "criminal_detected": False
                    })
            except Exception as e:
                return JsonResponse({
                    "status": f"⚠️ Error: {str(e)}",
                    "criminal_detected": False
                })
    return JsonResponse({
        "status": "⚠️ Invalid request",
        "criminal_detected": False
    })


# Real-time video stream
def video_feed(request):
    def generate():
        global camera_active
        cap = cv2.VideoCapture(0)

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)

        last_detection_time = {}
        detection_cooldown = 10

        try:
            while True:
                with camera_lock:
                    if not camera_active:
                        break

                success, frame = cap.read()
                if not success:
                    time.sleep(0.1)
                    continue

                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                face_locations = face_recognition.face_locations(rgb_frame, model="hog")
                face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

                current_time = time.time()

                for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                    name, distance = identify_face(face_encoding)

                    if name:
                        confidence = round((1 - distance) * 100, 2)
                        color = (0, 0, 255)
                        label = f"CRIMINAL: {name}"

                        last_time = last_detection_time.get(name, 0)
                        if current_time - last_time > detection_cooldown:
                            if save_criminal_detection(frame.copy(), name, confidence, (top, right, bottom, left)):
                                last_detection_time[name] = current_time
                                print(f"Criminal detected and saved: {name} ({confidence}%)")
                    else:
                        color = (0, 255, 0)
                        label = "Unknown"
                        confidence = 0

                    cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                    cv2.rectangle(frame, (left, top - 35), (right, top), color, cv2.FILLED)
                    text = f"{label} ({confidence}%)" if name else label
                    cv2.putText(frame, text, (left + 6, top - 6),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

                status_text = "CRIMINAL DETECTION ACTIVE"
                cv2.rectangle(frame, (10, 10), (300, 40), (0, 0, 0), cv2.FILLED)
                cv2.putText(frame, status_text, (15, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

                ret, buffer = cv2.imencode('.jpg', frame)
                if ret:
                    frame_bytes = buffer.tobytes()
                    try:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                    except BrokenPipeError:
                        print("Client disconnected from video stream")
                        break

                time.sleep(0.03)

        except Exception as e:
            print(f"Video feed error: {str(e)}")
        finally:
            cap.release()
            with camera_lock:
                camera_active = False

    return StreamingHttpResponse(generate(), content_type='multipart/x-mixed-replace; boundary=frame')
