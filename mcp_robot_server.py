from __future__ import annotations

import io
import logging
from typing import List, Optional, Union

import numpy as np
from PIL import Image as PILImage

from mcp.server.fastmcp import FastMCP, Image

from robot_controller import RobotController
from config import robot_config

import atexit
import traceback
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s MCP_Server %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Initialise FastMCP server
# -----------------------------------------------------------------------------

mcp = FastMCP(
    name="SO-ARM101 Robot Controller",
    host = '0.0.0.0',
    port = 4001
)

# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------

_robot: Optional[RobotController] = None
_initialized_with_instructions = False

def _np_to_mcp_image(arr_rgb: np.ndarray, crop: tuple | None = None) -> Image:
    """Convert a numpy RGB image to MCP image format.
    crop: (x1, x2, y1, y2) in pixels, e.g. (1280, 1920, 600, 1080)
    """
    if crop is not None:
        x1, x2, y1, y2 = crop
        arr_rgb = arr_rgb[y1:y2, x1:x2]
    pil_img = PILImage.fromarray(arr_rgb)
    with io.BytesIO() as buf:
        pil_img.save(buf, format="JPEG")
        raw_data = buf.getvalue()
    return Image(data=raw_data, format="jpeg")

def get_robot() -> RobotController:
    """Lazy-initialise the global RobotController instance.

    We avoid creating the controller at import time so the MCP Inspector can
    start even if the hardware is not connected. The first tool/resource call
    that actually needs the robot will trigger the connection.
    """
    global _robot
    if _robot is None:   
        try:
            _robot = RobotController()
            logger.info(f"RobotController initialized.")

        except Exception as e:
            logger.error(f"MCP: FATAL - Error initializing robot: {e}", exc_info=True)
            raise SystemExit(f"MCP Server cannot start: RobotController failed to initialize ({e})")
            
    return _robot

def get_state_with_images(result_json: dict, cameras: Optional[set] = None, is_movement: bool = False) -> List[Union[Image, dict, list]]:
    """Combine robot state with camera images into a unified response format.
    Returns a list containing:
    1. MCP images from all available cameras
    2. JSON with robot state and operation results

    Args:
        result_json: The operation result in JSON format
        cameras: Set of camera names to include in the response
        is_movement: If True, adds a small delay before capturing images to ensure they're current
    """

    camera_names = list(robot_config.lerobot_config.get("cameras", {}).keys())
    if cameras is not None:
        camera_names = [name for name in camera_names if name in cameras]

    robot = get_robot()
    try:
        if is_movement:
            time.sleep(1.0)
        
        raw_imgs = robot.get_camera_images(camera_names)
        
        if not raw_imgs:
            if camera_names:
                logger.warning("MCP: No Camera Images Available.")
                return [result_json, "Warning: No Camera Images Available."]
            return [result_json]

        CAMERA_CROPS = {
            "base": (160, 800, 256, 736), #(160, 800, 256, 736)
            "wrist": (220, 860, 144, 624), #(220, 860, 144, 624)
            "top": (256, 896, 144, 624), #(256, 896, 144, 624)
        }
        mcp_images = [_np_to_mcp_image(img, crop=CAMERA_CROPS.get(name)) for name, img in raw_imgs.items()]

        result_json["robot_state"] = result_json["robot_state"]["human_readable_state"]

        return [result_json] + mcp_images
    except Exception as e:
        logger.error(f"Error getting camera images: {str(e)}")
        logger.error(traceback.format_exc())

        return [result_json] + ["Error getting camera images"]

# -----------------------------------------------------------------------------
# Tools – read-only
# -----------------------------------------------------------------------------

# Can be resource instead but some clients support only tools
# @mcp.resource("robot://description")
@mcp.tool(description="Get a description of the robot and instructions for the user. Run it before using any other tool.")
def get_initial_instructions() -> str:
    global _initialized_with_instructions
    _initialized_with_instructions = True
    return robot_config.robot_description

