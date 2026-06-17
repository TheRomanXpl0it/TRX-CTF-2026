from channel import Channel, Curve, Point, point_to_bytes
import secrets, hashlib

__all__ = ['Sender', 'Receiver']


def hash_point(point: Point, tweak: bytes) -> int:
    """ Hashes a point with a tweak to produce a pseudorandom integer. """
    if not isinstance(point, Point):
        raise TypeError("point must be a Point instance")
    if not isinstance(tweak, bytes):
        raise TypeError("tweak must be bytes")
    data = point_to_bytes(point) + tweak
    digest = hashlib.shake_128(data).digest(32)
    return int.from_bytes(digest, 'big')


class Sender:
    def __init__(self, channel: Channel):
        """ Initializes the Sender with a communication channel. """
        if not isinstance(channel, Channel):
            raise TypeError("channel must be an instance of Channel")
        self.channel = channel
        self.x = secrets.randbelow(Curve.q - 1) + 1
        self.P = self.x * Curve.G
        self.counter = 0
        # Sender ---> Receiver: P = x * G
        channel.send_point(self.P)

    def send(self, options: list[tuple[int, int]]):
        """ Sends in OT the options for the Receiver to choose from. """
        if not isinstance(options, list):
            raise TypeError("options must be a list")
        if not all(isinstance(pair, tuple) and len(pair) == 2 for pair in options):
            raise TypeError("each option must be a tuple of two integers")
        Q = self.x * self.P
        for zero, one in options:
            # Receiver ---> Sender: R_i = r_i * G + b_i * P
            R = self.channel.read_point()
            S0 = self.x * R
            S1 = S0 - Q
            tweak = self.counter.to_bytes(16, 'little')
            k0 = hash_point(S0, tweak) ^ zero
            k1 = hash_point(S1, tweak) ^ one
            # Sender ---> Receiver: H(R_i * x), H((R_i - P) * x)
            self.channel.send_integer(k0)
            self.channel.send_integer(k1)
            self.counter += 1


class Receiver:
    def __init__(self, channel: Channel):
        """ Initializes the Receiver with a communication channel. """
        if not isinstance(channel, Channel):
            raise TypeError("channel must be an instance of Channel")
        self.channel = channel
        # Sender ---> Receiver: P = x * G
        self.P = channel.read_point()
        self.counter = 0

    def receive(self, choices: list[bool | int]) -> list[int]:
        """ Receives in OT the chosen options based on the choice bits. """
        if not isinstance(choices, list):
            raise TypeError("choices must be a list")
        if not all(isinstance(bit, (bool, int)) for bit in choices):
            raise TypeError("each choice must be a boolean or integer")
        ks = []
        for bit in choices:
            r = secrets.randbelow(Curve.q - 1) + 1
            R = r * Curve.G + self.P if bit else r * Curve.G
            # Receiver ---> Sender: R_i = r_i * G + b_i * P
            self.channel.send_point(R)
            k = hash_point(r * self.P, self.counter.to_bytes(16, 'little'))
            ks.append(k)
            self.counter += 1
        options = []
        for k, bit in zip(ks, choices):
            # Sender ---> Receiver: H(R_i * x), H((R_i - P) * x)
            c0 = self.channel.read_integer()
            c1 = self.channel.read_integer()
            option = c1 ^ k if bit else c0 ^ k
            options.append(option)
        return options


if __name__ == "__main__":
    from channel import InMemoryChannel
    import threading

    channel_sender, channel_receiver = InMemoryChannel.pair(timeout=5.0)
    sender = Sender(channel_sender)
    receiver = Receiver(channel_receiver)

    options = [(secrets.randbits(128), secrets.randbits(128)) for _ in range(512)]
    choices = [secrets.choice([False, True]) for _ in range(512)]

    sender_process = threading.Thread(target=sender.send, args=(options,))
    receiver_process = threading.Thread(target=receiver.receive, args=(choices,))
    sender_process.start()
    receiver_process.start()
    sender_process.join()
    receiver_process.join()
