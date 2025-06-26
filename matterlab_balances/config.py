"""
Configuration module for loading balance-related secrets.
"""
import os

def get_secret(secret_name, default_value=None, env_var_name=None):
    """
    Get a secret value from robot.my_secrets.py or environment variable.
    
    Args:
        secret_name: Name of the variable in my_secrets.py
        default_value: Default value if not found
        env_var_name: Environment variable name (if different from secret_name)
    
    Returns:
        The secret value
    """
    try:
        # Try to import from the robot package where secrets are stored
        from robot import my_secrets
        return getattr(my_secrets, secret_name, default_value)
    except ImportError:
        # Fall back to environment variable
        env_name = env_var_name or secret_name
        return os.getenv(env_name, default_value)

def get_balance_ip():
    return get_secret('BALANCE_IP', '192.168.254.83', 'BALANCE_IP')

def get_balance_password():
    return get_secret('BALANCE_PASSWORD', 'PASSWORD', 'BALANCE_PASSWORD')