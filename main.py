import cv2
import mediapipe as mp
import pygame
import time

pygame.init()

screenSize = (680, 480)
screen = pygame.display.set_mode(screenSize)
clock = pygame.time.Clock()
running = True

BaseOptions = mp.tasks.BaseOptions
PoseLandmarker = mp.tasks.vision.PoseLandmarker
PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
PoseLandmarkerResult = mp.tasks.vision.PoseLandmarkerResult
VisionRunningMode = mp.tasks.vision.RunningMode

capture = cv2.VideoCapture(2)

model_path = './model/pose_landmarker_lite.task'

left_shoulder = 0

# Create a pose landmarker instance with the live stream mode:
def print_result(result: PoseLandmarkerResult, output_image: mp.Image, timestamp_ms: int):
    if len(result.pose_landmarks) >= 1:
        global left_shoulder

        left_shoulder = result.pose_landmarks[0][11]

options = PoseLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=model_path),
    running_mode=VisionRunningMode.LIVE_STREAM,
    result_callback=print_result)

with PoseLandmarker.create_from_options(options) as landmarker:
    timestamp = 0
    while True:
        ret, frame = capture.read() # ret:camera 이상 여부, frame : 현재 시점의 frame
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
        landmarker.detect_async(mp_image, timestamp)
        timestamp += 33

        time.sleep(33 / 1000)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                break
        
        screen.fill('white')
        if left_shoulder != 0:
            pygame.draw.circle(screen, [255, 0, 0], [screenSize[0] * left_shoulder.x, screenSize[1] * left_shoulder.y], 10)
            print(left_shoulder.x, left_shoulder.y)

        pygame.display.flip()

