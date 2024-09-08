from PyQt5 import QtWidgets
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QThread, pyqtSignal as Signal, pyqtSlot as Slot
import cv2
import mediapipe as mp
import sys
import imutils
import math
import serial
import serial.tools.list_ports  # 시리얼 포트 검색을 위해 추가

screenSize = [int(680 * 3/2), int(480 * 3/2)]

class MyThread(QThread):
    frame_signal = Signal(QImage)
    error_signal = Signal(str)  # 오류 발생 시 메시지를 전달하는 시그널

    def __init__(self, camera_index=0, width=screenSize[0], height=screenSize[1], serial_port=None, baud_rate=9600):
        super().__init__()
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose()
        
        # 시리얼 포트 설정
        if serial_port:
            self.serial_port = serial.Serial(serial_port, baud_rate, timeout=1)
        else:
            self.serial_port = None
        
    def run(self):
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened():
                raise Exception("Camera could not be opened.")
            while self.cap.isOpened():
                ret, frame = self.cap.read()
                if not ret:
                    raise Exception("Failed to capture image from camera.")
                frame = self.process_frame(frame)
                frame = self.cvimage_to_label(frame)
                self.frame_signal.emit(frame)
        except Exception as e:
            self.error_signal.emit(str(e))  # 오류 메시지 전달
            self.cap.release()
            if self.serial_port:
                self.serial_port.close()  # 시리얼 포트 닫기

    def process_frame(self, frame):
        # Mediapipe를 사용하여 프레임에서 포즈를 추출
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(rgb_frame)

        # 양팔의 주요 관절 위치를 빨간 점으로 표시하고, 점 사이를 하얀 선으로 연결
        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark
            left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
            right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
            left_elbow = landmarks[self.mp_pose.PoseLandmark.LEFT_ELBOW]
            right_elbow = landmarks[self.mp_pose.PoseLandmark.RIGHT_ELBOW]
            left_wrist = landmarks[self.mp_pose.PoseLandmark.LEFT_WRIST]
            right_wrist = landmarks[self.mp_pose.PoseLandmark.RIGHT_WRIST]

            # 신뢰도가 높은 경우에만 표시
            if left_shoulder.visibility > 0.5 and right_shoulder.visibility > 0.5:
                self.draw_connections(frame, left_shoulder, left_elbow, left_wrist)
                self.draw_connections(frame, right_shoulder, right_elbow, right_wrist)
                
                # 각도 계산 및 시리얼로 전송
                left_arm_angle = self.calculate_angle(left_shoulder, left_elbow, left_wrist)
                right_arm_angle = self.calculate_angle(right_shoulder, right_elbow, right_wrist)
                self.send_angle_to_arduino(left_arm_angle, right_arm_angle)
        
        frame = cv2.flip(frame, 1)  # 좌우 반전

        return frame

    def draw_connections(self, frame, shoulder, elbow, wrist):
        # 랜드마크 좌표 계산
        height, width, _ = frame.shape
        shoulder_coords = (int(shoulder.x * width), int(shoulder.y * height))
        elbow_coords = (int(elbow.x * width), int(elbow.y * height))
        wrist_coords = (int(wrist.x * width), int(wrist.y * height))

        # 빨간 점 그리기
        cv2.circle(frame, shoulder_coords, 10, (0, 0, 255), -1)
        cv2.circle(frame, elbow_coords, 10, (0, 0, 255), -1)
        cv2.circle(frame, wrist_coords, 10, (0, 0, 255), -1)

        # 점을 연결하는 하얀 선 그리기
        cv2.line(frame, shoulder_coords, elbow_coords, (255, 255, 255), 2)
        cv2.line(frame, elbow_coords, wrist_coords, (255, 255, 255), 2)

    def calculate_angle(self, shoulder, elbow, wrist):
        # 각도 계산 (삼각법 사용)
        shoulder = [shoulder.x, shoulder.y]
        elbow = [elbow.x, elbow.y]
        wrist = [wrist.x, wrist.y]
        
        vector1 = [shoulder[0] - elbow[0], shoulder[1] - elbow[1]]
        vector2 = [wrist[0] - elbow[0], wrist[1] - elbow[1]]
        
        angle_radians = math.atan2(vector2[1], vector2[0]) - math.atan2(vector1[1], vector1[0])
        angle_degrees = math.degrees(angle_radians)
        if angle_degrees < 0:
            angle_degrees += 360
        return angle_degrees

    def send_angle_to_arduino(self, left_angle, right_angle):
        # 각도를 시리얼로 전송
        if self.serial_port:
            message = f"L:{left_angle:.2f},R:{right_angle:.2f}\n"
            self.serial_port.write(message.encode())

    def cvimage_to_label(self, image):
        # 창 크기에 맞춰 이미지 크기 조정
        image = imutils.resize(image, width=self.width, height=self.height)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = QImage(image,
                       image.shape[1],
                       image.shape[0],
                       QImage.Format_RGB888)
        return image

class MainApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.show()
    
    def init_ui(self):
        self.setFixedSize(screenSize[0], screenSize[1])
        self.setWindowTitle("Pose Detection with Camera")

        widget = QtWidgets.QWidget(self)
        layout = QtWidgets.QVBoxLayout()
        widget.setLayout(layout)

        self.label = QtWidgets.QLabel()
        layout.addWidget(self.label)

        self.combo_box = QtWidgets.QComboBox()
        self.detect_cameras()
        layout.addWidget(self.combo_box)

        self.port_combo_box = QtWidgets.QComboBox()  # 시리얼 포트 선택용 콤보박스
        self.detect_serial_ports()
        layout.addWidget(self.port_combo_box)

        self.open_btn = QtWidgets.QPushButton("Open The Camera", clicked=self.open_camera)
        layout.addWidget(self.open_btn)

        self.camera_thread = None

        self.setCentralWidget(widget)
    
    def detect_cameras(self):
        # Assuming maximum of 5 cameras for testing. Increase if needed.
        for index in range(5):
            cap = cv2.VideoCapture(index)
            if cap.isOpened():
                self.combo_box.addItem(f"Camera {index}", index)
            cap.release()

    def detect_serial_ports(self):
        # 사용 가능한 시리얼 포트 검색 및 콤보박스에 추가
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.port_combo_box.addItem(port.device)

    def open_camera(self):
        camera_index = self.combo_box.currentData()
        serial_port = self.port_combo_box.currentText()  # 선택된 시리얼 포트
        if self.camera_thread is not None and self.camera_thread.isRunning():
            self.camera_thread.terminate()
        
        self.camera_thread = MyThread(camera_index, width=screenSize[0], height=screenSize[1], serial_port=serial_port)
        self.camera_thread.frame_signal.connect(self.setImage)
        self.camera_thread.error_signal.connect(self.show_error)  # 에러 시그널 연결
        self.camera_thread.start()

    @Slot(QImage)
    def setImage(self, image):
        self.label.setPixmap(QPixmap.fromImage(image))

    @Slot(str)
    def show_error(self, message):
        error_dialog = QtWidgets.QMessageBox(self)
        error_dialog.setIcon(QtWidgets.QMessageBox.Critical)
        error_dialog.setWindowTitle("Camera Error")
        error_dialog.setText("An error occurred while opening the camera:")
        error_dialog.setInformativeText(message)
        error_dialog.exec_()

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    main_window = MainApp()
    sys.exit(app.exec())
