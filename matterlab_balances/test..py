from mt_balance import MTXPRBalance
from mt_balance import MTXPRBalanceDoors
from mt_balance import WeighingCaptureMode
from .config import get_balance_ip, get_balance_password
import time

balance = MTXPRBalance(host=get_balance_ip(), password=get_balance_password())


# Get the current status of the balance; TRUE = DOOR OPEN, FALSE = DOOR CLOSED
door_status = balance.is_door_open (MTXPRBalanceDoors.LEFT_OUTER)

if door_status == False:
    balance.tare()
    balance.smart_auto_dose (substance_name= "NaCl", target_dose_amount_mg = 0.5)


weight_val, unit, is_stable = balance.get_weight(WeighingCaptureMode.IMMEDIATE)

'''
if weight_val < 0.01:
    print("Vessel not detected, closing doors and zeroing balance")
    balance.close_door(MTXPRBalanceDoors.LEFT_OUTER)
    balance.close_door(MTXPRBalanceDoors.RIGHT_OUTER)
    balance.zero()

    # Insert robot arm code here to insert the vessel

else:
'''
print("Vessel detected, closing doors and taring vessel")

# balance.close_door(MTXPRBalanceDoors.LEFT_OUTER)
# balance.close_door(MTXPRBalanceDoors.RIGHT_OUTER)


# zero it when there is no vessel


# The auto_dosing function does the following:
