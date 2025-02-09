import cv2
import numpy as np
from ultralytics import YOLO
import math
import time
import random
import pygame
from pyfirmata import Arduino, util
from datetime import datetime
import json

pygame.mixer.init()
shot_sound = pygame.mixer.Sound("D:/jammer/myGame/sound/blaster.mp3")
model = YOLO("D:/jammer/myGame/yolo8/yolov8n-drone.pt")
model.to('cuda')

camera = cv2.VideoCapture(0)
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
if not camera.isOpened():
    print("Failed to open the camera")
    exit()

drone_image_path = "D:/jammer/myGame/images/drone.png"
with open("background_config.txt", "r") as f:
    background_image_path = f.read().strip()
drone_image = cv2.imread(drone_image_path, cv2.IMREAD_UNCHANGED)
background_image = cv2.imread(background_image_path)

if drone_image is None:
    print("Failed to load the drone image")
    exit()

if background_image is None:
    print("Failed to load the background image")
    exit()

background_image = cv2.resize(background_image, (1280, 720))

drone_rgb = drone_image[:, :, :3]
drone_alpha = drone_image[:, :, 3] if drone_image.shape[2] == 4 else np.ones_like(drone_image[:,:,0])
drone_alpha = cv2.normalize(drone_alpha, None, 0, 1, cv2.NORM_MINMAX)

drone_scale = 0.4
drone_h, drone_w = int(drone_rgb.shape[0] * drone_scale), int(drone_rgb.shape[1] * drone_scale)
drone_rgb = cv2.resize(drone_rgb, (drone_w, drone_h))
drone_alpha = cv2.resize(drone_alpha, (drone_w, drone_h))

board = Arduino('COM12')
servo_x = board.get_pin('d:9:s')
servo_y = board.get_pin('d:10:s')
laser_pin = board.get_pin('d:3:o')

servo_x.write(90)
servo_y.write(70)
laser_pin.write(0)

auto_aim = False
score = 0
crosshair_x = 640
crosshair_y = 360
drone_active = True
frame_w, frame_h = 0, 0
explosion_effect = False
explosion_start_time = 0
explosion_duration = 0.3
explosion_pos = (0, 0)
drone_respawn_delay = 1.0
drone_respawn_time = 0
no_drone_period = False
current_accuracy = 0
accuracy_display_time = 0
accuracy_display_duration = 2.0
use_background = False
zone_message = ""
shots_fired = 0
game_start_time = time.time()
accuracy_list = []

with open("game_settings.txt", "r") as f:
    settings = f.read().strip().split('\n')
    difficulty_level = int(settings[0])
    num_drones = int(settings[1])

def load_calibration(filename='calibration_data.json'):
    with open(filename, 'r') as f:
        calibration_data = json.load(f)
    return calibration_data

def log_game_results(score, shots_fired, accuracy_list, game_duration, difficulty_level, num_drones, auto_aim):
    results = {
        "score": score,
        "shots_fired": shots_fired,
        "accuracy_list": accuracy_list,
        "game_duration": game_duration,
        "difficulty_level": difficulty_level,
        "num_drones": num_drones,
        "auto_aim": auto_aim,
        "timestamp": datetime.now().isoformat()
    }
    with open("game_results.json", "w") as f:
        json.dump(results, f, indent=4)

calibration_data = load_calibration()
servo_x_min = min(point["servo_x"] for point in calibration_data["points"])
servo_x_max = max(point["servo_x"] for point in calibration_data["points"])
servo_y_min = min(point["servo_y"] for point in calibration_data["points"])
servo_y_max = max(point["servo_y"] for point in calibration_data["points"])

def map_angle(value, left_min, left_max, right_min=servo_x_min, right_max=servo_x_max):
    value = max(left_min, min(value, left_max))
    left_span = left_max - left_min
    right_span = right_max - right_min
    value_scaled = float(value - left_min) / float(left_span)
    return round(right_min + (value_scaled * right_span))

