import urx

class FindPos:
    def __init__(self):
        self.rob = urx.Robot("192.168.254.19")


    def print_lj(self):
        print('{')
        print(f'"l": {[round(x, 4) for x in self.rob.getl()]},')
        print(f'"j": {[round(x,4) for x in self.rob.getj()]}'+'},\n')

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
        self.print_lj()

    def movej(self,
            joints: str,
            vel: float = 1,
            acc: float = 1.4):
        
        self.rob.movej(joints,acc=acc,vel=vel)
        self.print_lj()

    

# rob = urx.Robot("192.168.254.19")
# l = rob.getl()
# j = rob.getj()
# print(f'"l": [{", ".join(f"{x:.4f}" for x in l)}],\n  "j": [{", ".join(f"{x:.4f}" for x in j)}]')


#Socket setingspy
# HOST="192.168.254.19" #replace by the IP address of the UR robot
# PORT=63352 #PORT used by robotiq gripper

# #Socket communication
# with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
#     #open the socket
#     s.connect((HOST, PORT))
#     s.sendall(b'GET POS\n')
#     data = s.recv(2**10)

# #Print finger position
# #Gripper finger position is between 0 (Full open) and 255 (Full close)
# print('Gripper finger position is: ', data)
 

# #gripper = Robotiq_Two_Finger_Gripper(rob)

# #print("Closing gripper...")

# #gripper.gripper_action(255)  # 255 = Fully closed
# #time.sleep(2)

# # balance_prep_pos = [-0.06988253226126798, 0.2161448471383651, 0.16269323687831955, -1.1745723551321567, -1.2630901362519305, 1.2009503381300655]\

# # balance_prep_posj = [2.0608971118927, -1.7893601856627406, -2.047377586364746, 3.67710988103833, -2.7033658663379114, 2.911921739578247]

# # p1 = [-0.11150735819978527, 0.22213332358926602, 0.1327182180444515, -1.248220622871663, -1.2758380331333574, 1.1660097926380657]


# # grip_vial_pos = [-0.22529450636862947, 0.21872444595335971, 0.09228346061664372, -1.1736537291607645, -1.2646698896406534, 1.2003766726955183]

# # ot_vial_pos = [-0.0948698027886696, -0.3361812639803029, 0.1898740620326494, -0.1502011359659618, -2.2602529028816676, 2.1232902705613057]

# # ot_posj=[5.063017845153809, -1.5197177615812798, -2.0921669006347656, 3.5386616426655273, -1.0763614813434046, 3.2224419116973877]

# # p2 = [-0.09499075248889581, -0.279624296544121, 0.20129576303649113, 0.019833447364132492, 2.26022094367661, -2.1617300424368935]

# # balance_prep_pos[2]-=0.02

# # rob.movel(grip_vial_pos, acc=0.05, vel=1)

# # print(grip_vial_pos)

# # rob.close()

# #time.sleep(2)
# #pos = rob.getl()
# #print(pos)



# #pos[2] += 0.05
# #rob.movel(pos)
# #rob.close()