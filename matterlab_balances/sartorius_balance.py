import time
from typing import Tuple, Optional

from matterlab_serial_device import SerialDevice, open_close
from matterlab_balances.base_balance import Balance


class SartoriusBalance(Balance, SerialDevice):
    def __init__(self,
                 com_port: str,
                 units: str = "g",
                 baudrate: int = 9600,
                 bytesize: int = 7,
                 stopbits: int = 1,
                 parity: str = "odd",
                 timeout: Optional[float] = 1.0, **kwargs
    ) -> None:
        """
        Class for controlling Sartorius balances.

        Args:
            com_port: COM port of the pump connected to, example: "COM1", "/tty/USB0"
            baudrate: baudrate of the device
            bytesize: number of data bits
            parity: parity of the device
            timeout: time to wait for a response from the device
            **kwargs: additional keyword arguments for the serial.Serial class

        Returns:
            None
        """
        SerialDevice.__init__(self, com_port=com_port, baudrate=baudrate, bytesize=bytesize, parity=parity, stopbits=stopbits, timeout=timeout, **kwargs)
        Balance.__init__(self)

        self.units: str = units

    @open_close
    def _weigh(self, wait_time: float = 0.5) -> Tuple[bool, float]:
        """
        Get the weight reading of the balance.

        Args:
            wait_time: time to wait before reading the weight

        Returns:
            (True, weight) for stable reading
            (False, weight) for unstable reading
        """
        response: list = self.query(write_command="\x1bP\r\n", read_delay=wait_time).split()

        # if the last element in the split return value is "g",
        #   the reading is stable, and the weight is rtn[-2], and sign is rtn[-3]
        # else the reading is unstable, and the weight is rtn[-1], and sign is rtn[-2]
        if response[0] == "-":
            sign = "-"
        else:
            sign = "+"

        if response[-1] != self.units:
            weight = float(sign + response[-1])
            stable: bool = False
        else:
            weight = float(sign + response[-2])
            stable: bool = True

        self.logger.info(f"Stable: {stable}, Weight: {weight} {self.units}.")
        return stable, weight

    def _weigh_stable(self, max_tries: int = 10, wait_time: float = 5) -> float:
        """
        Gets a stable weight. If the weight hasn't stabilized (weigh method returns None instead of a float),
        waits for wait_time seconds. If the max_tries is reached, raises an error.

        Args:
            max_tries: maximum number of tries to get a stable weight
            wait_time: time to wait before trying again

        Returns:
            float: stable weight reading

        Raises:
            IOError: if the balance is not stable in weighing
        """
        # try to weigh max_tries times
        for i in range(0, max_tries):
            stable, weight = self._weigh()
            # if returned weight is (0, weight) or (False, weight), the weighing result is not yet stable
            #   wait for wait_time seconds, continue the loop
            # else return the weight
            if not stable:
                self.logger.info(f"Weight not stable, waiting for {wait_time} seconds.")
                time.sleep(wait_time)
            else:
                return weight
        # reach here if hit max_tries
        # raise error that balance is not stable in weighing
        raise IOError("Could not get a stable balance reading.")

    def weigh(self, stable: bool = False, **kwargs) -> float:
        """
        Gets the weight reading of the balance.

        Args:
            stable: if True, returns stable weight reading, else returns unstable weight reading
            **kwargs: keyword arguments for _weigh_stable

        Returns:
            float: weight reading
        """
        if stable:
            weight: float = self._weigh_stable(**kwargs)
            self.logger.info(f"Balance reading, stable: {weight} {self.units}.")
        else:
            weight: float = self._weigh()[1]
            self.logger.info(f"Balance reading: {weight} {self.units}.")

        return weight

    @open_close
    def _tare(self, delay: float = 1) -> None:
        """
        Tares the balance.

        Args:
            delay: time to wait after sending the tare command

        Returns:
            None
        """
        # send taring command
        self.write("\x1bT\r\n")
        time.sleep(delay)

    def _tare_stable(self, max_tries: int = 10, wait_time: float = 10, tolerance: float = 0.01) -> bool:
        """
        Tares the balance until stable. If the balance is not stable after max_tries, raises an error.

        Args:
            max_tries: maximum number of tries to tare the balance
            wait_time: time to wait before trying again
            tolerance: tolerance for taring the balance

        Returns:
            bool: True if tare is successful

        Raises:
            IOError: if the balance is not stable after max_tries
        """
        # tare the balance and wait for 5 seconds
        self._tare()
        time.sleep(5)
        for i in range(0, max_tries):
            # get weight after tare
            weight = self._weigh_stable()
            # if weight returned is less than tolerance range
            #   tare successful, return True
            # else wait for wait_time, retare
            if abs(weight) <= tolerance:
                return True
            else:
                time.sleep(wait_time)
                self._tare()
        # reach here if tare hit max_tries
        # raise error as balance is not stable in taring
        raise IOError("Could not get the balance to tare reliably.")

    def tare(self, stable: bool = False, **kwargs) -> None:
        """
        Tares the balance.

        Args:
            stable: if True, tares the balance until stable, else tares the balance once
            **kwargs: keyword arguments for _tare_stable

        Returns:
            None
        """
        if stable:
            self._tare_stable(**kwargs)
        else:
            self._tare()

        self.logger.info("Balance tared.")
