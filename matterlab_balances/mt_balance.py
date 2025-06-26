import time
import enum
import base64
import hashlib
import logging
from os import path
from pathlib import Path
from typing import Optional, Any, List, Dict, Tuple, Union

import suds
from suds.client import Client 
from suds.plugin import MessagePlugin 
from suds.sudsobject import Object as SudsObject 
from jinja2 import Template 
import pprp 

BASE_PATH = Path(__file__).parent/"mt_wsdl"
DEFAULT_WSDL_TEMPLATE_NAME = 'MT.Laboratory.Balance.XprXsr.V03.wsdl.jinja2'
DEFAULT_WSDL_OUTPUT_NAME = 'MT.Laboratory.Balance.XprXsr.V03.wsdl' # Generated WSDL

# --- Logging Setup ---
logger = logging.getLogger(__name__)
# Basic logging configuration - customize as needed
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


# --- Custom Exceptions ---
class MTXPRBalanceError(Exception):
    """Base exception for MTXPRBalance errors."""
    def __init__(self, message: str, outcome: Optional[str] = None, error_message: Optional[str] = None, error_state: Optional[str] = None):
        super().__init__(message)
        self.outcome = outcome
        self.error_message = error_message
        self.error_state = error_state

    def __str__(self):
        parts = [super().__str__()]
        if self.outcome:
            parts.append(f"Outcome: {self.outcome}")
        if self.error_message:
            parts.append(f"Service Error: {self.error_message}")
        if self.error_state:
            parts.append(f"Service State: {self.error_state}")
        return " - ".join(parts)

class MTXPRBalanceAuthError(MTXPRBalanceError):
    """Authentication related errors."""
    pass

class MTXPRBalanceConnectionError(MTXPRBalanceError):
    """Connection related errors."""
    pass

class MTXPRBalanceRequestError(MTXPRBalanceError):
    """Errors during a specific service request."""
    pass

class MTXPRBalanceSessionError(MTXPRBalanceError):
    """Session related errors (e.g., invalid session ID)."""
    pass

class MTXPRBalanceDeviceError(MTXPRBalanceError):
    """Errors specific to device operations (e.g., tare, zero, weigh)."""
    pass

class MTXPRDosingHeadError(MTXPRBalanceDeviceError):
    """Errors related to the dosing head."""
    pass

class MTXPRBalanceDosingError(MTXPRBalanceDeviceError):
    """Errors during dosing operations."""
    pass

class MTXPRBalanceDoorError(MTXPRBalanceDeviceError):
    """Errors related to door operations."""
    pass

class MTXPRBalanceNotificationError(MTXPRBalanceError):
    """Errors related to handling notifications."""
    pass


# --- Enums for Balance Control ---
class MTXPRBalanceDoors(enum.Enum):
    LEFT_OUTER = 'LeftOuter'
    RIGHT_OUTER = 'RightOuter'
    LEFT_INNER = 'LeftInner'
    RIGHT_INNER = 'RightInner'
    TOP = 'Top'
    RADIAL = 'Radial'
    FLAP = 'Flap'


class WeighingCaptureMode(enum.Enum):
    """As defined in WSDL: WeighingCaptureMode."""
    STABLE = "Stable"
    IMMEDIATE = "Immediate"
    TIME_INTERVAL = "TimeInterval"
    WEIGHT_CHANGE = "WeightChange"

class WeightDetectionMode(enum.Enum):
    """As defined in WSDL: WeightDetectionMode."""
    ANY_DELTA = "AnyDelta" 
    NEGATIVE_DELTA = "NegativeDelta" 
    POSITIVE_DELTA = "PositiveDelta"

class Unit(enum.Enum):
    """As defined in WSDL: Unit. """
    GRAM = "Gram"
    MILLIGRAM = "Milligram"
    MICROGRAM = "Microgram" 
    KILOGRAM = "Kilogram" 

class DosingHeadType(enum.Enum):
    """As defined in WSDL: DosingHeadType."""
    POWDER = "Powder" 
    LIQUID = "Liquid"

