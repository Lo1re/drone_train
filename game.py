import cv2
import numpy as np
from ultralytics import YOLO
import math
import time
import random
import pygame
from pyfirmata import Arduino, util


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
background_image_path = "D:/jammer/myGame/images/background2.jpg" 
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


board = Arduino('COM7')  
servo_x = board.get_pin('d:9:s')
servo_y = board.get_pin('d:10:s')
laser_pin = board.get_pin('d:3:o')


servo_x.write(90)
servo_y.write(70)
laser_pin.write(0) 

#глобальны змінні
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

class DroneMovement:
    def __init__(self):
        self.respawn()
        self.prev_x = self.x
        self.prev_y = self.y
        self.velocity_x = 0
        self.velocity_y = 0
        self.prediction_steps = 5

    def respawn(self):
        global no_drone_period, drone_respawn_time
        self.x = random.randint(drone_w, frame_w - drone_w) if frame_w > 0 else 300
        self.y = random.randint(drone_h, frame_h - drone_h) if frame_h > 0 else 200
        self.angle = random.uniform(0, 2 * math.pi)
        self.speed = random.uniform(3, 7)
        self.direction_change_time = time.time() + random.uniform(0.5, 2.0)
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
        
        if current_time > self.direction_change_time:
            self.angle += random.uniform(-math.pi/4, math.pi/4)
            self.speed = random.uniform(3, 7)
            self.direction_change_time = current_time + random.uniform(0.5, 2.0)
        
        self.velocity_x = self.x - self.prev_x
        self.velocity_y = self.y - self.prev_y
        self.prev_x = self.x
        self.prev_y = self.y
        
        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed
        
        if self.x < 0 or self.x > frame_w - drone_w:
            self.angle = math.pi - self.angle
            self.x = max(0, min(self.x, frame_w - drone_w))
        if self.y < 0 or self.y > frame_h - drone_h:
            self.angle = -self.angle
            self.y = max(0, min(self.y, frame_h - drone_h))
        
        return int(self.x), int(self.y)

    def predict_position(self):
        if no_drone_period:
            return int(self.x), int(self.y)
        
        predicted_x = self.x
        predicted_y = self.y
        
        for _ in range(self.prediction_steps):
            predicted_x += self.velocity_x
            predicted_y += self.velocity_y
            
            if predicted_x < 0 or predicted_x > frame_w - drone_w:
                self.velocity_x *= -1
                predicted_x = max(0, min(predicted_x, frame_w - drone_w))
            if predicted_y < 0 or predicted_y > frame_h - drone_h:
                self.velocity_y *= -1
                predicted_y = max(0, min(predicted_y, frame_h - drone_h))
        
        return int(predicted_x), int(predicted_y)

    def get_predicted_center(self):
        pred_x, pred_y = self.predict_position()
        return (pred_x + drone_w // 2, pred_y + drone_h // 2)

    def get_current_center(self):
        return (int(self.x + drone_w // 2), int(self.y + drone_h // 2))

def calculate_shot_accuracy(shot_x, shot_y, current_center, predicted_center):
    current_distance = math.sqrt((shot_x - current_center[0])**2 + (shot_y - current_center[1])**2)
    predicted_distance = math.sqrt((shot_x - predicted_center[0])**2 + (shot_y - predicted_center[1])**2)
    max_distance = math.sqrt(drone_w**2 + drone_h**2) / 2
    
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
        crosshair_x = x
        crosshair_y = y
    servo_x.write(map_angle(crosshair_x, 0, frame_w, 110, 52))
    servo_y.write(map_angle(crosshair_y, 0, frame_h, 52, 80))
    if event == cv2.EVENT_LBUTTONDOWN:
        if no_drone_period:
            return

        shot_sound.play()
        laser_pin.write(1)  
        time.sleep(1)  
        laser_pin.write(0)  
        current_center = drone_movement.get_current_center()
        predicted_center = drone_movement.get_predicted_center()

        if auto_aim:
            current_accuracy = 100
            if abs(crosshair_x - predicted_center[0]) < drone_w // 2 and abs(crosshair_y - predicted_center[1]) < drone_h // 2:
                score += 1
                explosion_effect = True
                explosion_start_time = time.time()
                explosion_pos = predicted_center
                drone_movement.respawn()
                if use_background:
                    zone_message = check_drone_zone(crosshair_x, frame_w // 2)
        else:
            if abs(crosshair_x - current_center[0]) < drone_w // 2 and abs(crosshair_y - current_center[1]) < drone_h // 2:
                current_accuracy = calculate_shot_accuracy(crosshair_x, crosshair_y, current_center, predicted_center)
                score += 1
                explosion_effect = True
                explosion_start_time = time.time()
                explosion_pos = current_center
                drone_movement.respawn()
                if use_background:
                    zone_message = check_drone_zone(crosshair_x, frame_w // 2)
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
        servo_x.write(map_angle(crosshair_x, 0, frame_w, 110, 52))
        servo_y.write(map_angle(crosshair_y, 0, frame_h, 52, 80))

def map_angle(value, left_min, left_max, right_min, right_max):
    value = max(left_min, min(value, left_max))
    left_span = left_max - left_min
    right_span = right_max - right_min
    value_scaled = float(value - left_min) / float(left_span)
    return round(max(52, min(110, right_min + (value_scaled * right_span))))

cv2.namedWindow("Drone Hunter")
cv2.setMouseCallback("Drone Hunter", mouse_callback)
drone_movement = DroneMovement()


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
        updated_pos = drone_movement.update()
        
        if updated_pos is not None:
            x_pos, y_pos = updated_pos
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
            cv2.putText(frame, zone_message, (frame_w//2 - 400, frame_h//2+100),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
            
            
            if time.time() - explosion_start_time > explosion_duration:
                if time.time() - explosion_start_time < explosion_duration + 5:  # Показувати 3 секунди
                    cv2.putText(frame, zone_message, (frame_w//2 - 400, frame_h//2+100),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
                else:
                    zone_message = ""  
    
    results = model(frame)
    

    if not no_drone_period:
        if auto_aim and drone_active and len(results[0].boxes) > 0:
            drone_predicted_x, drone_predicted_y = drone_movement.predict_position()
            crosshair_x = drone_predicted_x + drone_w // 2
            crosshair_y = drone_predicted_y + drone_h // 2
            
    
            servo_x.write(map_angle(crosshair_x, 0, frame_w, 110, 53))
            servo_y.write(map_angle(crosshair_y, 0, frame_h, 52, 80))
            
            box = results[0].boxes[0]
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
        cv2.putText(frame, "RELOADING...", (frame_w//2 - 100, frame_h//2), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)

    cv2.imshow("Drone Hunter", frame)

    key = cv2.waitKey(1)
    if key == ord('q'):
        break
    elif key == ord(' '):
        auto_aim = not auto_aim
    elif key == ord('e'): 
        use_background = not use_background

camera.release()
cv2.destroyAllWindows()
pygame.quit()