@mcp.tool(description="Get current robot state with images from all cameras. Returns list of objects: json with results of the move and current state of the robot and images from all cameras")
def get_robot_state():
    global _initialized_with_instructions
    
    # Block access if get_initial_instructions hasn't been called yet
    if not _initialized_with_instructions:
        error_msg = "❌ ERROR: get_initial_instructions Not Called Yet."
        logger.warning("MCP: get_robot_state Tool Blocked: get_initial_instructions Not Called Yet")
        return [{"status": "error", "message": error_msg}]
    
    robot = get_robot()
    move_result = robot.get_current_robot_state()
    result_json = move_result.to_json()
    logger.info(f"MCP: get_robot_state outcome: {result_json.get('status', 'success')}, Msg: {move_result.msg}")
    return get_state_with_images(result_json, is_movement=False)

# -----------------------------------------------------------------------------
# Tools – actuation
# -----------------------------------------------------------------------------

@mcp.tool(
        description="""
        Move the robot with intuitive controls.
        Args:
            move_gripper_up_mm (float, optional): Distance to move gripper up in mm
            move_gripper_down_mm (float, optional): Distance to move gripper down in mm
            move_gripper_forward_mm (float, optional): Distance to move gripper forward in mm
            move_gripper_backward_mm (float, optional): Distance to move gripper backward in mm
            tilt_gripper_down_angle (float, optional): Angle to tilt gripper down in degrees
            tilt_gripper_up_angle (float, optional): Angle to tilt gripper up in degrees
            rotate_gripper_counterclockwise_angle (float, optional): Angle to rotate gripper counterclockwise in degrees
            rotate_gripper_clockwise_angle (float, optional): Angle to rotate gripper clockwise in degrees
            rotate_robot_left_angle (float, optional): Angle to rotate entire robot counterclockwise/left in degrees
            rotate_robot_right_angle (float, optional): Angle to rotate entire robot clockwise/right in degrees
        Expected input format:
        {
            "move_gripper_up_mm": "10",
            "move_gripper_forward_mm": "5",
            "tilt_gripper_down_angle": "10",
            "rotate_gripper_clockwise_angle": "15",
            "rotate_robot_left_angle": "15"
        }
        Returns:
            list: List containing:
                - JSON object with:
                    - status: Optional status in case of error
                    - message: Optional message
                    - warnings: Optional list of any warnings
                    - robot_state: Current robot state in human readable format
                - Camera images
    """
        )
def move_robot(
    move_gripper_up_mm=None,
    move_gripper_down_mm=None,
    move_gripper_forward_mm=None,
    move_gripper_backward_mm=None,
    tilt_gripper_down_angle=None,
    tilt_gripper_up_angle=None,
    rotate_gripper_counterclockwise_angle=None,
    rotate_gripper_clockwise_angle=None,
    rotate_robot_left_angle=None,
    rotate_robot_right_angle=None
):
    global _initialized_with_instructions

    if not _initialized_with_instructions:
        error_msg = "ERROR: get_initial_instructions Not Called Yet."
        logger.warning("MCP: move_robot Tool Blocked: get_initial_instructions Not Called Yet")
        return [{"status": "error", "message": error_msg}]
    
    robot = get_robot()
    logger.info(f"MCP Tool: move_robot received: up={move_gripper_up_mm}, down={move_gripper_down_mm}, "
                f"fwd={move_gripper_forward_mm}, bwd={move_gripper_backward_mm}, "
                f"tilt_down={tilt_gripper_down_angle}, tilt_up={tilt_gripper_up_angle}, "
                f"grip_ccw={rotate_gripper_counterclockwise_angle}, grip_cw={rotate_gripper_clockwise_angle}, "
                f"robot_left={rotate_robot_left_angle}, robot_right={rotate_robot_right_angle}")

    move_params = {
        "move_gripper_up_mm": float(move_gripper_up_mm) if move_gripper_up_mm is not None else None,
        "move_gripper_down_mm": float(move_gripper_down_mm) if move_gripper_down_mm is not None else None,
        "move_gripper_forward_mm": float(move_gripper_forward_mm) if move_gripper_forward_mm is not None else None,
        "move_gripper_backward_mm": float(move_gripper_backward_mm) if move_gripper_backward_mm is not None else None,
        "tilt_gripper_down_angle": float(tilt_gripper_down_angle) if tilt_gripper_down_angle is not None else None,
        "tilt_gripper_up_angle": float(tilt_gripper_up_angle) if tilt_gripper_up_angle is not None else None,
        "rotate_gripper_counterclockwise_angle": float(rotate_gripper_counterclockwise_angle) if rotate_gripper_counterclockwise_angle is not None else None,
        "rotate_gripper_clockwise_angle": float(rotate_gripper_clockwise_angle) if rotate_gripper_clockwise_angle is not None else None,
        "rotate_robot_left_angle": float(rotate_robot_left_angle) if rotate_robot_left_angle is not None else None,
        "rotate_robot_right_angle": float(rotate_robot_right_angle) if rotate_robot_right_angle is not None else None,
    }
    
    camera_angles = ["base", "wrist", "top"]
    if rotate_robot_left_angle is not None or rotate_robot_right_angle is not None:
        camera_angles = ["base","wrist"]
    elif move_gripper_forward_mm is not None or move_gripper_backward_mm is not None:
        camera_angles = ["base","wrist"]
    elif move_gripper_up_mm is not None or move_gripper_down_mm is not None:
        camera_angles = ["base", "wrist"]

    # Filter out None values to pass only specified arguments to the robot controller method
    actual_move_params = {k: v for k, v in move_params.items() if v is not None}
    
    if not actual_move_params:
        current_state_result = robot.get_current_robot_state()
        result_json = current_state_result.to_json()
        result_json["message"] = "No movement parameters provided to move_robot tool."
        logger.info(f"MCP: move_robot outcome: {result_json.get('status', 'success')}, Msg: {result_json.get('message', '')}")
        return get_state_with_images(result_json, cameras=camera_angles, is_movement=False)

    move_execution_result = robot.execute_intuitive_move(**actual_move_params)
    result_json = move_execution_result.to_json()
    
    logger.info(f"MCP: move_robot final outcome: {result_json.get('status', 'success')}, Msg: {result_json.get('message', '')}, Warnings: {len(result_json.get('warnings', []))}")
    
    return get_state_with_images(result_json, cameras=camera_angles, is_movement=True)

@mcp.tool(description="Control the robot's gripper openness from 0% (completely closed) to 100% (completely open). Expected input format: {gripper_openness_pct: '50'}. Returns list of objects: json with results of the move and current state of the robot and images from all cameras")
def control_gripper(gripper_openness_pct):
    global _initialized_with_instructions

    if not _initialized_with_instructions:
        error_msg = "ERROR: get_initial_instructions Not Called Yet."
        logger.warning("MCP: control_gripper Tool Blocked: get_initial_instructions Not Called Yet")
        return [{"status": "error", "message": error_msg}]
    
    robot = get_robot()
    
    try:
        openness = float(gripper_openness_pct)
        logger.info(f"MCP Tool: control_gripper called with openness={gripper_openness_pct}%")
        
        move_result = robot.set_joints_norm({'gripper': openness}, False)
        result_json = move_result.to_json()
        logger.info(f"MCP: control_gripper outcome: {result_json.get('status', 'success')}, Msg: {move_result.msg}, Warnings: {len(move_result.warnings)}")
        return get_state_with_images(result_json, cameras=[], is_movement=True)
        
    except (ValueError, TypeError) as e:
        logger.error(f"MCP: control_gripper received invalid input: {gripper_openness_pct}, error: {str(e)}")
        return {"status": "error", "message": f"Invalid gripper openness value: {str(e)}"}

# -----------------------------------------------------------------------------
# Graceful shutdown
# -----------------------------------------------------------------------------

def _cleanup():
    """Disconnect from hardware on server shutdown."""
    global _robot
    if _robot is not None:
        try:
            _robot.disconnect()
        except Exception as e_disc:
            logger.error(f"MCP: Exception during _robot.disconnect(): {e_disc}", exc_info=True)

atexit.register(_cleanup)

# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info("Starting MCP Robot Server...")
    try:
        mcp.run()
    except SystemExit as e:
        logger.error(f"MCP Server failed to start: {e}")
    except Exception as e_main:
        logger.error(f"MCP Server CRITICAL RUNTIME ERROR: {e_main}", exc_info=True) 