# --- Main Balance Class ---
class MTXPRBalance:
    BASIC_SERVICE = 'BasicHttpBinding_IBasicService'
    SESSION_SERVICE = 'BasicHttpBinding_ISessionService'
    WEIGHING_SERVICE = 'BasicHttpBinding_IWeighingService'
    WEIGHING_TASK_SERVICE = 'BasicHttpBinding_IWeighingTaskService'
    DOSING_AUTOMATION_SERVICE = 'BasicHttpBinding_IDosingAutomationService'
    NOTIFICATION_SERVICE = 'BasicHttpBinding_INotificationService'
    DRAFT_SHIELDS_SERVICE = 'BasicHttpBinding_IDraftShieldsService'
    AUTHENTICATION_SERVICE = 'BasicHttpBinding_IAuthenticationService'
    ADJUSTMENT_SERVICE = 'BasicHttpBinding_IAdjustmentService'
    FEEDER_SERVICE = 'BasicHttpBinding_IFeederService'
    ROUTINE_TEST_SERVICE = 'BasicHttpBinding_IRoutineTestService' 
    TOLERANCE_PROFILE_SERVICE = 'BasicHttpBinding_IToleranceProfileService' 


    SERVICES = [
        BASIC_SERVICE, SESSION_SERVICE, WEIGHING_SERVICE, WEIGHING_TASK_SERVICE,
        DOSING_AUTOMATION_SERVICE, NOTIFICATION_SERVICE, DRAFT_SHIELDS_SERVICE,
        AUTHENTICATION_SERVICE, ADJUSTMENT_SERVICE, FEEDER_SERVICE,
        ROUTINE_TEST_SERVICE, TOLERANCE_PROFILE_SERVICE
    ]

    # Default timeout for synchronous operations (in seconds)
    DEFAULT_SYNC_TIMEOUT = 60
    # Default polling interval for async operations (in seconds)
    DEFAULT_POLL_INTERVAL = 1
    # Default timeout for notification polling (in milliseconds for GetNotifications)
    DEFAULT_NOTIFICATION_POLL_TIMEOUT_MS = 500



    def __init__(self,
                 host: str = "192.168.1.100",  # Default placeholder - configure in my_secrets.py 
                 port: int = 8002, 
                 api_path: str = 'MT/Laboratory/Balance/XprXsr/V03/MT', 
                 wsdl_template_name: str = DEFAULT_WSDL_TEMPLATE_NAME,
                 generated_wsdl_name: str = DEFAULT_WSDL_OUTPUT_NAME,
                 password: str = 'password', 
                 connect_on_init: bool = True):

        self.logger = logger.getChild(self.__class__.__name__)
        self.host = host
        self.port = port
        self.api_path = api_path
        self.wsdl_template_path = BASE_PATH/wsdl_template_name
        self.generated_wsdl_path = BASE_PATH/generated_wsdl_name
        self._password = password
        self.client: Optional[Client] = None
        self._session_id: Optional[str] = None
        self._active_command_ids: set[int] = set()


        if connect_on_init:
            self.connect()

    def _build_wsdl_file(self) -> None:
        """Generates the WSDL file from a template with current host/port."""
        if not self.wsdl_template_path.exists():
            raise FileNotFoundError(f"WSDL template not found: {self.wsdl_template_path}")

        self.generated_wsdl_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.wsdl_template_path) as template_file:
            template_content = template_file.read()
        template = Template(template_content)

        wsdl_content = template.render(host=self.host,
                                       port=self.port,
                                       api_path=self.api_path,
                                       services=self.SERVICES)

        with open(self.generated_wsdl_path, 'w') as wsdl_file:
            wsdl_file.write(wsdl_content)
        self.logger.info(f"WSDL file generated at {self.generated_wsdl_path}")


    def connect(self) -> None:
        """Establishes connection to the balance and opens a session."""
        self._build_wsdl_file() 
        try:
            wsdl_file_uri = self.generated_wsdl_path.as_uri()
            
            self.client = Client(wsdl_file_uri)
            self.logger.info(f"Suds client initialized with WSDL: {wsdl_file_uri}")
        except Exception as e:
            self.logger.error(f"Failed to initialize Suds client: {e}")
            raise MTXPRBalanceConnectionError(f"Suds client initialization failed: {e}") from e

        self.open_session()
        self.logger.info("Successfully connected to the balance and session opened.")

    def _handle_suds_webfault(self, err: suds.WebFault, service_name: str, method_name: str, args: List[Any]) -> Any:
        """Handles Suds WebFault exceptions, attempting to reopen session if necessary."""
        fault_string = str(err.fault.faultstring) if err.fault and err.fault.faultstring else "Unknown Suds WebFault"
        detail = str(err.fault.detail) if err.fault and hasattr(err.fault, 'detail') else "No detail"
        self.logger.error(f"Suds WebFault during {service_name}.{method_name}: {fault_string} - Detail: {detail}")

        if 'SessionIdFault' in detail or (err.fault and err.fault.faultcode and 'SessionIdFault' in str(err.fault.faultcode)): 
            self.logger.warning("SessionIdFault detected. Attempting to re-open session.")
            self._session_id = None 
            try:
                self.open_session()
                method_to_call = getattr(self.client.service[service_name], method_name)
                method_args = args if service_name == self.SESSION_SERVICE and method_name == 'OpenSession' else [self._session_id, *args]
                return method_to_call(*method_args)
            except Exception as retry_err:
                self.logger.error(f"Failed to retry {service_name}.{method_name} after re-opening session: {retry_err}")
                raise MTXPRBalanceSessionError(f"Session error after retry: {retry_err}", error_message=str(retry_err)) from retry_err
        else:
            raise MTXPRBalanceRequestError(f"Suds WebFault: {fault_string}", error_message=detail) from err

    def _request(self, service_name: str, method_name: str, args: Optional[List[Any]] = None,
                include_session_id: bool = True,
                ignore_specific_outcomes: Optional[List[str]] = None
                ) -> SudsObject:
        """
        Helper method to make a request to the web service.
        Handles common error checking and session management.
        """
        if not self.client:
            raise MTXPRBalanceConnectionError("Client not connected. Call connect() first.")

        actual_args = args or []
        method_to_call = getattr(self.client.service[service_name], method_name)

        if include_session_id:
            if not self._session_id:
                self.logger.info("No active session. Opening a new session.")
                self.open_session()
            if not self._session_id: 
                 raise MTXPRBalanceSessionError("Failed to establish a session.")
            final_args = [self._session_id, *actual_args]
        else:
            final_args = actual_args

        self.logger.debug(f"Requesting: {service_name}.{method_name} with args (session_id omitted for brevity if included): "
                          f"{actual_args if include_session_id else final_args}")

        try:
            response = method_to_call(*final_args)
        except suds.WebFault as err:
            return self._handle_suds_webfault(err, service_name, method_name, final_args)
        except suds.transport.TransportError as err:
            self.logger.error(f"TransportError during {service_name}.{method_name}: {err}")
            raise MTXPRBalanceConnectionError(f"Network transport error: {err}") from err
        except Exception as e: 
            self.logger.error(f"Unexpected error during {service_name}.{method_name}: {e}")
            raise MTXPRBalanceError(f"Unexpected error: {e}") from e


        self.logger.debug(f"Response from {service_name}.{method_name}: Outcome='{response.Outcome}'")

        if ignore_specific_outcomes and response.Outcome in ignore_specific_outcomes:
            self.logger.info(f"Request {service_name}.{method_name} had an ignorable outcome: {response.Outcome}. Proceeding.")
        elif response.Outcome != 'Success': 
            err_msg = getattr(response, 'ErrorMessage', 'No error message provided.')
            err_state = getattr(response, 'ErrorState', None)
            self.logger.error(f"Request {service_name}.{method_name} failed. Outcome: {response.Outcome}, Message: {err_msg}, State: {err_state}")
            raise MTXPRBalanceRequestError(
                f"Request {service_name}.{method_name} failed.",
                outcome=response.Outcome,
                error_message=err_msg,
                error_state=str(err_state) if err_state else None
            )
        
        if hasattr(response, 'CommandId'):
            self._active_command_ids.add(response.CommandId)
            self.logger.info(f"Asynchronous command started: ID {response.CommandId} for {service_name}.{method_name}")


        return response


    def open_session(self) -> None: 
        """Opens a new session with the balance."""
        self.logger.debug("Attempting to open a new session.")
        session_response_obj = self._request(self.SESSION_SERVICE, 'OpenSession', include_session_id=False)
        try:
            decrypted_id = self.decrypt_session_id(self._password, session_response_obj.SessionId, session_response_obj.Salt)
            
            if not decrypted_id: 
                self.logger.error("Decryption process returned an empty or None session ID.")
                self._session_id = None 
                raise MTXPRBalanceAuthError('Decryption failed to produce a session ID.')
            
            self._session_id = decrypted_id
            self.logger.info(f"Session opened successfully. Session ID (decrypted): {'*' * len(self._session_id)}")

        except UnicodeEncodeError as error: # Catching error from decrypt_session_id
            self.logger.error(f"Authentication error: password/decryption issue in decrypt_session_id. {error}")
            self._session_id = None # Ensure session_id is None on failure
            raise MTXPRBalanceAuthError('Authentication error: invalid password or decryption issue') from error
        except MTXPRBalanceAuthError: # If decrypt_session_id raises custom auth error
            self._session_id = None
            raise
        except Exception as e: # Catch any other unexpected error from decryption
            self.logger.error(f"Unexpected error during session_id assignment after decryption: {e}")
            self._session_id = None
            raise MTXPRBalanceAuthError(f'Unexpected error processing session token: {e}') from e

    def decrypt_session_id(self, password, encrypted_session_id_b64, salt_b64):
        decoded_session_id = base64.b64decode(encrypted_session_id_b64)
        decoded_salt = base64.b64decode(salt_b64)
        encoded_password = password.encode() 
        key = hashlib.pbkdf2_hmac('sha1', encoded_password, decoded_salt, 1000, dklen=32)

        data_source = pprp.data_source_gen(decoded_session_id)
        decryption_gen = pprp.rijndael_decrypt_gen(key, data_source)
        session_id_bytes_from_pprp = pprp.decrypt_sink(decryption_gen)

        return session_id_bytes_from_pprp.decode() 

    def close_session(self) -> None:
        """Closes the current session."""
        if self._session_id:
            try:
                self._request(self.SESSION_SERVICE, 'CloseSession', args=[self._session_id], include_session_id=False) # CloseSession takes SessionId directly 
                self.logger.info("Session closed successfully.")
            except MTXPRBalanceRequestError as e:
                self.logger.warning(f"Error closing session on device: {e}. Session might already be invalid.")
            finally:
                self._session_id = None
        else:
            self.logger.info("No active session to close.")

    def tare(self, immediately: bool = True) -> None:
        """
        Tares the balance.
        :param immediately: If True, tares immediately. If False, waits for stability.
        """
        try:
            response = self._request(self.WEIGHING_SERVICE, 'Tare', [str(immediately).lower()])
            if hasattr(response, 'ErrorState') and response.ErrorState and response.ErrorState != 'Ok' and response.ErrorState != 'Undefined': # 'Ok' is not a TareZeroError enum in WSDL, 'Undefined' might mean no error
                # WSDL TareZeroError enum includes: Overload, Underload, Undefined, StaticDetectionFailed, NotPossibleDueToCurrentWeighingWorkflowState 
                raise MTXPRBalanceDeviceError(
                    "Tare operation resulted in an error state.",
                    outcome=response.Outcome,
                    error_state=str(response.ErrorState)
                )
            self.logger.info(f"Tare command successful. Immediately: {immediately}")
        except MTXPRBalanceRequestError as e:
            self.logger.error(f"Tare failed: {e}")
            raise MTXPRBalanceDeviceError(f"Tare operation failed: {e.error_message or str(e)}", outcome=e.outcome, error_state=e.error_state) from e


    def zero(self, immediately: bool = True) -> None:
        """
        Zeroes the balance.
        :param immediately: If True, zeroes immediately. If False, waits for stability.
        """
        try:
            # WSDL shows ZeroRequest takes ZeroImmediately (boolean) 
            response = self._request(self.WEIGHING_SERVICE, 'Zero', [str(immediately).lower()])
            if hasattr(response, 'ErrorState') and response.ErrorState and response.ErrorState != 'Ok' and response.ErrorState != 'Undefined':
                raise MTXPRBalanceDeviceError(
                    "Zero operation resulted in an error state.",
                    outcome=response.Outcome,
                    error_state=str(response.ErrorState)
                )
            self.logger.info(f"Zero command successful. Immediately: {immediately}")
        except MTXPRBalanceRequestError as e:
            self.logger.error(f"Zero failed: {e}")
            raise MTXPRBalanceDeviceError(f"Zero operation failed: {e.error_message or str(e)}", outcome=e.outcome, error_state=e.error_state) from e


    def get_weight(self,
                   capture_mode: WeighingCaptureMode = WeighingCaptureMode.STABLE,
                   timeout_seconds: int = DEFAULT_SYNC_TIMEOUT) -> Tuple[float, str, bool]:
        """
        Retrieves a single weight value from the balance.
        :param capture_mode: How the weight should be captured (e.g., Stable, Immediate).
        :param timeout_seconds: Timeout for the synchronous GetWeight operation.
        :return: Tuple of (net_weight_value, unit, is_stable).
        :raises MTXPRBalanceDeviceError: If the weighing operation fails or returns an error status.
        """
        # GetWeightRequest from WSDL 
        # Parameters: WeighingCaptureMode, WeightDetectionMode, WeightChangeThreshold, WeightChangeThresholdUnit,
        # TimeIntervalCaptureDuration, TimeIntervalCaptureDelay, TimeoutInSeconds.
        # For a simple get_weight, many can be default/nillable.
        args = [
            capture_mode.value, # WeighingCaptureMode
            None,  # WeightDetectionMode (nillable) 
            None,  # WeightChangeThreshold (nillable) 
            None,  # WeightChangeThresholdUnit (nillable) 
            None,  # TimeIntervalCaptureDuration (nillable)
            None,  # TimeIntervalCaptureDelay (nillable)
            timeout_seconds # TimeoutInSeconds (nillable) 
        ]
        try:
            response = self._request(self.WEIGHING_SERVICE, 'GetWeight', args)
            weight_sample = response.WeightSample 
            if not weight_sample:
                raise MTXPRBalanceDeviceError("GetWeight returned no WeightSample.", outcome=response.Outcome)

            if weight_sample.Status != 'Ok': 
                raise MTXPRBalanceDeviceError(
                    f"Weight sample status is not Ok: {weight_sample.Status}",
                    outcome=response.Outcome,
                    error_state=weight_sample.Status
                )
            
            net_weight = weight_sample.NetWeight 
            if not net_weight or not hasattr(net_weight, 'Value') or not hasattr(net_weight, 'Unit'):
                 raise MTXPRBalanceDeviceError("NetWeight data is incomplete in WeightSample.", outcome=response.Outcome)

            value = float(net_weight.Value)
            unit = str(net_weight.Unit)
            is_stable = bool(weight_sample.Stable) 

            self.logger.info(f"Weight received: {value} {unit}, Stable: {is_stable}, CaptureMode: {capture_mode.value}")
            return value, unit, is_stable
        except MTXPRBalanceRequestError as e:
            self.logger.error(f"GetWeight failed: {e}")
            raise MTXPRBalanceDeviceError(f"GetWeight operation failed: {e.error_message or str(e)}", outcome=e.outcome, error_state=e.error_state) from e
        except (ValueError, TypeError, AttributeError) as e:
            self.logger.error(f"Error parsing weight sample: {e}")
            raise MTXPRBalanceDeviceError(f"Could not parse weight data: {e}") from e

    def _create_draft_shield_position_array(self, door_positions: List[Dict[str, Any]]) -> SudsObject:
        """Helper to create ArrayOfDraftShieldPosition suds object."""
        if not self.client:
            raise MTXPRBalanceConnectionError("Client not connected.")
        
        positions_array = self.client.factory.create('ns0:ArrayOfDraftShieldPosition') # ns0 is typical for tns
        positions_array.DraftShieldPosition = []

        for dp in door_positions:
            shield_pos = self.client.factory.create('ns0:DraftShieldPosition')
            shield_pos.DraftShieldId = dp['DraftShieldId'] # e.g., MTXPRBalanceDoors.LEFT_OUTER.value
            shield_pos.OpeningWidth = dp['OpeningWidth']   # 0 to 100 
            shield_pos.OpeningSide = dp.get('OpeningSide', None)
            positions_array.DraftShieldPosition.append(shield_pos)
        return positions_array

    def set_door_position(self, door: MTXPRBalanceDoors, position: int) -> None:
        """
        Sets the position of a specified door.
        :param door: The door to control (e.g., MTXPRBalanceDoors.LEFT_OUTER).
        :param position: The desired position (0 for closed, 100 for fully open). 
        """
        if not (0 <= position <= 100):
            raise ValueError("Position must be between 0 and 100.")

        shield_position_data = {
            'DraftShieldId': door.value,
            'OpeningWidth': position,
            'OpeningSide': None # Usually not needed for simple open/close for outer doors 
        }
        # According to WSDL, SetPositionRequest takes ArrayOfDraftShieldPosition 
        try:
            positions_array = self._create_draft_shield_position_array([shield_position_data])
            self._request(self.DRAFT_SHIELDS_SERVICE, 'SetPosition', [positions_array])
            self.logger.info(f"Door {door.value} position set to {position}.")
        except MTXPRBalanceRequestError as e:
            self.logger.error(f"Failed to set door {door.value} position: {e}")
            raise MTXPRBalanceDoorError(f"SetPosition failed for door {door.value}: {e.error_message or str(e)}", outcome=e.outcome) from e


    def open_door(self, door: MTXPRBalanceDoors) -> None:
        """Opens the specified door."""
        self.set_door_position(door, 100)

    def close_door(self, door: MTXPRBalanceDoors) -> None:
        """Closes the specified door."""
        self.set_door_position(door, 0) 


    def get_door_position(self, door: MTXPRBalanceDoors) -> int:
        """
        Gets the current position of the specified door.
        :param door: The door to query.
        :return: The opening width (0-100).
        """
        # GetPositionRequest takes ArrayOfDraftShieldIdentifier 
        if not self.client:
            raise MTXPRBalanceConnectionError("Client not connected.")
        
        draft_shield_ids = self.client.factory.create('ns0:ArrayOfDraftShieldIdentifier')
        draft_shield_ids.DraftShieldIdentifier = [door.value]

        try:
            response = self._request(self.DRAFT_SHIELDS_SERVICE, 'GetPosition', [draft_shield_ids])
            if response.DraftShieldsInformation and response.DraftShieldsInformation.DraftShieldInformation: 
                door_info = response.DraftShieldsInformation.DraftShieldInformation[0]
                # Check PositionDeterminationOutcome as per WSDL
                if door_info.PositionDeterminationOutcome != 'Success':
                    self.logger.warning(f"Door {door.value} position determination status: {door_info.PositionDeterminationOutcome}. Position may be inaccurate.")
                position = int(door_info.OpeningWidth)
                self.logger.info(f"Door {door.value} current position: {position}")
                return position
            else:
                raise MTXPRBalanceDoorError(f"No information returned for door {door.value}.", outcome=response.Outcome)
        except MTXPRBalanceRequestError as e:
            self.logger.error(f"Failed to get door {door.value} position: {e}")
            raise MTXPRBalanceDoorError(f"GetPosition failed for door {door.value}: {e.error_message or str(e)}", outcome=e.outcome) from e


    def is_door_open(self, door: MTXPRBalanceDoors) -> bool:
        """Checks if the specified door is open (position > 0)."""
        return self.get_door_position(door) > 0

    # --- Dosing Head Functions ---
    def read_dosing_head(self) -> Dict[str, Any]:
        """
        Reads information from the currently attached dosing head.
        :return: Dictionary with dosing head information. [cite: 2]
        :raises MTXPRDosingHeadError: If reading fails or no head is attached properly.
        """
        try:
            response = self._request(self.DOSING_AUTOMATION_SERVICE, 'ReadDosingHead') 

            head_info: Dict[str, Any] = {
                'head_id': str(response.HeadId) if hasattr(response, 'HeadId') and response.HeadId is not None else None, 
                'head_type': str(response.HeadType) if hasattr(response, 'HeadType') and response.HeadType is not None else None, 
                'head_type_name': str(response.HeadTypeName) if hasattr(response, 'HeadTypeName') and response.HeadTypeName is not None else None, 
                'dosing_head_info_details': {}
            }

            if hasattr(response, 'DosingHeadInfo') and response.DosingHeadInfo:
                dhi = response.DosingHeadInfo
                details = {
                    'substance_name': str(dhi.SubstanceName) if hasattr(dhi, 'SubstanceName') and dhi.SubstanceName is not None else None, 
                    'lot_id': str(dhi.LotId) if hasattr(dhi, 'LotId') and dhi.LotId is not None else None,
                    'number_of_dosages': int(dhi.NumberOfDosages) if hasattr(dhi, 'NumberOfDosages') and dhi.NumberOfDosages is not None else None,
                    'remaining_dosages': int(dhi.RemainingDosages) if hasattr(dhi, 'RemainingDosages') and dhi.RemainingDosages is not None else None,
                    'tapping_while_dosing': bool(dhi.TappingWhileDosing) if hasattr(dhi, 'TappingWhileDosing') and dhi.TappingWhileDosing is not None else None, 
                    'tapping_before_dosing': bool(dhi.TappingBeforeDosing) if hasattr(dhi, 'TappingBeforeDosing') and dhi.TappingBeforeDosing is not None else None,
                }
                if hasattr(dhi, 'RemainingQuantity') and dhi.RemainingQuantity:
                    details['remaining_quantity_value'] = float(dhi.RemainingQuantity.Value) if dhi.RemainingQuantity.Value is not None else None
                    details['remaining_quantity_unit'] = str(dhi.RemainingQuantity.Unit) if dhi.RemainingQuantity.Unit is not None else None
                head_info['dosing_head_info_details'] = details
            
            # Check if essential info like HeadType is present, as WSDL says it's minOccurs=1 for HeadType in response
            if not head_info['head_type'] and not head_info['head_id']:
                 # This case can happen if no head is attached or readable, Outcome might still be Success but ErrorMessage would detail it.
                 # The original code raised MTXPRDosingHeadError if Outcome was 'Error'.
                 # If Outcome is Success but no head info, it's still an issue.
                 self.logger.warning("ReadDosingHead successful but no head information returned. Assuming no head or unreadable.")

            self.logger.info(f"Dosing head information read: {head_info}")
            return head_info

        except MTXPRBalanceRequestError as e:
            # This is if _request itself raises an error (e.g. Outcome != Success)
            self.logger.error(f"Failed to read dosing head: {e}")
            raise MTXPRDosingHeadError(f"ReadDosingHead failed: {e.error_message or str(e)}", outcome=e.outcome, error_message=e.error_message) from e
        except (AttributeError, ValueError, TypeError) as e:
            self.logger.error(f"Error parsing dosing head response: {e}")
            raise MTXPRDosingHeadError(f"Could not parse dosing head data: {e}") from e

    def is_dosing_head_installed(self) -> bool:
        """Checks if a dosing head is installed and readable."""
        try:
            head_info = self.read_dosing_head()
            # A head is considered installed if it has a type and ID.
            # The ReadDosingHead service might return Success even if no head is present,
            # but HeadId/HeadType would be missing or null.
            return bool(head_info.get('head_id') and head_info.get('head_type'))
        except MTXPRDosingHeadError: # Catches errors from read_dosing_head
            return False 

    def write_dosing_head(self, head_type: DosingHeadType, head_id: str, info_to_write: Dict[str, Any]) -> None:
        """
        Writes information to the dosing head.
        :param head_type: Type of the dosing head (Powder or Liquid). 
        :param head_id: ID of the dosing head. 
        :param info_to_write: Dictionary containing EditableDosingHeadInfo fields to write. 
                              Example: {'SubstanceName': 'MySubstance', 'LotId': 'L123', ...}
        """
        if not self.client:
            raise MTXPRBalanceConnectionError("Client not connected.")

        try:
            editable_info = self.client.factory.create('ns0:EditableDosingHeadInfo')
            for key, value in info_to_write.items():
                if hasattr(editable_info, key):
                    if isinstance(getattr(editable_info, key, None), SudsObject) and isinstance(value, dict):
                        # Handle nested ValueWithUnit objects e.g. MolarMass, Purity
                        nested_obj = getattr(editable_info, key)
                        if 'Value' in value and hasattr(nested_obj, 'Value'):
                            nested_obj.Value = value['Value']
                        if 'Unit' in value and hasattr(nested_obj, 'Unit'):
                            nested_obj.Unit = value['Unit'] # Expects Unit enum string value
                    else:
                        setattr(editable_info, key, value)
                else:
                    self.logger.warning(f"Field '{key}' not found in EditableDosingHeadInfo model. Skipping.")
            
            args = [
                head_type.value, # DosingHeadType 
                head_id,         # HeadId (string)
                editable_info    # DosingHeadInfo (EditableDosingHeadInfo)
            ]
            self._request(self.DOSING_AUTOMATION_SERVICE, 'WriteDosingHead', args)
            self.logger.info(f"Successfully wrote data to dosing head ID: {head_id}")
        except MTXPRBalanceRequestError as e:
            self.logger.error(f"Failed to write to dosing head {head_id}: {e}")
            raise MTXPRDosingHeadError(f"WriteDosingHead failed: {e.error_message or str(e)}", outcome=e.outcome) from e
        except Exception as e:
            self.logger.error(f"Unexpected error writing to dosing head {head_id}: {e}")
            raise MTXPRDosingHeadError(f"Unexpected error in WriteDosingHead: {str(e)}") from e

    # --- Automated Dosing ---
    def _find_auto_dose_method(self, method_name: Optional[str] = None) -> SudsObject:
        """Finds an automated dosing method by name, or the first one available."""
        methods_response = self._request(self.WEIGHING_TASK_SERVICE, 'GetListOfMethods') 
        if not methods_response.Methods or not methods_response.Methods.MethodDescription:
            raise MTXPRBalanceDeviceError("No weighing methods found on the device.")

        available_methods = methods_response.Methods.MethodDescription
        
        if method_name:
            for method in available_methods:
                if method.Name == method_name and method.MethodType == 'AutomatedDosing':
                    self.logger.info(f"Found specified automated dosing method: {method.Name}")
                    return method
            raise MTXPRBalanceDeviceError(f"Automated dosing method '{method_name}' not found.")
        else: # Find first available automated dosing method
            for method in available_methods:
                if method.MethodType == 'AutomatedDosing':
                    self.logger.info(f"Found first available automated dosing method: {method.Name}")
                    return method
            raise MTXPRBalanceDeviceError("No automated dosing methods found on the device.")

    def _create_dosing_job_list(self, jobs_data: List[Dict[str, Any]]) -> SudsObject:
        """Helper to create ArrayOfDosingJob suds object."""
        if not self.client:
            raise MTXPRBalanceConnectionError("Client not connected.")

        job_list_obj = self.client.factory.create('ns0:ArrayOfDosingJob') 
        job_list_obj.DosingJob = []

        for job_data in jobs_data:
            dosing_job = self.client.factory.create('ns0:DosingJob') 
            dosing_job.SubstanceName = job_data.get('SubstanceName') 
            dosing_job.VialName = job_data.get('VialName', 'DefaultVial') 

            if 'TargetWeight' in job_data:
                tw = self.client.factory.create('ns0:WeightWithUnit')
                tw.Value = job_data['TargetWeight']['Value']
                tw.Unit = job_data['TargetWeight']['Unit']  
                dosing_job.TargetWeight = tw
            
            if 'LowerTolerance' in job_data and job_data['LowerTolerance']:
                lt = self.client.factory.create('ns0:WeightWithUnit')
                lt.Value = job_data['LowerTolerance']['Value']
                lt.Unit = job_data['LowerTolerance']['Unit']
                dosing_job.LowerTolerance = lt

            if 'UpperTolerance' in job_data and job_data['UpperTolerance']:
                ut = self.client.factory.create('ns0:WeightWithUnit')
                ut.Value = job_data['UpperTolerance']['Value']
                ut.Unit = job_data['UpperTolerance']['Unit']
                dosing_job.UpperTolerance = ut
            
            job_list_obj.DosingJob.append(dosing_job)
        return job_list_obj


    def auto_dose(self,
                  substance_name: str,
                  target_weight_mg: float,
                  vial_name: str = "Vial",
                  lower_tolerance_percent: float = 5.0, 
                  upper_tolerance_percent: float = 5.0,
                  dosing_method_name: Optional[str] = None,
                  notification_timeout_seconds: int = 200) -> float: 
        """
        Starts a single automated dosing job and waits for its completion.
        Handles notifications related to the dosing process.
        :return: Actual amount dosed in milligrams.
        :raises MTXPRBalanceDosingError: If dosing fails or times out.
        """
        try:
            dosing_method = self._find_auto_dose_method (dosing_method_name)
            self._request(self.WEIGHING_TASK_SERVICE, 'StartTask', [dosing_method.Name]) 
            self.logger.info(f"Weighing task '{dosing_method.Name}' started for automated dosing.")
        except MTXPRBalanceDeviceError as e:
             raise MTXPRBalanceDosingError(f"Failed to start dosing task: {e}") from e

        actual_dose_amount_mg: Optional[float] = None
        command_id: Optional[int] = None

        lower_tol_val = round(target_weight_mg * (lower_tolerance_percent / 100.0), 6) 
        upper_tol_val = round(target_weight_mg * (upper_tolerance_percent / 100.0), 6)

        dosing_job_data = {
            'SubstanceName': substance_name,
            'VialName': vial_name,
            'TargetWeight': {'Value': round(target_weight_mg, 6), 'Unit': Unit.MILLIGRAM.value}, 
            'LowerTolerance': {'Value': lower_tol_val, 'Unit': Unit.MILLIGRAM.value}, 
            'UpperTolerance': {'Value': upper_tol_val, 'Unit': Unit.MILLIGRAM.value} 
        }
        job_list_suds = self._create_dosing_job_list([dosing_job_data])

        start_response = self._request(self.DOSING_AUTOMATION_SERVICE, 'StartExecuteDosingJobListAsync', [job_list_suds]) 
        command_id = start_response.CommandId
        self.logger.info(f"Automated dosing job list started. Command ID: {command_id}")
        
        # Check for immediate errors from StartExecuteDosingJobListAsyncResponse
        if hasattr(start_response, 'StartDosingJobListError') and start_response.StartDosingJobListError:
            raise MTXPRBalanceDosingError(f"Error starting dosing job list: {start_response.StartDosingJobListError}",
                                            error_state=str(start_response.StartDosingJobListError))
        if hasattr(start_response, 'JobErrors') and start_response.JobErrors and start_response.JobErrors.DosingJobError:
            job_errors = [str(je.Error) for je in start_response.JobErrors.DosingJobError]
            raise MTXPRBalanceDosingError(f"Errors in dosing job setup: {', '.join(job_errors)}")


        # Poll for notifications
        end_time = time.time() + notification_timeout_seconds

        while time.time() < end_time:
            try:
                notifications_response = self._request(
                    self.NOTIFICATION_SERVICE, 
                    'GetNotifications', 
                    [self.DEFAULT_NOTIFICATION_POLL_TIMEOUT_MS],
                    ignore_specific_outcomes=['Timeout'] # Tell _request to not error on Timeout for this call
                )
            except MTXPRBalanceRequestError as e:
                 # This would catch other errors from GetNotifications, not Timeout
                 self.logger.error(f"Non-timeout error during GetNotifications: {e}")
                 raise MTXPRBalanceNotificationError(f"GetNotifications failed with non-timeout error: {e}") from e


            if notifications_response.Outcome == 'Success' and hasattr(notifications_response, 'Notifications') and notifications_response.Notifications:
                for item in notifications_response.Notifications:

                    if not isinstance(item, tuple) or len(item) != 2:
                        self.logger.warning(f"Unexpected notification item format: {item}")
                        continue
                    
                    notification_type, notification = item

                    if not hasattr(notification, 'CommandId') or notification.CommandId != command_id:
                        # self.logger.debug(f"Ignoring notification for different command ID ({notification.CommandId if hasattr(notification, 'CommandId') else 'N/A'})")
                        continue # Notification for a different command

                    self.logger.info(f"Processing notification: Type='{notification_type}', CommandId='{notification.CommandId}'")

                    if notification.Outcome == 'Error': 
                        dosing_err = getattr(notification, 'DosingError', 'Unknown dosing error')
                        err_msg = getattr(notification, 'ErrorMessage', dosing_err)
                        self.logger.error(f"Dosing notification reported error: {err_msg} (Type: {dosing_err})")
                        raise MTXPRBalanceDosingError(f"Dosing error from notification: {err_msg}", error_state=str(dosing_err))

                    if notification_type == 'DosingAutomationActionAsyncNotification': 
                        action_type = notification.DosingJobActionType
                        action_item = notification.ActionItem 
                        self.logger.info(f"Dosing requires action: {action_type} for item '{action_item}'. Confirming...")
                        self._request(self.DOSING_AUTOMATION_SERVICE, 'ConfirmDosingJobAction', [action_type, action_item]) 
                        continue

                    elif notification_type == 'DosingAutomationJobFinishedAsyncNotification':
                        if notification.DosingResult and notification.DosingResult.WeightSample and notification.DosingResult.WeightSample.NetWeight:
                            actual_dose_amount_mg = float(notification.DosingResult.WeightSample.NetWeight.Value) 
                            unit = notification.DosingResult.WeightSample.NetWeight.Unit
                            self.logger.info(f"Dosing automation job finished. Actual weight: {actual_dose_amount_mg} {unit}")
                            return actual_dose_amount_mg
                            # This notification is per-job. Wait for the DosingAutomationFinished for the whole list.
                        else:
                            self.logger.warning("DosingAutomationJobFinishedAsyncNotification received without full DosingResult.WeightSample.NetWeight.")


                    elif notification_type == 'DosingAutomationFinishedAsyncNotification':
                        # This notification indicates the entire job list is done.
                        if notification.Outcome == 'Success':
                            self.logger.info(f"Dosing job list (Command ID: {command_id}) finished successfully.")
                            if actual_dose_amount_mg is None:
                                    # This can happen if the JobFinished notification wasn't fully parsed or if only one job.
                                    self.logger.warning("DosingAutomationFinished but actual_dose_amount_mg not set from JobFinished. This might be an issue if multiple jobs.")
                                    # Attempt to get final weight from task completion if necessary, or rely on earlier JobFinished.
                                    # For a single job, this means it's done.
                            try:
                                self._request(self.WEIGHING_TASK_SERVICE, 'CompleteCurrentTask')
                                self.logger.info("Weighing task completed after dosing.")
                            except MTXPRBalanceRequestError as e:
                                self.logger.warning(f"Could not complete weighing task after dosing: {e}")
                            if actual_dose_amount_mg is not None:
                                return actual_dose_amount_mg
                            else:
                                # This is a fallback, ideally JobFinished should provide the weight.
                                # If it's critical, one might re-weigh or parse CompleteCurrentTaskResponse if it has WeighingItems
                                self.logger.error("Dosing finished, but could not determine the exact amount dosed from notifications.")
                                raise MTXPRBalanceDosingError("Dosing finished, but final dosed amount unclear from notifications.")
                        else: # Error or Canceled
                            failure_reason = getattr(notification, 'FailureReason', 'Unknown reason') 
                            failure_desc = getattr(notification, 'FailureDescription', '')
                            raise MTXPRBalanceDosingError(f"Dosing job list failed. Reason: {failure_reason} - {failure_desc}", outcome=notification.Outcome)
                    
                    elif notification_type == 'BufferOverrunEvent': 
                            self.logger.warning(f"Notification buffer overrun for command {notification.CommandId}. Some notifications may have been lost.")
            elif notifications_response.Outcome == 'Timeout':
                self.logger.debug("GetNotifications timed out (no new notifications). Continuing poll.")
            else:
                self.logger.warning(f"GetNotifications returned outcome {notifications_response.Outcome} with no notifications.")
            

            time.sleep(self.DEFAULT_POLL_INTERVAL)

        # If loop finishes without returning, it's a timeout
        raise MTXPRBalanceDosingError(f"Timeout ({notification_timeout_seconds}s) waiting for dosing job (Command ID: {command_id}) to finish.")

    def smart_auto_dose(self, 
                        substance_name: str, 
                        target_dose_amount_mg: float, 
                        max_attempts: int = 3, 
                        min_dosed_threshold_percent: float = 90.0, 
                        lower_tolerance_percent: float = 2.0,
                        upper_tolerance_percent: float = 2.0,
                        dosing_method_name: Optional[str] = None) -> float:
        """
        More robust automated dosing method that handles retries and common errors.
        :return: Total actual mass dosed in milligrams.
        """
        if not (0 < min_dosed_threshold_percent <= 100):
            raise ValueError("min_dosed_threshold_percent must be between 0 and 100.")

        total_actual_dosed_mg = 0.0
        remaining_target_mg = target_dose_amount_mg

        for attempt in range(1, max_attempts + 1):
            self.logger.info(f"Smart Dosing Attempt {attempt}/{max_attempts} for {substance_name}.")
            self.logger.info(f"Overall Target: {target_dose_amount_mg:.3f} mg. Remaining Target for this attempt: {remaining_target_mg:.3f} mg.")

            if remaining_target_mg <= 0.001: # Consider very small amounts as effectively dosed
                self.logger.info("Remaining target is negligible. Considering dosing complete.")
                break
            
            try:
                self.close_door(MTXPRBalanceDoors.LEFT_OUTER) 
                self.close_door(MTXPRBalanceDoors.RIGHT_OUTER) 
                time.sleep(1) 
                self.tare()
                pre_dose_net_weight, _, _ = self.get_weight(capture_mode=WeighingCaptureMode.IMMEDIATE) # Get weight before dose 

                # The dose_amount_mg for start_automated_dosing_job should be the remaining amount
                dosed_this_attempt_mg = self.auto_dose(
                    substance_name=substance_name,
                    target_weight_mg=remaining_target_mg,
                    lower_tolerance_percent=lower_tolerance_percent,
                    upper_tolerance_percent=upper_tolerance_percent,
                    dosing_method_name=dosing_method_name
                )
                
                # Verify actual dispensed amount if start_automated_dosing_job returns it directly
                if dosed_this_attempt_mg is None: # Should not happen if start_automated_dosing_job is implemented correctly
                    self.logger.warning("start_automated_dosing_job returned None. Weighing to confirm.")
                    time.sleep(1) 
                    post_dose_net_weight, _, _ = self.get_weight(capture_mode=WeighingCaptureMode.STABLE)
                    dosed_this_attempt_mg = post_dose_net_weight - pre_dose_net_weight # Net change
                
                if dosed_this_attempt_mg < 0:
                    self.logger.warning(f"Negative dose detected ({dosed_this_attempt_mg:.3f} mg). This might indicate an issue. Assuming 0mg dosed for this attempt.")
                    dosed_this_attempt_mg = 0.0


            except MTXPRBalanceDosingError as e:
                self.logger.error(f"Dosing attempt {attempt} failed: {e}. Cancelling current operation.")
                self.cancel_active() # Cancel task if dosing errored out mid-way
                dosed_this_attempt_mg = 0.0 # Assume nothing was dosed if error
                if attempt == max_attempts: 
                    raise
                time.sleep(2)
                continue 
            except MTXPRBalanceError as e: # Catch other balance errors during setup (tare, weigh)
                self.logger.error(f"Balance error during dosing attempt {attempt} setup: {e}")
                self.cancel_active()
                if attempt == max_attempts:
                    raise MTXPRBalanceDosingError(f"Failed smart dosing due to balance error on last attempt: {e}") from e
                time.sleep(2)
                continue

            total_actual_dosed_mg += dosed_this_attempt_mg
            remaining_target_mg = target_dose_amount_mg - total_actual_dosed_mg
            
            self.logger.info(f"Attempt {attempt}: Dosed {dosed_this_attempt_mg:.4f} mg. Total dosed: {total_actual_dosed_mg:.4f} mg. New remaining: {remaining_target_mg:.4f} mg.")

            if total_actual_dosed_mg >= (target_dose_amount_mg * (min_dosed_threshold_percent / 100.0)):
                self.logger.info(f"Target threshold reached ({min_dosed_threshold_percent}%). Smart dosing successful.")
                break
            if remaining_target_mg < 0.001: # If overshot slightly but within tolerance, or very close
                 self.logger.info("Target effectively reached or slightly overshot. Smart dosing considered complete.")
                 break
        else: # Loop finished without breaking (max_attempts reached and threshold not met)
            self.logger.error(f"Smart dosing failed after {max_attempts} attempts. Total dosed: {total_actual_dosed_mg:.3f} mg (Target: {target_dose_amount_mg:.3f} mg).")
            raise MTXPRBalanceDosingError(f"Smart dosing failed after {max_attempts} attempts. Target not met.")

        return round(total_actual_dosed_mg, 4) # Return with reasonable precision

    def cancel_active(self) -> None:
        """Attempts to cancel the currently active weighing task. Safe to call even if no task is active."""
        try:
            # Check if a task is implicitly active, e.g. after StartTask or if a command ID is pending
            self.logger.info("Attempting to cancel current weighing task.")
            self._request(self.WEIGHING_TASK_SERVICE, 'CancelCurrentTask') 
            self.logger.info("CancelCurrentTask command sent.")
        except MTXPRBalanceRequestError as e:
            # It's common for this to fail if no task is active, or if session is bad.
            if "no active task" in str(e.error_message).lower(): 
                self.logger.info("No active task to cancel, or task already completed/cancelled.")
            else:
                self.logger.warning(f"Could not cancel current task (may not be critical): {e}")
        except Exception as e:
            self.logger.warning(f"Unexpected error trying to cancel current task: {e}")


    def cancel_all(self) -> None:
        """Cancels all pending asynchronous commands known to the client or on the device."""
        # WSDL CancelRequest parameters: SessionId, CancelType, CommandId (nillable int for Asynchronous) 
        # CancelType can be All, CurrentSynchronous, Asynchronous 
        try:
            self.logger.info("Attempting to cancel all pending commands on the device (CancelType: All).")
            self._request(self.SESSION_SERVICE, 'Cancel', ['All', None]) 
            self.logger.info("All pending commands cancelled on the device.")
            self._active_command_ids.clear()
        except MTXPRBalanceRequestError as e:
            self.logger.error(f"Failed to cancel all commands: {e}")
            # Don't re-raise, as this is a cleanup effort.
        except Exception as e:
            self.logger.error(f"Unexpected error cancelling all commands: {e}")

    def __enter__(self):
        if not self.client or not self._session_id:
            self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.info("Exiting context manager. Cleaning up...")
        if self._active_command_ids:
            self.logger.warning(f"There are active command IDs: {self._active_command_ids}. Attempting to cancel.")

            self.cancel_all()
        self.close_session()


