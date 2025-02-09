import cv2
import numpy as np
from pyfirmata import Arduino, util
import json
import time
import subprocess


board = Arduino('COM12')
servo_x = board.get_pin('d:9:s')
servo_y = board.get_pin('d:10:s')
laser_pin = board.get_pin('d:3:o')


servo_x.write(90)
servo_y.write(70)
laser_pin.write(0)

# Global 
crosshair_x = 640
crosshair_y = 360
calibration_points = []
current_point = 0
frame_w = 1280
frame_h = 720

points_to_calibrate = [
    {"pos": (640, 360), "name": "Center"},
    {"pos": (100, 100), "name": "Top Left"},
    {"pos": (1180, 100), "name": "Top Right"},
    {"pos": (100, 620), "name": "Bottom Left"},
    {"pos": (1180, 620), "name": "Bottom Right"}
]

def map_angle(value, left_min, left_max, right_min, right_max):
    value = max(left_min, min(value, left_max))
    left_span = left_max - left_min
    right_span = right_max - right_min
    value_scaled = float(value - left_min) / float(left_span)
    return round(max(52, min(110, right_min + (value_scaled * right_span))))

def save_calibration(calibration_data, filename='calibration_data.json'):
    with open(filename, 'w') as f:
        json.dump(calibration_data, f)

def mouse_callback(event, x, y, flags, param):
    global crosshair_x, crosshair_y, current_point, calibration_points
    
    if event == cv2.EVENT_MOUSEMOVE:
        crosshair_x = x
        crosshair_y = y
        
    servo_x.write(map_angle(crosshair_x, 0, frame_w, 110, 52))
    servo_y.write(map_angle(crosshair_y, 0, frame_h, 52, 80))
    
    if event == cv2.EVENT_LBUTTONDOWN:
        current_angles = {
            "screen_pos": points_to_calibrate[current_point]["pos"],
            "servo_x": map_angle(crosshair_x, 0, frame_w, 110, 52),
            "servo_y": map_angle(crosshair_y, 0, frame_h, 52, 80)
        }
        calibration_points.append(current_angles)
        current_point += 1

def draw_crosshair(frame, x, y, size=20, color=(0, 0, 255)):
    cv2.line(frame, (x - size, y), (x + size, y), color, 2)
    cv2.line(frame, (x, y - size), (x, y + size), color, 2)
    cv2.circle(frame, (x, y), 2, color, -1)

def main():
    global current_point, frame_w, frame_h
    
    camera = cv2.VideoCapture(0)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    if not camera.isOpened():
        print("Failed to open camera")
        return False
    
    laser_pin.write(1)
    
    cv2.namedWindow("Calibration")
    cv2.setMouseCallback("Calibration", mouse_callback)
    
    while current_point < len(points_to_calibrate):
        ret, frame = camera.read()
        if not ret:
            break
            
        frame_h, frame_w = frame.shape[:2]
        
        for i, point in enumerate(points_to_calibrate):
            color = (0, 255, 0) if i == current_point else (128, 128, 128)
            cv2.circle(frame, point["pos"], 10, color, -1)
            cv2.putText(frame, point["name"], 
                       (point["pos"][0] + 15, point["pos"][1]), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        
        draw_crosshair(frame, crosshair_x, crosshair_y)
        cv2.imshow("Calibration", frame)
        
        key = cv2.waitKey(1)
        if key == 27:
            break
            
    laser_pin.write(0)
    
    if current_point >= len(points_to_calibrate):
        calibration_data = {
            "points": calibration_points,
            "frame_width": frame_w,
            "frame_height": frame_h
        }
        save_calibration(calibration_data)
        print("Calibration completed successfully!")
        success = True
    else:
        print("Calibration was cancelled")
        success = False
    
    camera.release()
    cv2.destroyAllWindows()
    
    if success:
        subprocess.run(["python", "menu.py"])  
    
    return success

if __name__ == "__main__":
    main()
