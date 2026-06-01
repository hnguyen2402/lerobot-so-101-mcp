import os
from dataclasses import dataclass, field
from typing import Dict, Tuple, Any, Final
from lerobot.cameras.opencv.configuration_opencv import OpenCVCameraConfig, ColorMode, Cv2Rotation, Cv2Backends

DEFAULT_ROBOT_TYPE : Final[str] = "LeRobot SO-101"
DEFAULT_SERIAL_PORT: Final[str] = "/dev/ttyACM0"

DEFAULT_CAMERA_FPS   : Final[int] = 30
DEFAULT_CAMERA_WIDTH : Final[int] = 1024
DEFAULT_CAMERA_HEIGHT: Final[int] = 768

@dataclass
class RobotConfig:
    """
    Configuration for the robot controller.
    
    This dataclass contains all configuration parameters neseded for robot operation,
    including hardware settings, kinematic parameters, and movement constants.
    """

    lerobot_config: Dict[str, Any] = field(
        default_factory=lambda: {
            "type": DEFAULT_ROBOT_TYPE,
            "port": DEFAULT_SERIAL_PORT,
            "cameras": {
                "base": OpenCVCameraConfig(
                    index_or_path=0,
                    fps=DEFAULT_CAMERA_FPS,
                    width=DEFAULT_CAMERA_WIDTH,
                    height=DEFAULT_CAMERA_HEIGHT,
                    color_mode=ColorMode.RGB,
                    rotation=Cv2Rotation.NO_ROTATION,
                    warmup_s=1,
                    fourcc="MJPG",
                    backend=Cv2Backends.ANY,
                ),
                "wrist": OpenCVCameraConfig(
                    index_or_path=2,
                    fps=DEFAULT_CAMERA_FPS,
                    width=DEFAULT_CAMERA_WIDTH,
                    height=DEFAULT_CAMERA_HEIGHT,
                    color_mode=ColorMode.RGB,
                    rotation=Cv2Rotation.NO_ROTATION,
                    warmup_s=1,
                    fourcc="MJPG",
                    backend=Cv2Backends.ANY,
                ),
                "top": OpenCVCameraConfig(
                    index_or_path=4,
                    fps=60,
                    width=1152,
                    height=768,
                    color_mode=ColorMode.RGB,
                    rotation=Cv2Rotation.ROTATE_180,
                    warmup_s=1,
                    fourcc="MJPG",
                    backend=Cv2Backends.V4L2,
                ),
            },
        }
    )

    MOTOR_NORMALIZED_TO_DEGREE_MAPPING: Dict[str, Tuple[float, float, float, float]] = field(
        default_factory=lambda: {
            "shoulder_pan" : (-94.0, 86.0, 0.0, 180.0),
            "shoulder_lift": (-89.4, 99.4, 0.0, 180.0),
            "elbow_flex"   : (96.5, -92.7, 0.0, 180.0),
            "wrist_flex"   : (-90.0, 90.0, -90.0, 90.0),
            "wrist_roll"   : (100.0, -100.0, -90.0, 90.0),
            "gripper"      : (0.0, 93.1, -45.0, 90.0),
        }
    )

    MOVEMENT_CONSTANTS: Dict[str, Any] = field(
        default_factory=lambda: {
            "DEGREES_PER_STEP"       : 1.5,
            "MAX_INTERPOLATION_STEPS": 150,
            "STEP_DELAY_SECONDS"     : 0.01,
        }
    )

    robot_description: str = ("""
INSTRUCTIONS:
- Follow exactly. No deviations, hallucinations, guesses, or assumptions.
- You control a 5-DOF robot arm with a gripper. Left gripper tip is marked red.
- Forward/backward range: 20 mm to 165 mm. Up/down range: 120 mm to 280 mm.
- The horizontal red stripe on the white wall is 20 cm from the gripper at start. Use this to estimate distance.- 
- Think concisely. No second-guessing completed steps. No "wait", "actually", "but wait", or "let me reconsider".

FORBIDDEN WORDS (using any = task failure):
- "approximately", "roughly", "close enough", "near center", "almost", "centered enough", "acceptable", "sufficient"

SAFETY PROTOCOLS:
- You are in STANDBY. Do NOT execute Step 1 until user types "Pick up" or "Start".
- When asked what you see: get_robot_state → describe the scene and STOP.
- When given an explicit movement command: execute it and STOP. Wait for next command.
- Never act without an explicit command.

CAMERAS (FOV is wide):
- Base (Return Image #1):
    + Mounted at the robot's base. Rotates with the robot.
    + Used for left/right and rotation alignment only.
- Wrist (Return Image #2):
    + Mounted on the robot's gripper. Moves with the gripper.
    + Used for forward/backward alignment only.
- Top (Return Image #3):
    + Mounted on top of the workspace.
    + Used to detect existing object(s) on the workspace.

CAMERA IMAGES:
- Calling control_gripper does not return any images.
- Calling rotate_robot_right_angle or rotate_robot_left_angle will return Base and Wrist camera image only.
- Calling move_gripper_forward_mm or move_gripper_backward_mm will return Base and Wrist camera image only.
- Calling move_gripper_up_mm or move_gripper_down_mm will return Base and Wrist camera image only.
- Calling other tools will return all camera images.

RULES:
- Execute one action at a time. Check the newest images after every action before proceeding.
- Do not reason beyond what the newest images show.
- Do not reconsider a completed step.
- Do not loop. Once a step is complete, move to the next step.
- Never assume a movement succeeded without verifying using the newest images.
- Never move with the gripper near the ground unless grasping the object.
- You can only move the right gripper. The left gripper is fixed.

STEPS (NEVER DEVIATE OR SKIP ANY STEP. DEVIATION OR SKIP = FAILURE):
1. Preparation:
    + Open the gripper to 75%.
    + Tilt the gripper downward 45°.
    + Move upward 8 cm.
2. Rotation Alignment:
    + Look at the Base camera ONLY.
    + Do not move up or down during this step.
    + Do not move backward or forward during this step.
    + After each rotation, check the newest Base camera image.
    + Mentally divide the image into five equal vertical zones: far left, left, center, right, far right.
        * If the object is in the far left zone → rotate left 15°-30°. Do not exceed 30° per rotation.
        * If the object is in the left zone → rotate left 3°-10°. Do not exceed 10° per rotation.
        * If the object is in the far right zone → rotate right 15°-30°. Do not exceed 30° per rotation.
        * If the object is in the right zone → rotate right 3°-10°. Do not exceed 10° per rotation.
        * If the object is exactly in the ABSOLUTE center zone → stop immediately. Go to Step 3.
        * If the object moved farther from the ABSOLUTE center of the Base camera image, you rotated the wrong way. Reverse immediately.
        * You may only rotate a maximum of 4 times: 1 initial rotation (15°-30°) + 3 corrections (3°-10°).
    + Do not proceed to Step 3 until the object is in the ABSOLUTE center zone on the Base camera image.
3. Forward/Backward Alignment:
    + Look at the Wrist camera ONLY.
    + Do not move up or down during this step.
    + Do not rotate left or right during this step.
    + After each movement, check the newest Wrist camera image.
    + Mentally divide the frame into four equal horizontal zones: top, upper-middle, lower-middle, bottom.
        * If the object is in the top zone → move forward in 50-70 mm increments. Do not exceed 70 mm per movement.
        * If the object is in the upper-middle zone → move forward in 10-30 mm increments. Do not exceed 30 mm per movement.
        * If the object is in the bottom zone → move backward in 30-50 mm increments. Do not exceed 50 mm per movement.
        * If the object is in the lower-middle zone → stop immediately. Go to Step 4.
        * If the object moved farther from the lower-middle zone of the Wrist camera image, you moved the wrong way. Reverse immediately.
        * You may only move a maximum of 4 times: 1 initial movement (50-70 mm) + 3 corrections (10-30 mm).
    + Do not proceed to Step 4 until the object is in the lower-middle zone on the Wrist camera image.
4. Final Verification:
    + Condition 1: Check Base camera: object must be in the ABSOLUTE center zone.
    + Condition 2: Check Wrist camera: object must be in the lower-middle zone.
    + If condition 1 fails, go back to Step 2.
    + If condition 2 fails, go back to Step 3.
    + If condition 1 AND condition 2 fail, go back to Step 2.
    + Do not proceed until all two conditions pass.
5. Lower for Grasp:
    + Lower the robot arm 10 cm.
6. Grasp:
    + Close the gripper to 0%.
7. Lift and Verify:
    + Move upward 10 cm.
    + Condition 1: Check Base camera: object must no longer be resting on the platform.
    + Condition 2: Check Wrist camera: object must be visible and held between the gripper fingers.
    + If condition 1 OR condition 2 fails → pickup failed. Open the gripper to 75% and go to Step 2.
    + Do not proceed until all two conditions pass.
8. Drop and Pick another Object:
(Only execute Step 8 if the user explicitly requests picking up an additional object after Step 7 completes)
    + Open the gripper to 75% and repeat Steps 2-7 for the next object.
    + Do not repeat step 1.

LANGUAGE:
    - You are FORBIDDEN from using the following words or phrases:
        + "approximately", "roughly", "close enough", "near center", "almost", "centered enough", "acceptable", "sufficient".
    - Using any of these words = task failure.
""")

    KINEMATIC_PARAMS: Dict[str, Dict[str, Any]] = field(
        default_factory=lambda: {
            "default": {
                "L1"                      : 116.0,  # Shoulder to elbow length (mm)
                "L2"                      : 136.0,  # Elbow to wrist length (mm)
                "BASE_HEIGHT_MM"          : 118.5,
                "SHOULDER_MOUNT_OFFSET_MM": 32.0,
                "ELBOW_MOUNT_OFFSET_MM"   : 4.0,
                "SPATIAL_LIMITS": {
                    "x": (20.0, 165.0),  # Forward/backward limits
                    "z": (120.0, 280.0),   # Up/down limits
                },
                "GRIPPER_DEG_LIMITS"      : (-45, 100),
            }
        }
    )

    PRESET_POSITIONS: Dict[str, Dict[str, float]] = field(
        default_factory=lambda: {
            "1": { "gripper": -35.5, "wrist_roll": 90.0, "wrist_flex": 0.0, "elbow_flex": 0.0, "shoulder_lift": 0.0, "shoulder_pan": 90.0 },
            "2": { "gripper": -35.5, "wrist_roll": 90.0, "wrist_flex": 0.0, "elbow_flex": 45.0, "shoulder_lift": 45.0, "shoulder_pan": 90.0 },
            "3": { "gripper": 68.9, "wrist_roll": 90.0, "wrist_flex": 90.0, "elbow_flex": 45.0, "shoulder_lift": 45.0, "shoulder_pan": 90.0 },
            "4": { "gripper": 68.9, "wrist_roll": 90.0, "wrist_flex": -60.0, "elbow_flex": 20.0, "shoulder_lift": 80.0, "shoulder_pan": 90.0 },
        }
    )

robot_config = RobotConfig()
