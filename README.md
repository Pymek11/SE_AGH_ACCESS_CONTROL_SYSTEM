# SE_AGH_ACCESS_CONTROL_SYSTEM

This repository contains a minimal Local Web Application for a QR and Biometrics-based Access Control System (prototype).

Run instructions (Windows):

1. Create and activate a virtual environment.

	Recommended on Windows: Python 3.13 (or 3.12). Python 3.14 can pull an
	experimental NumPy build (MinGW) that prints warnings and may be unstable.

```cmd
py -3.13 -m venv .venv
.\.venv\Scripts\activate
```

2. Install dependencies:

```cmd
pip install -r requirements.txt
```

3. Start the server:

```cmd
python -m app.main
```

4. Open a browser and go to `http://localhost:8000` (use Chrome/Edge in kiosk mode if desired).

Notes:
- The app streams MJPEG to the frontend from your default camera. Ensure the camera is accessible.
- `face_recognition` requires `dlib` and may need build tools on Windows. See its project docs if installation fails.

# Access Control System Specification: Technology Stack

This document specifies the architecture and core technologies selected for the QR and Biometrics-based Access Control System.

## 1. ⚙️ System Architecture: Local Web Application

The system is deployed as a **Local Web Application**, running as a server on a dedicated workstation (laptop).

* **Backend (Server):** Handles real-time video processing, biometric verification, and database management. Developed in **Python**.
* **Frontend (Client):** The user interface, accessed via a standard web browser (e.g., Chrome/Edge in Kiosk Mode). Communicates with the Backend via **HTTP API** and **Video Streaming Endpoints**.



---

## 2. 💻 Recommended Technology Stack Summary

| Layer | Technology | Component/Library | Rationale |
| :--- | :--- | :--- | :--- |
| **Backend Framework** | **FastAPI** | Python 3.10+ | High performance, excellent asynchronous support (`async/await`) essential for non-blocking operations. |
| **Server** | **Uvicorn** | ASGI Server | Lightning-fast, production-grade server implementation for running FastAPI. |
| **Frontend** | **HTML5, CSS3, JS (ES6+)** | Fetch API, Bootstrap | Standard web technologies for flexible UI, dynamic updates, and easy styling. |
| **Computer Vision** | **OpenCV** | Python Library | Captures camera frames and streams them efficiently to the browser using **MJPEG** over HTTP. |
| **Biometrics/QR** | **face\_recognition, pyzbar** | Python Libraries | Executes verification logic securely on the backend before sending results to the frontend. |
| **Database/ORM** | **SQLite + SQLAlchemy** | File-based DB + Python ORM | **SQLite** is lightweight and zero-configuration; **SQLAlchemy** provides safe, object-oriented database interaction. |

---

## 3. 🔑 Key Technical Decisions

### Performance and Concurrency

The combination of **FastAPI** (with async support) and **Uvicorn** ensures the backend can handle high-throughput tasks like continuous video streaming and simultaneous database requests efficiently without blocking the user interface.

### Video Streaming

Instead of complex protocols, the system utilizes the low-overhead **MJPEG (Motion JPEG)** standard. **OpenCV** encodes frames as JPEGs, and the backend streams them directly to an `<img`> tag on the HTML frontend, achieving real-time display with minimal complexity.

### Data Management

**SQLite** was chosen for its file-based, zero-configuration nature, making it ideal for a local system deployment. **SQLAlchemy** provides an abstraction layer (ORM), ensuring robust and maintainable database interactions from the Python application.
