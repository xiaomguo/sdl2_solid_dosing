Copy `my_secrets_example.py` to `my_secrets.py` and fill in your secrets.

## Configuration

The robots and balance IP addresses are now configured via the `my_secrets.py` file instead of being hardcoded.

1. Copy `my_secrets_example.py` to `my_secrets.py`
2. Update the IP addresses and passwords in `my_secrets.py` for your environment
3. The configuration will be automatically used by all robot and balance modules

Alternatively, you can set environment variables:
- `UR_ROBOT_IP` - IP address of the UR robot  
- `GRIPPER_PORT` - Port for gripper communication
- `BALANCE_IP` - IP address of the MT balance
- `BALANCE_PASSWORD` - Password for the MT balance
