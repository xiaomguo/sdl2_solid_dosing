# Workflows

This directory contains the integration workflows for coordinating robot arm and balance operations.

## Structure

```
workflows/
├── __init__.py                 # Package initialization
├── dosing_workflow.py          # Main dosing workflow
├── test_workflow.py            # Test script to verify setup
├── README.md                   # This file
└── config/
    └── workflow_config.json    # Configuration file
```

## Quick Start

1. **Test your setup:**
   ```bash
   python workflows/test_workflow.py
   ```

2. **Update configuration:**
   - Edit `config/workflow_config.json` with your actual IP addresses and waypoints
   - Update robot waypoints based on your setup

3. **Run the workflow:**
   ```bash
   python workflows/dosing_workflow.py
   ```

## Configuration

The `workflow_config.json` file contains:

- **Balance settings**: IP address and password
- **Robot settings**: IP address and port
- **Waypoints**: Robot positions for different operations
- **Dosing parameters**: Substance name and target amount
- **Safety limits**: Maximum weight and timeout values

## Workflow Steps

The main workflow performs these steps in sequence:

1. **Initialize hardware** - Connect to balance and robot
2. **Open balance door** - Open left door for vial insertion
3. **Place vial** - Robot picks up vial and places it in balance
4. **Close balance door** - Close door to prepare for dosing
5. **Place dosing head** - Robot places dosing head on balance
6. **Start dosing** - Begin automatic dosing process
7. **Return home** - Robot returns to safe position

## Customization

### Adding Robot Commands

In `dosing_workflow.py`, look for TODO comments and add your robot-specific commands:

```python
# Example: Add gripper commands
self.robot.gripper_open()
self.robot.gripper_close()
```

### Updating Waypoints

Edit the waypoints in `config/workflow_config.json`:

```json
{
  "waypoints": {
    "vial_pickup": [x, y, z, rx, ry, rz],
    "vial_place_balance": [x, y, z, rx, ry, rz],
    "dosing_head_pickup": [x, y, z, rx, ry, rz],
    "dosing_head_place": [x, y, z, rx, ry, rz],
    "home_position": [x, y, z, rx, ry, rz]
  }
}
```

### Error Handling

The workflow includes error handling and will stop if any step fails. Check the console output for detailed error messages.

## Troubleshooting

1. **Import errors**: Make sure your robot module is properly imported in `dosing_workflow.py`
2. **Connection errors**: Verify IP addresses and network connectivity
3. **Waypoint errors**: Test robot movements individually before running full workflow
4. **Balance errors**: Ensure balance is properly connected and doors are accessible

## Safety Notes

- Always test waypoints in simulation mode first
- Keep emergency stop accessible during testing
- Verify robot movements don't interfere with balance doors
- Monitor weight limits and timeouts 