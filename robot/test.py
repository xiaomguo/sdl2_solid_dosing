from robot_control import URController
from find_pos import FindPos
import time

def main():
    ur = URController()
    fp = FindPos()


    print("\n--- Testing gripper ---")
    ur.gripper_position(0)       # Open
    time.sleep(1)
    ur.gripper_position(255)     # Close
    time.sleep(1)
    ur.gripper_position(128)     # Half

    print("\n--- Testing movej ---")
    fp.movej([-3.0, -2.0, 1.5, -0.5, 1.4, 9.2])
    time.sleep(1)

    print("\n--- Testing movel (relative move) ---")
    fp.movel(z=0.02)  # Move up 2 cm
    time.sleep(1)
    fp.movel(z=-0.02) # Move back down
    time.sleep(1)


if __name__ == "__main__":
    main()