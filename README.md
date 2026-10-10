# Drone Hunter Training System

A multimedia training simulator for anti-drone systems operators using AI-powered target detection and tracking. This project combines physical hardware (turret system) with virtual simulation to create an effective training environment for drone detection and neutralization.
<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/90707aa7-8e4a-4817-a968-b99df95ed92d" />
## Overview

The Drone Hunter Training System is designed to help train anti-drone system operators in a safe environment while simulating real combat scenarios. The system uses computer vision and AI to track targets, predict drone movement, and provide feedback on shot accuracy and potential civilian infrastructure risks.

### Key Features

- Dual control modes:
  - Manual targeting with mouse/keyboard controls
  - AI-assisted automatic targeting
- Real-time drone movement simulation with randomized patterns
- Shot accuracy tracking and scoring system
- Civilian infrastructure risk assessment
- Switchable backgrounds (real camera feed or virtual environment)
- Arduino-controlled laser targeting system
- YOLO-based drone detection
- Predictive targeting system

## Hardware Requirements

- Computer with CUDA-capable GPU
- Arduino board (connected to COM7)
- Servo motors (x2)
- Laser module
- USB webcam (or compatible camera)
- Mouse and keyboard for control

## Software Requirements

- Python 3.x
- OpenCV (cv2)
- PyFirmata
- Pygame
- Ultralytics YOLO
- NumPy
- Arduino IDE for initial setup

## Installation

1. Clone the repository
2. Install required Python packages:
```bash
pip install opencv-python pygame pyfirmata ultralytics numpy
```
3. Upload standard firmata sketch to Arduino board
4. Configure hardware connections:
   - Servo X on digital pin 9
   - Servo Y on digital pin 10
   - Laser module on digital pin 3

## File Structure

```
myGame/
├── yolo8/
│   └── yolov8n-drone.pt    # YOLO model for drone detection
├── sound/
│   └── blaster.mp3         # Sound effect for shots
├── images/
│   ├── drone.png          # Drone sprite
│   └── background2.jpg    # Virtual environment background
└── game.py               # Main game script
```

## Usage

1. Start the application:
```bash
python game.py
```

2. Controls:
   - Mouse movement: Aim targeting system
   - Left click: Fire laser
   - WASD keys: Alternative movement controls
   - Spacebar: Toggle auto-aim
   - E: Toggle between camera feed and virtual background
   - Q: Quit application

3. Game Features:
   - Score tracking
   - Accuracy percentage display
   - Auto-aim status indicator
   - Reloading period between shots
   - Hit zone assessment messages

## Safety Features

The system includes several safety-oriented features:
- Risk zone detection for drone neutralization
- Warning messages for high-risk areas
- Safe training environment for operators
- No actual laser emission during training

## Current Development Status

The project is actively being developed with planned features including:
- Multiple difficulty levels
- Dynamic drone behavior patterns
- Multi-drone scenarios
- Enhanced movement prediction algorithms

## Technical Architecture

The system consists of three main components:
1. Physical Hardware:
   - Servo-controlled turret system
   - Laser targeting module
   - Camera input system

2. Software Systems:
   - AI-powered drone detection (YOLO)
   - Movement prediction algorithms
   - User interface and scoring system

3. Control Systems:
   - Arduino-based servo control
   - Manual and automatic targeting modes
   - Real-time position synchronization

## Contributing

This is an active research project. For contribution inquiries, please contact the project maintainers.

## Author

Mykola Rybiak

## Academic Supervisors
- Roman Sosiak - Physics and Computer Science Teacher
- Andrii Hryhorovych - Ph.D., Associate Professor

## License

This project is intended for educational and research purposes only.
