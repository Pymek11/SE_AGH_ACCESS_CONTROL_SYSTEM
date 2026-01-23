import os
import tempfile
import unittest
from unittest.mock import patch

import cv2
import numpy as np
from sqlalchemy import create_engine, insert, select
from sqlalchemy.orm import sessionmaker

from app.models.qr_image import metadata as core_metadata
from app.models.qr_image import employees
from app.services.qr_generator import build_qr_payload, generate_qr_code_blob
import app.services.facial_recognition as facial_recognition


class FakeRecognizer:
    def __init__(self, label: int, confidence: float):
        self._label = label
        self._confidence = confidence

    def predict(self, _face_img):
        return self._label, self._confidence


class MSERecognizer:
    """Deterministic recognizer for tests.

    Mimics OpenCV recognizer API: predict(face_200x200_gray) -> (label, confidence)
    Lower confidence is better.
    """

    def __init__(self, known_faces_200x200_gray: list[np.ndarray]):
        self._known = known_faces_200x200_gray

    def predict(self, face_200x200_gray: np.ndarray):
        if not self._known:
            return -1, float("inf")
        face_f = face_200x200_gray.astype(np.float32)
        best_label = 0
        best_mse = float("inf")
        for i, known in enumerate(self._known):
            diff = face_f - known.astype(np.float32)
            mse = float(np.mean(diff * diff))
            if mse < best_mse:
                best_mse = mse
                best_label = i
        return best_label, best_mse


class StubCascade:
    def __init__(self, boxes: np.ndarray):
        self._boxes = boxes

    def detectMultiScale(self, _img, *_args, **_kwargs):
        return self._boxes


def _fixtures_dir() -> str:
    return os.path.join(os.path.dirname(__file__), "fixtures", "faces")


def _list_face_fixtures() -> list[str]:
    folder = _fixtures_dir()
    if not os.path.isdir(folder):
        return []
    files = []
    for name in os.listdir(folder):
        lower = name.lower()
        if lower.endswith((".jpg", ".jpeg", ".png")):
            files.append(os.path.join(folder, name))
    files.sort(key=lambda p: os.path.basename(p).lower())
    return files


def _fixture_stem(path: str) -> str:
    return os.path.splitext(os.path.basename(path))[0]


def _load_face_image_200x200_gray(path: str) -> np.ndarray:
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise RuntimeError(f"Could not read image fixture: {path}")
    return cv2.resize(img, (200, 200))


def _make_camera_frame_with_face(face_200x200_gray: np.ndarray, x: int = 50, y: int = 60) -> np.ndarray:
    """Create a camera-like BGR frame and paste a face ROI into it.

    We still stub the cascade detector to return the ROI box, but the ROI pixels
    come from a real face photo fixture.
    """
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    face_bgr = cv2.cvtColor(face_200x200_gray, cv2.COLOR_GRAY2BGR)
    frame[y : y + 200, x : x + 200] = face_bgr
    return frame


def _project_root_db_path() -> str:
    return os.path.join(os.getcwd(), "access_control.db")


def _load_employees_from_sqlite_db(db_path: str) -> list[tuple[int, str, bytes, bytes]]:
    """Load employees from a sqlite db file path.

    Returns list of (emp_id, emp_name, emp_qr_code, emp_photo) for rows where all are present.
    """
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                select(
                    employees.c.emp_id,
                    employees.c.emp_name,
                    employees.c.emp_qr_code,
                    employees.c.emp_photo,
                )
                .where(employees.c.emp_name.is_not(None))
                .where(employees.c.emp_qr_code.is_not(None))
                .where(employees.c.emp_photo.is_not(None))
                .order_by(employees.c.emp_id.asc())
            ).all()
        # Normalize to plain tuples
        return [(int(r[0]), str(r[1]), r[2], r[3]) for r in rows]
    finally:
        engine.dispose()


class FacialRecognitionQrDbFlowTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._db_path = os.path.join(self._tmpdir.name, "test_access_control.db")
        self._engine = create_engine(
            f"sqlite:///{self._db_path}",
            connect_args={"check_same_thread": False},
        )
        core_metadata.create_all(self._engine)
        self._SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self._engine)

    def tearDown(self):
        self._engine.dispose()
        self._tmpdir.cleanup()

    def _insert_employee(self, name: str, face_gray_200: np.ndarray) -> None:
        ok, buffer = cv2.imencode(".jpg", face_gray_200)
        if not ok:
            raise RuntimeError("Failed to encode test face image")

        qr_blob = generate_qr_code_blob(name)

        with self._SessionLocal() as db:
            db.execute(
                insert(employees).values(
                    emp_name=name,
                    emp_qr_code=qr_blob,
                    emp_photo=buffer.tobytes(),
                )
            )
            db.commit()

    def _get_db_employees_with_photos_ordered(self) -> tuple[list[str], list[np.ndarray]]:
        """Return (names, faces) from the test DB in deterministic emp_id order."""
        names: list[str] = []
        faces: list[np.ndarray] = []
        with self._SessionLocal() as db:
            rows = db.execute(
                select(employees.c.emp_name, employees.c.emp_photo)
                .where(employees.c.emp_photo.is_not(None))
                .order_by(employees.c.emp_id.asc())
            ).all()

        for emp_name, emp_photo in rows:
            img_array = np.frombuffer(emp_photo, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            faces.append(cv2.resize(img, (200, 200)))
            names.append(emp_name)
        return names, faces

    def _assert_employee_exists(self, name: str) -> None:
        with self._SessionLocal() as db:
            row = db.execute(
                select(employees.c.emp_id, employees.c.emp_qr_code, employees.c.emp_photo)
                .where(employees.c.emp_name == name)
                .order_by(employees.c.emp_id.desc())
            ).first()
        self.assertIsNotNone(row, f"Employee {name!r} not found in employees table")
        self.assertIsNotNone(row[1], f"Employee {name!r} has no emp_qr_code")
        self.assertIsNotNone(row[2], f"Employee {name!r} has no emp_photo")

    def test_all_face_fixtures_are_loadable(self):
        fixtures = _list_face_fixtures()
        if not fixtures:
            raise unittest.SkipTest(
                "No face fixtures found. Add .jpg/.png/.jpeg files under tests/fixtures/faces/."
            )
        print("[fixture] loadable fixtures:")
        for p in fixtures:
            print(f"  - {p}")
            img = _load_face_image_200x200_gray(p)
            self.assertEqual(img.shape, (200, 200))
            self.assertEqual(img.dtype, np.uint8)

    def test_qr_payload_prefix_matches_employee_in_db(self):
        fixtures = _list_face_fixtures()
        if not fixtures:
            raise unittest.SkipTest(
                "No face fixtures found. Add .jpg/.png/.jpeg files under tests/fixtures/faces/."
            )
        print("[fixture] qr/db fixtures:")
        # Insert one employee per fixture and verify QR payload prefix finds the row.
        for fixture in fixtures:
            emp_name = _fixture_stem(fixture)
            print(f"  - {fixture} -> emp_name={emp_name!r}")
            face = _load_face_image_200x200_gray(fixture)
            self._insert_employee(emp_name, face)

            self._assert_employee_exists(emp_name)

            payload = build_qr_payload(emp_name)
            name_prefix = payload.split("|", 1)[0].strip()

            with self._SessionLocal() as db:
                found = db.execute(
                    select(employees.c.emp_name).where(employees.c.emp_name == name_prefix)
                ).scalar()

            self.assertEqual(found, emp_name)

    def test_camera_like_frame_matches_employee_photo_set(self):
        # Use ALL fixtures: insert them to DB, then for each one simulate a camera frame
        # and force the recognizer label to point at that fixture's name.
        fixtures = _list_face_fixtures()
        if not fixtures:
            raise unittest.SkipTest(
                "No face fixtures found. Add .jpg/.png/.jpeg files under tests/fixtures/faces/."
            )
        print("[fixture] face-match fixtures:")
        for fixture in fixtures:
            emp_name = _fixture_stem(fixture)
            face = _load_face_image_200x200_gray(fixture)
            print(f"  - {fixture} -> emp_name={emp_name!r}")
            self._insert_employee(emp_name, face)
            self._assert_employee_exists(emp_name)

        # IMPORTANT: build recognition label->name mapping from DB (employees) ordering.
        known_names, known_faces = self._get_db_employees_with_photos_ordered()
        self.assertGreaterEqual(len(known_names), 1)

        stub_cascade = StubCascade(np.array([[50, 60, 200, 200]]))
        with patch.object(facial_recognition, "FACE_CASCADE", stub_cascade):
            for i, (emp_name, face) in enumerate(zip(known_names, known_faces)):
                frame_bgr = _make_camera_frame_with_face(face, x=50, y=60)
                recognizer = FakeRecognizer(label=i, confidence=45.0)
                final_name, conf, _annotated, face_count = facial_recognition.recognize_and_annotate_frame(
                    frame_bgr,
                    recognizer=recognizer,
                    known_names=known_names,
                    threshold=80.0,
                )
                self.assertEqual(face_count, 1)
                self.assertEqual(final_name, emp_name)
                self.assertLess(conf, 80.0)
                # And ensure the recognized name actually exists in DB employees
                self._assert_employee_exists(final_name)

    def test_camera_like_frame_unknown_when_confidence_high(self):
        fixtures = _list_face_fixtures()
        if not fixtures:
            raise unittest.SkipTest(
                "No face fixtures found. Add .jpg/.png/.jpeg files under tests/fixtures/faces/."
            )
        fixture = fixtures[0]
        print(f"[fixture] unknown-threshold test uses: {fixture}")
        face = _load_face_image_200x200_gray(fixture)
        self._insert_employee("Charlie", face)

        with patch.object(facial_recognition, "SessionLocal", self._SessionLocal):
            _faces, names = facial_recognition.load_faces_from_db()

        frame_bgr = _make_camera_frame_with_face(face, x=10, y=10)
        recognizer = FakeRecognizer(label=0, confidence=200.0)

        stub_cascade = StubCascade(np.array([[10, 10, 200, 200]]))
        with patch.object(facial_recognition, "FACE_CASCADE", stub_cascade):
            final_name, conf, _annotated, face_count = facial_recognition.recognize_and_annotate_frame(
                frame_bgr,
                recognizer=recognizer,
                known_names=names,
                threshold=80.0,
            )

        self.assertEqual(face_count, 1)
        self.assertEqual(final_name, "Unknown")
        self.assertGreaterEqual(conf, 80.0)

    def test_break_in_attempt_using_someone_elses_qr_is_denied(self):
        """Security scenario:

        Attacker presents a valid QR code (target employee identity), but their face
        is different. Access should be denied.

        This test iterates all fixture faces (as camera input) against all fixture
        employee identities (as QR targets) and asserts access is only granted for
        the same person.
        """

        fixtures = _list_face_fixtures()
        if len(fixtures) < 2:
            raise unittest.SkipTest(
                "Need at least 2 face fixtures to test break-in attempts (imposter vs victim)."
            )

        # Seed DB: each fixture becomes an employee with QR+photo.
        print("[fixture] break-in fixtures:")
        for fixture in fixtures:
            emp_name = _fixture_stem(fixture)
            print(f"  - {fixture} -> emp_name={emp_name!r}")
            face = _load_face_image_200x200_gray(fixture)
            self._insert_employee(emp_name, face)
            self._assert_employee_exists(emp_name)

        # Build known faces/names directly from DB (access_control employees table).
        known_names, known_faces = self._get_db_employees_with_photos_ordered()
        self.assertGreaterEqual(len(known_names), 2)
        recognizer = MSERecognizer(known_faces)

        # Force face detection to return a single 200x200 ROI box.
        stub_cascade = StubCascade(np.array([[50, 60, 200, 200]]))

        # For each target identity (QR), try every camera face.
        # Access should only be granted when camera face == target employee.
        with patch.object(facial_recognition, "FACE_CASCADE", stub_cascade):
            for target_index, target_name in enumerate(known_names):
                qr_text = build_qr_payload(target_name)
                qr_name_prefix = (qr_text or "").split("|", 1)[0].strip()

                # Simulate what the app does: QR resolves employee identity by name prefix.
                with self._SessionLocal() as db:
                    resolved = db.execute(
                        select(employees.c.emp_name)
                        .where(employees.c.emp_name == qr_name_prefix)
                        .order_by(employees.c.emp_id.desc())
                    ).scalar()
                self.assertEqual(resolved, target_name)

                print(f"[break-in] QR target employee: {target_name!r} (resolved from qr_prefix={qr_name_prefix!r})")

                for camera_index, camera_name in enumerate(known_names):
                    frame_bgr = _make_camera_frame_with_face(known_faces[camera_index], x=50, y=60)
                    detected_name, conf, _annotated, face_count = facial_recognition.recognize_and_annotate_frame(
                        frame_bgr,
                        recognizer=recognizer,
                        known_names=known_names,
                        # MSE is 0.0 for exact self-match; non-zero for different faces.
                        threshold=1.0,
                    )

                    self.assertEqual(face_count, 1)

                    granted = detected_name == target_name
                    should_grant = camera_index == target_index

                    verdict = "GRANT" if granted else "DENY"
                    print(
                        f"[break-in] camera_face={camera_name!r} compared_to_qr_user={target_name!r} "
                        f"-> detected={detected_name!r} conf={conf:.4f} verdict={verdict}"
                    )

                    if should_grant:
                        self.assertTrue(
                            granted,
                            f"Expected GRANT for target={target_name!r} with camera={camera_name!r} (conf={conf})",
                        )
                    else:
                        self.assertFalse(
                            granted,
                            f"Expected DENY for target={target_name!r} with camera={camera_name!r} (detected={detected_name!r}, conf={conf})",
                        )

    def test_break_in_attempt_against_access_control_db_employees(self):
        """Integration-style check against the real ./access_control.db.

        Uses *DB employees photos* as the camera faces (JPEG blobs) and *DB employees*
        as the QR identities (each QR belongs to an employee). Ensures presenting a
        different employee's QR does not grant access.

        This test is read-only and will be skipped if access_control.db is missing
        or does not contain enough employee rows with photos+qr.
        """

        db_path = _project_root_db_path()
        if not os.path.exists(db_path):
            raise unittest.SkipTest(f"Missing production DB file: {db_path}")

        rows = _load_employees_from_sqlite_db(db_path)
        if len(rows) < 2:
            raise unittest.SkipTest(
                "Need at least 2 employees with emp_name+emp_qr_code+emp_photo in access_control.db"
            )

        # Decode employee photos to grayscale 200x200.
        known_ids: list[int] = []
        known_names: list[str] = []
        known_faces: list[np.ndarray] = []

        print(f"[prod-db] Using employees from: {db_path}")
        for emp_id, emp_name, _qr_blob, photo_blob in rows:
            img_array = np.frombuffer(photo_blob, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            face = cv2.resize(img, (200, 200))
            known_ids.append(emp_id)
            known_names.append(emp_name)
            known_faces.append(face)
            print(f"[prod-db] employee emp_id={emp_id} emp_name={emp_name!r} photo_bytes={len(photo_blob)}")

        if len(known_names) < 2:
            raise unittest.SkipTest("Not enough decodable employee photos in access_control.db")

        recognizer = MSERecognizer(known_faces)
        stub_cascade = StubCascade(np.array([[50, 60, 200, 200]]))

        # Target identity = each employee (represents 'using that person's QR code').
        with patch.object(facial_recognition, "FACE_CASCADE", stub_cascade):
            for target_index, target_name in enumerate(known_names):
                print(f"[prod-db break-in] QR target employee: {target_name!r} (emp_id={known_ids[target_index]})")

                for camera_index, camera_name in enumerate(known_names):
                    frame_bgr = _make_camera_frame_with_face(known_faces[camera_index], x=50, y=60)
                    detected_name, conf, _annotated, face_count = facial_recognition.recognize_and_annotate_frame(
                        frame_bgr,
                        recognizer=recognizer,
                        known_names=known_names,
                        threshold=1.0,
                    )

                    self.assertEqual(face_count, 1)

                    granted = detected_name == target_name
                    should_grant = camera_index == target_index

                    verdict = "GRANT" if granted else "DENY"
                    print(
                        f"[prod-db break-in] camera_face={camera_name!r} compared_to_qr_user={target_name!r} "
                        f"-> detected={detected_name!r} conf={conf:.4f} verdict={verdict}"
                    )

                    if should_grant:
                        self.assertTrue(
                            granted,
                            f"Expected GRANT for target={target_name!r} with camera={camera_name!r} (conf={conf})",
                        )
                    else:
                        self.assertFalse(
                            granted,
                            f"Expected DENY for target={target_name!r} with camera={camera_name!r} (detected={detected_name!r}, conf={conf})",
                        )

    def test_fixture_faces_against_each_real_employee_in_access_control_db(self):
        """Try each fixture face against every real employee in access_control.db.

        Scenario: an attacker uses some random face photo (fixtures) but presents a valid
        employee QR identity. Access should be denied.

        This test is read-only against ./access_control.db.
        """

        fixtures = _list_face_fixtures()
        if not fixtures:
            raise unittest.SkipTest(
                "No fixture faces found under tests/fixtures/faces/. Add at least one .jpg/.png/.jpeg."
            )

        db_path = _project_root_db_path()
        if not os.path.exists(db_path):
            raise unittest.SkipTest(f"Missing production DB file: {db_path}")

        rows = _load_employees_from_sqlite_db(db_path)
        if len(rows) < 1:
            raise unittest.SkipTest(
                "Need at least 1 employee with emp_name+emp_qr_code+emp_photo in access_control.db"
            )

        # Build known faces/names from DB employees.
        known_ids: list[int] = []
        known_names: list[str] = []
        known_faces: list[np.ndarray] = []
        for emp_id, emp_name, _qr_blob, photo_blob in rows:
            img_array = np.frombuffer(photo_blob, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            known_ids.append(emp_id)
            known_names.append(emp_name)
            known_faces.append(cv2.resize(img, (200, 200)))

        if not known_names:
            raise unittest.SkipTest("No decodable employee photos in access_control.db")

        recognizer = MSERecognizer(known_faces)
        stub_cascade = StubCascade(np.array([[50, 60, 200, 200]]))

        print(f"[fixture-vs-prod-db] Using DB: {db_path}")
        print(f"[fixture-vs-prod-db] Employees: {len(known_names)}")
        print(f"[fixture-vs-prod-db] Fixtures: {len(fixtures)}")

        # Very strict threshold: only near-identical images count as a match.
        strict_threshold = 1e-6

        with patch.object(facial_recognition, "FACE_CASCADE", stub_cascade):
            for fixture_path in fixtures:
                fixture_name = _fixture_stem(fixture_path)
                fixture_face = _load_face_image_200x200_gray(fixture_path)
                frame_bgr = _make_camera_frame_with_face(fixture_face, x=50, y=60)

                # Determine what DB employee (if any) this fixture is closest to.
                predicted_label, predicted_mse = recognizer.predict(fixture_face)
                predicted_employee = (
                    known_names[predicted_label] if 0 <= predicted_label < len(known_names) else "Unknown"
                )

                print(
                    f"[fixture-vs-prod-db] fixture={os.path.basename(fixture_path)!r} "
                    f"closest_db_employee={predicted_employee!r} mse={predicted_mse:.6f}"
                )

                for target_index, target_name in enumerate(known_names):
                    detected_name, conf, _annotated, face_count = facial_recognition.recognize_and_annotate_frame(
                        frame_bgr,
                        recognizer=recognizer,
                        known_names=known_names,
                        threshold=strict_threshold,
                    )
                    self.assertEqual(face_count, 1)

                    granted = detected_name == target_name

                    verdict = "GRANT" if granted else "DENY"
                    print(
                        f"[fixture-vs-prod-db] fixture_face={fixture_name!r} compared_to_qr_user={target_name!r} "
                        f"-> detected={detected_name!r} conf={conf:.6f} verdict={verdict}"
                    )

                    # Only allow grant if the fixture is essentially identical to the target's stored photo.
                    should_grant = (
                        predicted_employee == target_name and predicted_mse < strict_threshold
                    )
                    if should_grant:
                        self.assertTrue(granted)
                    else:
                        self.assertFalse(granted)


if __name__ == "__main__":
    unittest.main()
