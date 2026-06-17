from abc import ABC, abstractmethod
from collections import deque
from fastecdsa.curve import brainpoolP256r1 as Curve
from fastecdsa.point import Point
from fastecdsa.encoding.sec1 import SEC1Encoder as Encoder
import threading, time

__all__ = ['Channel', 'InMemoryChannel', 'StdIOChannel', 'PwnToolsChannel', 'point_to_bytes', 'bytes_to_point']


def point_to_bytes(point: Point) -> bytes:
    """ Converts a Point to its byte representation. """
    return Encoder.encode_public_key(point, compressed=True)


def bytes_to_point(data: bytes) -> Point:
    """ Converts bytes to a Point on W25519. """
    return Encoder.decode_public_key(data, Curve)


class Channel(ABC):
    """ Abstract communication channel for sending and receiving wire labels and points. """

    @abstractmethod
    def send_integer(self, integer: int):
        """ Sends an integer through the channel. """
        pass

    def send_integers(self, integers: list[int]):
        """ Sends a list of integers through the channel. """
        for integer in integers:
            self.send_integer(integer)

    @abstractmethod
    def send_bytes(self, data: bytes):
        """ Sends bytes through the channel. """
        pass

    @abstractmethod
    def send_point(self, point: Point):
        """ Sends a point through the channel. """
        pass
    
    @abstractmethod
    def read_integer(self) -> int:
        """ Reads an integer from the channel. """
        pass

    def read_integers(self, count: int) -> list[int]:
        """ Reads a list of integers from the channel. """
        return [self.read_integer() for _ in range(count)]

    @abstractmethod
    def read_bytes(self) -> bytes:
        """ Reads bytes from the channel. """
        pass

    @abstractmethod
    def read_point(self) -> Point:
        """ Reads a point from the channel. """
        pass


class InMemoryChannel(Channel):
    def __init__(self, threadsafe: bool = False, timeout: float = 0.0):
        """ Creates an in-memory channel, do not use directly, use pair() instead. """
        self.integer_buffer_write: deque[int] = None
        self.point_buffer_write: deque[Point] = None
        self.byte_buffer_write: deque[bytes] = None
        self.integer_buffer_read: deque[int] = None
        self.point_buffer_read: deque[Point] = None
        self.byte_buffer_read: deque[bytes] = None
        self.threadsafe = threadsafe
        self.timeout = timeout
        self.integer_lock_write: threading.Lock = None
        self.point_lock_write: threading.Lock = None
        self.byte_lock_write: threading.Lock = None
        self.integer_lock_read: threading.Lock = None
        self.point_lock_read: threading.Lock = None
        self.byte_lock_read: threading.Lock = None
    
    def send_integer(self, integer: int):
        if self.threadsafe:
            with self.integer_lock_write:
                self.integer_buffer_write.append(integer)
        else:
            self.integer_buffer_write.append(integer)

    def send_bytes(self, data: bytes):
        if self.threadsafe:
            with self.byte_lock_write:
                self.byte_buffer_write.append(data)
        else:
            self.byte_buffer.append(data)

    def send_point(self, point: Point):
        if self.threadsafe:
            with self.point_lock_write:
                self.point_buffer_write.append(point)
        else:
            self.point_buffer_write.append(point)

    def read_integer(self) -> int:
        tick = time.time()
        while not self.integer_buffer_read and time.time() - tick < self.timeout:
            time.sleep(0.01)
        if not self.integer_buffer_read:
            raise RuntimeError("No data to receive")
        if self.threadsafe:
            with self.integer_lock_read:
                return self.integer_buffer_read.popleft()
        else:
            return self.integer_buffer_read.popleft()

    def read_bytes(self) -> bytes:
        tick = time.time()
        while not self.byte_buffer_read and time.time() - tick < self.timeout:
            time.sleep(0.01)
        if not self.byte_buffer_read:
            raise RuntimeError("No data to receive")
        if self.threadsafe:
            with self.byte_lock_read:
                return self.byte_buffer_read.popleft()
        else:
            return self.byte_buffer_read.popleft()
    
    def read_point(self) -> Point:
        tick = time.time()
        while not self.point_buffer_read and time.time() - tick < self.timeout:
            time.sleep(0.01)
        if not self.point_buffer_read:
            raise RuntimeError("No data to receive")
        if self.threadsafe:
            with self.point_lock_read:
                return self.point_buffer_read.popleft()
        else:
            return self.point_buffer_read.popleft()

    @classmethod
    def pair(cls, timeout: float = 0.0) -> tuple['InMemoryChannel', 'InMemoryChannel']:
        """ Creates a pair of connected InMemoryChannels for two-way communication. """
        channel1 = cls(threadsafe=True, timeout=timeout)
        channel2 = cls(threadsafe=True, timeout=timeout)
        # 1 --> 2
        channel1.integer_buffer_write = channel2.integer_buffer_read = deque()
        channel1.point_buffer_write = channel2.point_buffer_read = deque()
        channel1.byte_buffer_write = channel2.byte_buffer_read = deque()
        channel1.integer_lock_write = channel2.integer_lock_read = threading.Lock()
        channel1.point_lock_write = channel2.point_lock_read = threading.Lock()
        channel1.byte_lock_write = channel2.byte_lock_read = threading.Lock()
        # 2 --> 1
        channel2.integer_buffer_write = channel1.integer_buffer_read = deque()
        channel2.point_buffer_write = channel1.point_buffer_read = deque()
        channel2.byte_buffer_write = channel1.byte_buffer_read = deque()
        channel2.integer_lock_write = channel1.integer_lock_read = threading.Lock()
        channel2.point_lock_write = channel1.point_lock_read = threading.Lock()
        channel2.byte_lock_write = channel1.byte_lock_read = threading.Lock()
        return channel1, channel2


class StdIOChannel(Channel):
    def send_integer(self, integer: int):
        print(f"{integer:x}")
    
    def send_bytes(self, data: bytes):
        print(data.hex())

    def send_point(self, point: Point):
        data = point_to_bytes(point)
        print(data.hex())
    
    def read_integer(self) -> int:
        line = input().strip()
        return int(line, 16)
    
    def read_bytes(self) -> bytes:
        line = input().strip()
        return bytes.fromhex(line)
    
    def read_point(self) -> Point:
        line = input().strip()
        data = bytes.fromhex(line)
        return bytes_to_point(data)


class PwnToolsChannel(Channel):
    def __init__(self, io, timeout: float = 5.0):
        from pwn import process
        self.io: process = io
        self.timeout = timeout

    def send_integer(self, integer: int):
        self.io.sendline(f"{integer:x}".encode())

    def send_bytes(self, data: bytes):
        self.io.sendline(data.hex().encode())

    def send_point(self, point: Point):
        data = point_to_bytes(point)
        self.io.sendline(data.hex().encode())

    def read_integer(self) -> int:
        line = self.io.recvline(timeout=self.timeout).strip()
        return int(line, 16)

    def read_bytes(self) -> bytes:
        line = self.io.recvline(timeout=self.timeout).strip()
        return bytes.fromhex(line.decode())

    def read_point(self) -> Point:
        line = self.io.recvline(timeout=self.timeout).strip()
        data = bytes.fromhex(line.decode())
        return bytes_to_point(data)
