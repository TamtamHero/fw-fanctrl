from abc import ABC, abstractmethod

from fw_fanctrl.exception.UnimplementedException import UnimplementedException


class HardwareController(ABC):
    @abstractmethod
    def get_temperature(self):
        raise UnimplementedException()

    @abstractmethod
    def set_speed(self, speed):
        raise UnimplementedException()

    @abstractmethod
    def pause(self):
        pass

    @abstractmethod
    def resume(self):
        pass

    @abstractmethod
    def is_on_ac(self):
        raise UnimplementedException()
