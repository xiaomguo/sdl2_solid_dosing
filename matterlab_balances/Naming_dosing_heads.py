from mt_balance import MTXPRBalance
from mt_balance import DosingHeadType
from .config import get_balance_ip, get_balance_password
import time

balance = MTXPRBalance(host=get_balance_ip(), password=get_balance_password())

# Need to detect automatic dosing head id as next iteration

# Reads values of current dosing head attached
value = balance.read_dosing_head()

# writes to dosing head obv
balance.write_dosing_head(head_type =  DosingHeadType.POWDER, head_id = '085021103153', info_to_write = { 'SubstanceName': 'NaCl', "LotId" : "Slot 1"})

print (value)