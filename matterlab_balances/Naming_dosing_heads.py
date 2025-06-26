from mt_balance import MTXPRBalance
from mt_balance import DosingHeadType
import time

try:
    from robot import my_secrets
except ImportError:
    my_secrets = None

balance_ip = getattr(my_secrets, 'BALANCE_IP', '192.168.254.83') if my_secrets else '192.168.254.83'
balance_password = getattr(my_secrets, 'BALANCE_PASSWORD', 'PASSWORD') if my_secrets else 'PASSWORD'

balance = MTXPRBalance(host=balance_ip, password=balance_password)

# Need to detect automatic dosing head id as next iteration

# Reads values of current dosing head attached
value = balance.read_dosing_head()

# writes to dosing head obv
balance.write_dosing_head(head_type =  DosingHeadType.POWDER, head_id = '085021103153', info_to_write = { 'SubstanceName': 'NaCl', "LotId" : "Slot 1"})

print (value)