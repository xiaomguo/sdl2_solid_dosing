# Note: Dosing is slow sometimes, especially small amounts (< 5mg), we can edit the tolreances or the dose method itself (OR BOTH)

from mt_balance import MTXPRBalance
from mt_balance import MTXPRBalanceDoors
from mt_balance import MTXPRBalanceDosingError
from mt_balance import WeighingCaptureMode
from .config import get_balance_ip, get_balance_password
import time

balance = MTXPRBalance(host=get_balance_ip(), password=get_balance_password())

# Get input from the user

# substance_name = input ("Enter the name of the substance: ")
substance_name = "NaCl"

# Get the target weight of the substance

# target_weight_mg = float (input ("Enter the target weight in mg: "))
target_weight_mg = 2

# Get robot arm to pick the right substance from the rack

# Insert robot arm code here to pick the right substance (make it a function or class)






# The following tries to auto dose the substance, if dosing error occurs, robot arm to removes the
# vessel, cancels the active dosing, and then reinsert the vessel and tries again

try:
    # Open balance door, get robot arm to insert the vessel
    balance.auto_dose (substance_name = substance_name, target_weight_mg= target_weight_mg)

except MTXPRBalanceDosingError as e:

    balance.cancel_active()
    balance.open_door(MTXPRBalanceDoors.LEFT_OUTER)
    # Insert robot arm code here to remove the vessel (make it a function or class)
    balance.close_door(MTXPRBalanceDoors.LEFT_OUTER)
    balance.zero()

    balance.open_door(MTXPRBalanceDoors.LEFT_OUTER)
    # Insert robot arm code here to insert the vessel (make it a function or class)
    balance.auto_dose(substance_name=substance_name, target_weight_mg=target_weight_mg)













