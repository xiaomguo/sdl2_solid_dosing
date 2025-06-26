import urx
import socket
import time
import json
from urx.urrobot import RobotException

try:
    from . import my_secrets
except ImportError:
    my_secrets = None

class URController:
    def __init__(self,
                 ur_ip=None,
                 gripper_port=None,
                 location_file="ur3_positions.json"):
        # Use values from my_secrets if available, otherwise use defaults
        if ur_ip is None:
            ur_ip = getattr(my_secrets, 'UR_ROBOT_IP', "192.168.254.19") if my_secrets else "192.168.254.19"
        if gripper_port is None:
            gripper_port = getattr(my_secrets, 'GRIPPER_PORT', 63352) if my_secrets else 63352
        try:
            self.rob = urx.Robot(ur_ip)
            print("UR Robot connected!")
        except Exception as e:
            print(f"Failed to connect to UR Robot: {e}")

        # import ur3_positions.json file
        with open("ur3_positions.json", 'r') as f:
            data = json.load(f)
            self.loc = data["rob_locations"]

        # connect to gripper
        self.gripper_ip = ur_ip
        self.gripper_port = gripper_port

        self.gripper_dist = {
            "open":{"vial": 214, "dose": 165},
            "close":{"vial": 244, "dose": 178}
        }
        # set TCP position
        tcp_pose = [0.0, 0.0, 0.195, 0.0, 0.0, 0.0 ]
        self.rob.set_tcp(tcp_pose)
        # set payload
        weight = 0.82
        center_of_gravity = (-0.006, 0.002, 0.065)
        self.rob.set_payload(weight, center_of_gravity)

        self._rob_loc = None
        self._gripper_item = None
            
    def send_gripper_command(self,command):
        """Send a command to the gripper and print the response."""
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(10)
                s.connect((self.gripper_ip, self.gripper_port))
                s.sendall(command.encode('utf-8') + b'\n')
                data = s.recv(1024)
                print(f"Sent: {command}")
                print("Response:", data.decode(errors="ignore"))
        except Exception as e:
                print("Error:", e)

    def actuvate_gripper(self):
        self.send_gripper_command("SET ACT 1")
        time.sleep(2)

    def gripper_position(self, pos):
        pos = max(0,min(255,pos))
        self.send_gripper_command(f"SET POS {pos} GT01")



    def movej(self,
            pos: str,
            vel: float = 1,
            acc: float = 1.4):
        joints = self.loc[pos]["q"]
        if not joints or len(joints)!=6:
         raise ValueError(f"Invalid joint data for {pos}")
        
        try:
            self.rob.movej(joints, acc=acc, vel=vel)
        except RobotException as e:
            print(f"[Warning] RobotException while moving to '{pos}': {e}")

        self.rob.movej(joints,acc=acc,vel=vel)
        self._rob_loc = pos

    def movel(self,
            x = 0, y = 0, z = 0,
            rx = 0, ry = 0, rz = 0,
            vel = 0.1, acc = 1.2):
        current_pose = self.rob.getl()
        target_pose = [
            current_pose[0] + x,
            current_pose[1] + y,
            current_pose[2] + z,
            current_pose[3] + rx,
            current_pose[4] + ry,
            current_pose[5] + rz
        ]
        self.rob.movel(target_pose, acc=acc, vel=vel)

    def home_h(self):
        self.movej("home")
        self._rob_loc = "home"
    def home_h_2_vial_rack(self):
        if self._rob_loc !="home":
            raise ValueError("start position should be 'home'")
    # if self._gripper_item is not None:
    #     raise ValueError("move to vial rack gripper must be None")
        self.movej("safe_rack_vial")
        self.movej("rack_center")
        self._rob_loc = "rack_center"

    def vial_rack_2_vial(self,release_vial:bool):
        if self._rob_loc !="rack_center":
            raise ValueError("start position should be 'rack_center'")
        if not release_vial:
            if self._gripper_item is not None:
                raise ValueError("move to vial rack gripper must be None")
        
            self.gripper_position(self.gripper_dist["open"]["vial"])
            self.movej("pre_A1vial_grip")
            self.movej("A1vial_grip")
            self.gripper_position(self.gripper_dist["close"]["vial"])
            self.movel(z = 0.08)
            self.movej("safe_rack_vial")

            self._gripper_item = "vial"
            self._rob_loc = "safe_rack_vial"

                         


#define robot positions

# home = []
# pos1 = []
# pos2 = []

# rob.movej(pos1,acc=acc,vel=vel)
# time.sleep(1)
# gripper_position(100)


# rob.movej(pos2,acc=acc,vel=vel)
# time.sleep(1)


# rob.movej(home,acc=acc,vel=vel)
# time.sleep(1)

# def activate_gripper():
#     send_gripper_command("SET ACT 1")

# def open_gripper():
#     send_gripper_command("SET POS 0 GTO1")

# def close_gripper():
#     send_gripper_command("SET POS 255 GTO1")
# rob.close()

# Activate the gripper
# send_gripper_command('SET ACT 1')
# time.sleep(1)

# Set speed and force
# send_gripper_command('SET SPE 255')  # Max speed
# send_gripper_command('SET FOR 150')  # Medium force

# # Close gripper
# print("Closing gripper...")
# send_gripper_command('SET POS 255 GTO1')
# time.sleep(2)

# # Open gripper
# print("Closing gripper...")
# send_gripper_command('SET POS 0 GTO1')
# time.sleep(2)


# def movel(
#         self,
#         pos:str,
#         vel:float = 50,
#         acc: float = None):
#     pose = self.loc[pos]["p"]
#     if not pose or len(pose)!=6:
#         raise ValueError(f"Invalid joint data for {pos}")
#     self.rob.movel(pose, vel=vel, acc=acc)
