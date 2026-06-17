from gf2 import GF2Vector, GF2Matrix
from channel import Channel
from ot import Sender as OTSender, Receiver as OTReceiver
import secrets, hashlib, dataclasses, itertools

OK = b"ok"
ABORT = b"abort"


@dataclasses.dataclass(frozen=True)
class OTEParam:
    """ Parameters for the OT extension protocol. """
    n: int
    m: int
    ell: int
    security_parameter: int = 128

    def __post_init__(self):
        if not isinstance(self.n, int) or self.n < 0:
            raise ValueError("n must be a non-negative integer")
        if not isinstance(self.m, int) or self.m < 0:
            raise ValueError("m must be a non-negative integer")
        if not isinstance(self.ell, int) or self.ell < 0:
            raise ValueError("ell must be a non-negative integer")
        if not isinstance(self.security_parameter, int) or self.security_parameter < 0:
            raise ValueError("security_parameter must be a non-negative integer")
        if self.security_parameter & (self.security_parameter - 1) != 0:
            raise ValueError("security_parameter must be a power of 2")

    @property
    def kappa(self):
        return self.security_parameter * 2
    
    @property
    def mu(self):
        return self.security_parameter
    
    @property
    def C(self):
        """ Walsh-Hadamard code with codewords of length kappa. """
        G = GF2Matrix.from_columns(
            GF2Vector.from_bytes(bytes([i]), self.kappa.bit_length() - 1) for i in range(self.kappa)
        )
        gs = G.rows()
        for bs in itertools.product(range(2), repeat=self.kappa.bit_length() - 1):
            yield sum((g for g, b in zip(gs, bs) if b), GF2Vector.zeros(self.kappa))
        
    def commit(self, coins: bytes) -> bytes:
        """ Commits to the given coins and returns the commitment and salt. """
        if not isinstance(coins, bytes):
            raise TypeError("coins must be bytes")
        salt = secrets.token_bytes(self.security_parameter // 8)
        return hashlib.shake_128(salt + coins).digest(self.kappa // 8), salt
    
    def verify(self, com: bytes, salt: bytes, coins: bytes) -> bool:
        """ Verifies a commitment against the given coins and salt. """
        if not isinstance(com, bytes):
            raise TypeError("com must be bytes")
        if not isinstance(salt, bytes):
            raise TypeError("salt must be bytes")
        if not isinstance(coins, bytes):
            raise TypeError("coins must be bytes")
        expected_com = hashlib.shake_128(salt + coins).digest(self.kappa // 8)
        return expected_com == com

    def mask(self, idx: int, seed: bytes) -> int:
        """ Computes a mask for the given index and seed. """
        if not isinstance(idx, int) or idx < 0:
            raise ValueError("idx must be a non-negative integer")
        if not isinstance(seed, bytes):
            raise TypeError("seed must be bytes")
        if idx >= self.m:
            raise ValueError("idx must be less than m")
        data = idx.to_bytes(4, 'little') + seed
        mask = hashlib.shake_128(data).digest((self.ell + 7) // 8)
        return int.from_bytes(mask, 'little') & ((1 << self.ell) - 1)


def seed_to_vector(seed: bytes, length: int) -> GF2Vector:
    """ Converts a seed to a GF(2) vector of the given length. """
    if not isinstance(seed, bytes):
        raise TypeError("seed must be bytes")
    if not isinstance(length, int) or length < 0:
        raise ValueError("length must be a non-negative integer")
    data = hashlib.shake_128(seed).digest((length + 7) // 8)
    return GF2Vector.from_bytes(data, length)


class OTEAbort(Exception):
    """ Exception raised when the protocol is aborted due to a check failure with the other party. """
    pass


def send(param: OTEParam, channel: Channel, xs: list[list[int]]) -> None:
    """ Sends in OT the options for the Receiver to choose from based on the input lists. """
    if not isinstance(channel, Channel):
        raise TypeError("channel must be an instance of Channel")
    if not isinstance(xs, list):
        raise TypeError("xs must be a list")
    if not all(isinstance(x, list) and all(isinstance(xj, int) for xj in x) for x in xs):
        raise TypeError("each xs must be a list of integers")
    if len(xs) != param.m:
        raise ValueError("length of xs must be m")
    if len(set(map(len, xs))) != 1:
        raise ValueError("all entries of xs must have the same length")
    if set(map(len, xs)) != {param.n}:
        raise ValueError("each entry of xs must have length n")
    C = list(param.C)

    s = [secrets.randbits(1) for _ in range(param.kappa)]
    ot_receiver = OTReceiver(channel)
    ks = ot_receiver.receive(s)

    D = GF2Matrix.from_bytes(channel.read_bytes(), param.m + param.mu, param.kappa)
    cols = []
    for j, k in enumerate(ks):
        col = D.column(j) * s[j] + \
            seed_to_vector(k.to_bytes((param.kappa + 7) // 8, 'little'), param.m + param.mu)
        cols.append(col)
    A = GF2Matrix.from_columns(cols)

    receiver_com = channel.read_bytes()
    sender_coins = secrets.token_bytes(param.kappa // 8)
    sender_com, sender_salt = param.commit(sender_coins)
    channel.send_bytes(sender_com)
    receiver_coins = channel.read_bytes()
    receiver_salt = channel.read_bytes()
    channel.send_bytes(sender_coins)
    channel.send_bytes(sender_salt)

    response = channel.read_bytes()
    if response == ABORT:
        raise OTEAbort("receiver aborted the protocol at commitment verification")
    elif response != OK:
        raise OTEAbort("invalid response from receiver at commitment verification")
    if not param.verify(receiver_com, receiver_salt, receiver_coins):
        channel.send_bytes(ABORT)
        raise OTEAbort("receiver commitment verification failed")
    channel.send_bytes(OK)

    seed = receiver_coins + sender_coins
    ws = []
    for i in range(param.mu):
        w = seed_to_vector(seed + i.to_bytes(4, 'little'), param.m + param.mu)
        ws.append(w)
    
    b = GF2Vector.from_bytes(channel.read_bytes(), param.mu)
    alphas = channel.read_integers(param.mu)
    s = GF2Vector.from_list(s)
    for l, w in enumerate(ws):
        alpha = alphas[l]
        if alpha < 0 or alpha >= len(C):
            raise ValueError("invalid alpha")
        a = (w * A).parity
        p = (s * C[alpha]).parity
        if a != b[l] ^ p:
            channel.send_bytes(ABORT)
            raise OTEAbort(f"invalid check at index {l}")
    channel.send_bytes(OK)

    for i, x in enumerate(xs):
        a = A.row(i)
        ys = [xj ^ param.mask(i, (a + s * C[j]).to_bytes()) for j, xj in enumerate(x)]
        channel.send_integers(ys)


def receive(param: OTEParam, channel: Channel, rs: list[bool | int]) -> list[int]:
    """ Receives in OT the chosen options based on the choice bits. """
    if not isinstance(channel, Channel):
        raise TypeError("channel must be an instance of Channel")
    if not isinstance(rs, list):
        raise TypeError("rs must be a list")
    if not all(isinstance(bit, (bool, int)) for bit in rs):
        raise TypeError("each rs must be a boolean or integer")
    if len(rs) != param.m:
        raise ValueError("length of rs must be m")
    C = list(param.C)

    ot_sender = OTSender(channel)
    k0 = [secrets.randbits(param.kappa) for _ in range(param.kappa)]
    k1 = [secrets.randbits(param.kappa) for _ in range(param.kappa)]
    ot_sender.send(list(zip(k0, k1)))

    B = GF2Matrix.from_columns(
        seed_to_vector(k0[i].to_bytes((param.kappa + 7) // 8, 'little'), param.m + param.mu) 
    for i in range(param.kappa))
    E = GF2Matrix.from_rows(
        [C[r] for r in rs] + [C[secrets.randbelow(param.kappa)] for _ in range(param.mu)]
    )
    D = B + E + GF2Matrix.from_columns(
        seed_to_vector(k1[i].to_bytes((param.kappa + 7) // 8, 'little'), param.m + param.mu) 
    for i in range(param.kappa))
    channel.send_bytes(D.to_bytes())

    receiver_coins = secrets.token_bytes(param.kappa // 8)
    receiver_com, receiver_salt = param.commit(receiver_coins)
    channel.send_bytes(receiver_com)
    sender_com = channel.read_bytes()
    channel.send_bytes(receiver_coins)
    channel.send_bytes(receiver_salt)
    sender_coins = channel.read_bytes()
    sender_salt = channel.read_bytes()
    
    if not param.verify(sender_com, sender_salt, sender_coins):
        channel.send_bytes(ABORT)
        raise OTEAbort("sender commitment verification failed")
    channel.send_bytes(OK)
    response = channel.read_bytes()
    if response == ABORT:
        raise OTEAbort("sender aborted the protocol at commitment verification")
    elif response != OK:
        raise OTEAbort("invalid response from sender at commitment verification")
    
    seed = receiver_coins + sender_coins
    ws = []
    for i in range(param.mu):
        w = seed_to_vector(seed + i.to_bytes(4, 'little'), param.m + param.mu)
        ws.append(w)
    
    b = GF2Vector.from_list([(w * B).parity for w in ws])
    alphas = []
    for w in ws:
        e = w * E
        assert e in C, "invalid codeword"
        alpha = C.index(e)
        alphas.append(alpha)
    channel.send_bytes(b.to_bytes())
    channel.send_integers(alphas)

    response = channel.read_bytes()
    if response == ABORT:
        raise OTEAbort("sender aborted the protocol at check phase")
    elif response != OK:
        raise OTEAbort("invalid response from sender at check phase")

    zs = []
    for i, r in enumerate(rs):
        b = B.row(i)
        y = channel.read_integers(param.n)[r]
        z = y ^ param.mask(i, b.to_bytes())
        zs.append(z)
    return zs


if __name__ == "__main__":
    from channel import InMemoryChannel
    import threading

    param = OTEParam(n=16, m=8, ell=256)
    channel_sender, channel_receiver = InMemoryChannel.pair(timeout=5.0)
    xs = [[secrets.randbits(param.ell) for _ in range(param.n)] for _ in range(param.m)]
    rs = [secrets.randbelow(param.n) for _ in range(param.m)]

    sender_process = threading.Thread(target=send, args=(param, channel_sender, xs))
    receiver_process = threading.Thread(target=receive, args=(param, channel_receiver, rs))
    sender_process.start()
    receiver_process.start()
    sender_process.join()
    receiver_process.join()