def map_angle_y(value, left_min, left_max, right_min=servo_y_min, right_max=servo_y_max):
    value = max(left_min, min(value, left_max))
    left_span = left_max - left_min
    right_span = right_max - right_min
    value_scaled = float(value - left_min) / float(left_span)
    return round(right_min + (value_scaled * right_span))

class DroneMovement:
    def __init__(self, speed_range=(3, 7), drone_count=1):
        self.drone_count = drone_count
        self.drones = [self.create_drone(speed_range) for _ in range(drone_count)]
        self.respawn()
        self.prediction_steps = 5

    def create_drone(self, speed_range):
        return {
            "x": random.randint(drone_w, frame_w - drone_w) if frame_w > 0 else 300,
            "y": random.randint(drone_h, frame_h - drone_h) if frame_h > 0 else 200,
            "angle": random.uniform(0, 2 * math.pi),
            "speed": random.uniform(*speed_range),
            "direction_change_time": time.time() + random.uniform(0.5, 2.0)
        }

    def respawn(self):
        global no_drone_period, drone_respawn_time
        for drone in self.drones:
            drone["x"] = random.randint(drone_w, frame_w - drone_w) if frame_w > 0 else 300
            drone["y"] = random.randint(drone_h, frame_h - drone_h) if frame_h > 0 else 200
            drone["angle"] = random.uniform(0, 2 * math.pi)
            drone["speed"] = random.uniform(3, 7)
            drone["direction_change_time"] = time.time() + random.uniform(0.5, 2.0)
        no_drone_period = True
        drone_respawn_time = time.time() + drone_respawn_delay

    def update(self):
        global no_drone_period, drone_respawn_time
        current_time = time.time()

        if no_drone_period:
            if current_time >= drone_respawn_time:
                no_drone_period = False
            else:
                return None

        for drone in self.drones:
            if current_time > drone["direction_change_time"]:
                drone["angle"] += random.uniform(-math.pi / 4, math.pi / 4)
                drone["speed"] = random.uniform(3, 7) if difficulty_level == 1 else random.uniform(5, 10)
                drone["direction_change_time"] = current_time + random.uniform(0.5, 2.0)

            drone["x"] += math.cos(drone["angle"]) * drone["speed"]
            drone["y"] += math.sin(drone["angle"]) * drone["speed"]

            if drone["x"] < 0 or drone["x"] > frame_w - drone_w:
                drone["angle"] = math.pi - drone["angle"]
                drone["x"] = max(0, min(drone["x"], frame_w - drone_w))
            if drone["y"] < 0 or drone["y"] > frame_h - drone_h:
                drone["angle"] = -drone["angle"]
                drone["y"] = max(0, min(drone["y"], frame_h - drone_h))

        return [(int(drone["x"]), int(drone["y"])) for drone in self.drones]

    def predict_position(self):
        if no_drone_period:
            return [(int(drone["x"]), int(drone["y"])) for drone in self.drones]

        predicted_positions = []
        for drone in self.drones:
            predicted_x = drone["x"]
            predicted_y = drone["y"]
            velocity_x = math.cos(drone["angle"]) * drone["speed"]
            velocity_y = math.sin(drone["angle"]) * drone["speed"]

            for _ in range(self.prediction_steps):
                predicted_x += velocity_x
                predicted_y += velocity_y

                if predicted_x < 0 or predicted_x > frame_w - drone_w:
                    velocity_x *= -1
                    predicted_x = max(0, min(predicted_x, frame_w - drone_w))
                if predicted_y < 0 or predicted_y > frame_h - drone_h:
                    velocity_y *= -1
                    predicted_y = max(0, min(predicted_y, frame_h - drone_h))

            predicted_positions.append((int(predicted_x), int(predicted_y)))

        return predicted_positions

    def get_predicted_center(self):
        return [(pred[0] + drone_w // 2, pred[1] + drone_h // 2) for pred in self.predict_position()]

    def get_current_center(self):
        return [(int(drone["x"] + drone_w // 2), int(drone["y"] + drone_h // 2)) for drone in self.drones]

def calculate_shot_accuracy(shot_x, shot_y, current_center, predicted_center):
    current_distance = math.sqrt((shot_x - current_center[0]) ** 2 + (shot_y - current_center[1]) ** 2)
    predicted_distance = math.sqrt((shot_x - predicted_center[0]) ** 2 + (shot_y - predicted_center[1]) ** 2)
    max_distance = math.sqrt(drone_w ** 2 + drone_h ** 2) / 2

    if predicted_distance < current_distance:
        accuracy = max(0, 100 * (1 - predicted_distance / max_distance))
    else:
        accuracy = max(0, 70 * (1 - current_distance / max_distance))

    return min(100, accuracy)

def draw_crosshair(frame, x, y, size=20, color=(0, 0, 255)):
    cv2.line(frame, (x - size, y), (x + size, y), color, 2)
    cv2.line(frame, (x, y - size), (x, y + size), color, 2)
    cv2.circle(frame, (x, y), 2, color, -1)

def draw_explosion(frame, x, y, radius):
    overlay = frame.copy()
    cv2.circle(overlay, (x, y), radius, (0, 165, 255), -1)
    alpha = 0.5
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

def check_drone_zone(crosshair_x, middle_x):
    if crosshair_x < middle_x:
        return "Warning! Drone destroyed in a high-risk zone. Risk to people or buildings."
    else:
        return "Target destroyed in a safe zone. Continue operation."

def mouse_callback(event, x, y, flags, param):
    global crosshair_x, crosshair_y, drone_active, score, explosion_effect
    global explosion_start_time, explosion_pos, current_accuracy, accuracy_display_time, laser_pin, zone_message

    if event == cv2.EVENT_MOUSEMOVE:
        global shots_fired
        shots_fired += 1   
        crosshair_x = x
        crosshair_y = y
    servo_x.write(map_angle(crosshair_x, 0, frame_w))
    servo_y.write(map_angle_y(crosshair_y, 0, frame_h))
    
    if event == cv2.EVENT_LBUTTONDOWN:
        shot_sound.play()
        laser_pin.write(1)
        time.sleep(1)
        laser_pin.write(0)
        current_center = drone_movement.get_current_center()
        predicted_center = drone_movement.get_predicted_center()

        if auto_aim:
            current_accuracy = 100
            for pred_center in predicted_center:
                if abs(crosshair_x - pred_center[0]) < drone_w // 2 and abs(crosshair_y - pred_center[1]) < drone_w // 2:
                    if current_accuracy > 0:  
                        accuracy_list.append(current_accuracy)
                    score += 1
                    explosion_effect = True
                    explosion_start_time = time.time()
                    explosion_pos = pred_center
                    drone_movement.respawn()
                    if use_background:
                        zone_message = check_drone_zone(crosshair_x, frame_w // 2)
                    break
        else:
            for curr_center in current_center:
                if abs(crosshair_x - curr_center[0]) < drone_w // 2 and abs(crosshair_y - curr_center[1]) < drone_w // 2:
                    current_accuracy = calculate_shot_accuracy(crosshair_x, crosshair_y, curr_center, predicted_center[0])
                    if current_accuracy > 0:  
                        accuracy_list.append(current_accuracy)
                    score += 1
                    explosion_effect = True
                    explosion_start_time = time.time()
                    explosion_pos = curr_center
                    drone_movement.respawn()
                    if use_background:
                        zone_message = check_drone_zone(crosshair_x, frame_w // 2)
                    break
                else:
                    current_accuracy = 0

        accuracy_display_time = time.time()

def handle_keys():
    global crosshair_x, crosshair_y
    
    keys = pygame.key.get_pressed()
    move_speed = 5
    
    if keys[pygame.K_w]:
        crosshair_y = max(0, crosshair_y - move_speed)
    if keys[pygame.K_s]:
        crosshair_y = min(frame_h - 1, crosshair_y + move_speed)
    if keys[pygame.K_a]:
        crosshair_x = max(0, crosshair_x - move_speed)
    if keys[pygame.K_d]:
        crosshair_x = min(frame_w - 1, crosshair_x + move_speed)
    
    if frame_w > 0 and frame_h > 0:
        servo_x.write(map_angle(crosshair_x, 0, frame_w))
        servo_y.write(map_angle_y(crosshair_y, 0, frame_h))

cv2.namedWindow("Drone Hunter")
cv2.setMouseCallback("Drone Hunter", mouse_callback)
drone_movement = DroneMovement(speed_range=(3, 5) if difficulty_level == 1 else (5, 10), drone_count=num_drones)

pygame.init()

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if no_drone_period:
                continue
            shot_sound.play()
            laser_pin.write(1)
            time.sleep(1)
            laser_pin.write(0)

    handle_keys()
    
    if use_background:
        frame = background_image.copy()
    else:
        ret, frame = camera.read()
        if not ret:
            break
        
    frame_h, frame_w = frame.shape[:2]
    
    if drone_active:
        updated_positions = drone_movement.update()
        if updated_positions is not None:
            for i, (x_pos, y_pos) in enumerate(updated_positions):
                roi = frame[y_pos:y_pos + drone_h, x_pos:x_pos + drone_w]
                for c in range(3):
                    roi[:, :, c] = roi[:, :, c] * (1 - drone_alpha) + drone_rgb[:, :, c] * drone_alpha
                frame[y_pos:y_pos + drone_h, x_pos:x_pos + drone_w] = roi
    
    if explosion_effect:
        current_time = time.time()
        if current_time - explosion_start_time < explosion_duration:
            progress = (current_time - explosion_start_time) / explosion_duration
            radius = int(50 * progress)
            draw_explosion(frame, explosion_pos[0], explosion_pos[1], radius)
        else:
            explosion_effect = False

        if use_background and zone_message:
            cv2.putText(frame, zone_message, (frame_w // 2 - 400, frame_h // 2 + 100),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
            
            if time.time() - explosion_start_time > explosion_duration:
                if time.time() - explosion_start_time < explosion_duration + 5:
                    cv2.putText(frame, zone_message, (frame_w // 2 - 400, frame_h // 2 + 100),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
                else:
                    zone_message = ""

    results = model(frame)
    
    if not no_drone_period:
        if auto_aim and drone_active and len(results[0].boxes) > 0:
            drone_predicted_x, drone_predicted_y = drone_movement.predict_position()[0]
            crosshair_x = drone_predicted_x + drone_w // 2
            crosshair_y = drone_predicted_y + drone_h // 2
            
            servo_x.write(map_angle(crosshair_x, 0, frame_w))
            servo_y.write(map_angle_y(crosshair_y, 0, frame_h))
            
            for box in results[0].boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

    draw_crosshair(frame, crosshair_x, crosshair_y)

    cv2.putText(frame, f'Score: {score}', (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    aim_status = "Auto-aim: ON" if auto_aim else "Auto-aim: OFF"
    cv2.putText(frame, aim_status, (10, 60), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    if time.time() - accuracy_display_time < accuracy_display_duration:
        accuracy_text = f"Accuracy: {current_accuracy:.1f}%"
        cv2.putText(frame, accuracy_text, (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    if no_drone_period:
        cv2.putText(frame, "RELOADING...", (frame_w // 2 - 100, frame_h // 2), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)

    cv2.imshow("Drone Hunter", frame)

    key = cv2.waitKey(1)
    if key == ord('q'):
        game_duration = time.time() - game_start_time
        log_game_results(score, shots_fired, accuracy_list, game_duration, difficulty_level, num_drones, auto_aim)
        break
    elif key == ord(' '):
        auto_aim = not auto_aim
    elif key == ord('e'):
        use_background = not use_background

camera.release()
cv2.destroyAllWindows()
pygame.quit()
exit()