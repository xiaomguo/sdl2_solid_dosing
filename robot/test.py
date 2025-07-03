from robot_control import URController
from find_pos import FindPos
import time

def main():
    ur = URController()
    fp = FindPos()
    rob = URController()


    print("\n--- Testing gripper ---") # test pased

    ur.activate_gripper() #activate
    time.sleep(0.5)
    # ur.gripper_position(0)       # Open
    # time.sleep(0.5)
    # ur.gripper_position(255)     # Close
    # time.sleep(0.5)
    # ur.gripper_position(128)     # Half
    # time.sleep(0.5)

    print("\n--- Testing movej ---")
    # fp.movej([-3.3178, -2.0058, 1.8084, 0.2148, 1.4316, 9.4424])
    # time.sleep(1)


    rob.movej("home_h")
    time.sleep(1)

    # print("\n--- Testing movel (relative move) ---")
    # fp.movel(z=0.02)  # Move up 2 cm
    # time.sleep(1)
    # fp.movel(z=-0.02) # Move back down
    # time.sleep(1)


if __name__ == "__main__":
    main()