if __name__ == '__main__':
    from .config import get_balance_ip, get_balance_password
    
    BALANCE_IP = get_balance_ip()
    BALANCE_PASSWORD = get_balance_password()

    # More detailed logging for debugging
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("Starting MTXPRBalance example usage...")

    try:
        with MTXPRBalance(host=BALANCE_IP, password=BALANCE_PASSWORD) as balance:
            logger.info("Balance connected.")

            # --- Basic Weighing Operations ---
            try:
                logger.info("Performing Tare...")
                balance.tare()
                logger.info("Tare complete.")
                time.sleep(2) # Allow balance to settle

                logger.info("Getting stable weight...")
                weight_val, unit, stable = balance.get_weight(capture_mode=WeighingCaptureMode.STABLE)
                logger.info(f"Stable weight: {weight_val} {unit}, Stable: {stable}")
                time.sleep(1)

                logger.info("Getting immediate weight...")
                weight_val_imm, unit_imm, stable_imm = balance.get_weight(capture_mode=WeighingCaptureMode.IMMEDIATE)
                logger.info(f"Immediate weight: {weight_val_imm} {unit_imm}, Stable: {stable_imm}")

            except MTXPRBalanceDeviceError as e:
                logger.error(f"Weighing operation error: {e}")

            # --- Door Operations ---
            try:
                logger.info("Opening left outer door...")
                balance.open_door(MTXPRBalanceDoors.LEFT_OUTER)
                time.sleep(3) # Give door time to open
                logger.info(f"Left outer door open: {balance.is_door_open(MTXPRBalanceDoors.LEFT_OUTER)}")

                logger.info("Closing left outer door...")
                balance.close_door(MTXPRBalanceDoors.LEFT_OUTER)
                time.sleep(3) # Give door time to close
                logger.info(f"Left outer door open: {balance.is_door_open(MTXPRBalanceDoors.LEFT_OUTER)}")

            except MTXPRBalanceDoorError as e:
                logger.error(f"Door operation error: {e}")

            # --- Dosing Head Operations ---
            try:
                if balance.is_dosing_head_installed():
                    logger.info("Dosing head is installed.")
                    head_data = balance.read_dosing_head()
                    logger.info(f"Dosing Head Data: {head_data}")

                    # Example: Write to dosing head (use with caution and correct data)
                    # info_to_write = {
                    #     'SubstanceName': 'Test Substance',
                    #     'LotId': 'LOT001',
                    #     'TappingWhileDosing': True,
                    # }
                    # if head_data.get('head_id') and head_data.get('head_type'):
                    #     logger.info("Attempting to write to dosing head...")
                    #     balance.write_dosing_head(
                    #         head_type=DosingHeadType(head_data['head_type']),
                    #         head_id=head_data['head_id'],
                    #         info_to_write=info_to_write
                    #     )
                    #     logger.info("Write to dosing head complete. Verifying...")
                    #     updated_head_data = balance.read_dosing_head()
                    #     logger.info(f"Updated Dosing Head Data: {updated_head_data}")

                else:
                    logger.info("No dosing head installed or readable.")
            except MTXPRDosingHeadError as e:
                logger.error(f"Dosing head operation error: {e}")


            # --- Automated Dosing (Example - ensure a dosing head is attached and method exists) ---
            # USE WITH CAUTION - THIS WILL ATTEMPT TO DISPENSE MATERIAL
            # try:
            #     logger.info("Attempting smart automated dosing...")
            #     substance = "TestSolid"
            #     target_mg = 10.5
            #     # Ensure an "AutomatedDosing" method exists on your balance,
            #     # or specify its name if not using the default search.
            #     # e.g., dosing_method_name = "MyDosingMethod"
            #     actual_dosed = balance.smart_automated_dosing(
            #         substance_name=substance,
            #         target_dose_amount_mg=target_mg,
            #         max_attempts=2, # Keep attempts low for testing
            #         min_dosed_threshold_percent=80.0
            #     )
            #     logger.info(f"Smart automated dosing complete. Target: {target_mg} mg, Actual: {actual_dosed:.3f} mg")
            # except MTXPRBalanceDosingError as e:
            #     logger.error(f"Automated dosing failed: {e}")
            # except MTXPRBalanceDeviceError as e: # Catch if no dosing method found
            #      logger.error(f"Could not start dosing, device error: {e}")


    except MTXPRBalanceAuthError as e:
        logger.critical(f"Authentication failed: {e}")
    except MTXPRBalanceConnectionError as e:
        logger.critical(f"Connection failed: {e}")
    except MTXPRBalanceSessionError as e:
        logger.critical(f"Session management error: {e}")
    except FileNotFoundError as e:
        logger.critical(f"WSDL Template file not found. Ensure '{DEFAULT_WSDL_TEMPLATE_NAME}' is in the script's directory. Error: {e}")
    except Exception as e:
        logger.critical(f"An unexpected error occurred in the main application: {e}", exc_info=True)
    finally:
        logger.info("MTXPRBalance example usage finished.")

