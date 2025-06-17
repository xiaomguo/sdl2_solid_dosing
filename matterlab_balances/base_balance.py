from abc import ABC, abstractmethod


class Balance(ABC):
    """
    Abstract Base Class for handling different kinds of syringe pumps.
    """

    # def __init__(self):
    #     pass

    @abstractmethod
    def weigh(self, stable: bool = True) -> float:
        """
        abstract method to get weight of the balance
        :param stable:  if wait until the balance is stable
        :return:
        """
        pass

    @abstractmethod
    def tare(self, stable: bool = True):
        """
        abstract method to tare a balance
        :param stable: if wait until balance is stable
        :return:
        """
        pass
