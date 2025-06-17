from mt_balance import MTXPRBalance
from mt_balance import DosingHeadType
import time

BALANCE_IP = "192.168.254.83"
BALANCE_PASSWORD = "PASSWORD"

balance = MTXPRBalance (host = BALANCE_IP, password = BALANCE_PASSWORD)

# Need to detect automatic dosing head id as next iteration

# Reads values of current dosing head attached
value = balance.read_dosing_head()

# writes to dosing head obv
balance.write_dosing_head(head_type =  DosingHeadType.POWDER, head_id = '085021103153', info_to_write = { 'SubstanceName': 'NaCl', "LotId" : "Slot 1"})

print (value)