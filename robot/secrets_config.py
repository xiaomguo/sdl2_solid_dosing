"""
Configuration module for loading secrets from my_secrets.py or environment variables.
"""
import os

def get_secret(secret_name, default_value=None, env_var_name=None):
    """
    Get a secret value from my_secrets.py or environment variable.
    
    Args:
        secret_name: Name of the variable in my_secrets.py
        default_value: Default value if not found
        env_var_name: Environment variable name (if different from secret_name)
    
    Returns:
        The secret value
    """
    try:
        from . import my_secrets
        return getattr(my_secrets, secret_name, default_value)
    except ImportError:
        # Fall back to environment variable
        env_name = env_var_name or secret_name
        return os.getenv(env_name, default_value)

# Convenient accessors for common secrets
def get_robot_ip():
    return get_secret('UR_ROBOT_IP', '192.168.254.19', 'UR_ROBOT_IP')

def get_gripper_port():
    return get_secret('GRIPPER_PORT', 63352, 'GRIPPER_PORT')

def get_balance_ip():
    return get_secret('BALANCE_IP', '192.168.254.83', 'BALANCE_IP')

def get_balance_password():
    return get_secret('BALANCE_PASSWORD', 'PASSWORD', 'BALANCE_PASSWORD')