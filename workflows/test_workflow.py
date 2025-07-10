"""
Simple test script to verify workflow setup and connections.
"""

import sys
from pathlib import Path

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent))

def test_imports():
    """Test if all required modules can be imported."""
    print("Testing imports...")
    
    try:
        from matterlab_balances.mt_balance import MTXPRBalance, MTXPRBalanceDoors, WeighingCaptureMode
        print("✓ Balance modules imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import balance modules: {e}")
        return False
    
    try:
        # Try different possible robot module names
        try:
            from robot.urx_robot import URXRobot
            print("✓ Robot module imported successfully (urx_robot)")
        except ImportError:
            try:
                from robot.robot_control import RobotControl
                print("✓ Robot module imported successfully (robot_control)")
            except ImportError:
                print("⚠ Robot module import failed - you'll need to adjust the import in dosing_workflow.py")
                print("  Available robot modules:")
                import robot
                for item in dir(robot):
                    if not item.startswith('_'):
                        print(f"    - {item}")
    except Exception as e:
        print(f"✗ Error checking robot modules: {e}")
        return False
    
    return True

def test_config():
    """Test if configuration file can be loaded."""
    print("\nTesting configuration...")
    
    try:
        import json
        config_file = Path(__file__).parent / "config" / "workflow_config.json"
        
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
            print("✓ Configuration file loaded successfully")
            print(f"  Balance IP: {config.get('balance', {}).get('ip', 'Not set')}")
            print(f"  Robot IP: {config.get('robot', {}).get('ip', 'Not set')}")
            return True
        else:
            print(f"✗ Configuration file not found: {config_file}")
            return False
    except Exception as e:
        print(f"✗ Failed to load configuration: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing workflow setup...\n")
    
    imports_ok = test_imports()
    config_ok = test_config()
    
    print("\n" + "="*50)
    if imports_ok and config_ok:
        print("✅ All tests passed! You can now run the workflow.")
        print("\nNext steps:")
        print("1. Update the robot import in dosing_workflow.py if needed")
        print("2. Update waypoints in config/workflow_config.json")
        print("3. Add gripper commands where marked with TODO")
        print("4. Run: python workflows/dosing_workflow.py")
    else:
        print("❌ Some tests failed. Please fix the issues above.")
    
    print("="*50)

if __name__ == "__main__":
    main() 