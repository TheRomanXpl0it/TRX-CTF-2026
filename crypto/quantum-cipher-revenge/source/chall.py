#!/usr/bin/env python3

import warnings
warnings.filterwarnings("ignore")

from Crypto.Util.number import bytes_to_long, long_to_bytes
from os import urandom
import numpy as np

from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import PermutationGate, UnitaryGate
from qiskit_aer import AerSimulator

FLAG = b'TRX{8L0CH_5PH3R3_150M0RPH15M_4ND_GL084L_PH453}'
NQUBITS = 24
ROUNDS = 31
MAX_QUERIES = 1

KEY_INDEX = [3, 1, 6, 0, 5, 4, 7, 2]
PERMUTATION = np.array(range(NQUBITS))
np.random.shuffle(PERMUTATION)

class QCipher():
    def __init__(self, nqubits, rounds):
        self.nqubits = nqubits
        self.rounds = rounds

        self.theta = np.random.random()*np.pi
        self.phi = np.random.random()*2*np.pi

        self.n = [
            np.cos(self.phi)*np.sin(self.theta),
            np.sin(self.phi)*np.sin(self.theta),
            np.cos(self.theta)]
        
        self.alpha = [np.random.random()*2*np.pi for _ in range(self.rounds)]

        self.I = np.eye(2, dtype='complex')
        X = np.array([[0, 1],[1, 0]], dtype='complex')
        Y = np.array([[0, -1j],[1j, 0]], dtype='complex')
        Z = np.array([[1, 0],[0, -1]], dtype='complex')

        self.H = self.n[0]*X + self.n[1]*Y + self.n[2]*Z
        
        self.secret = bin(urandom(1)[0])[2:].rjust(8, '0')
        self.sampler = AerSimulator(method='statevector', precision='single')

    def state_from_string(self, state):
        
        state_string = state[::-1]
        state_qc = QuantumCircuit(self.nqubits, self.nqubits)

        for i, b in enumerate(state_string):
            if b=='1':
                state_qc.x(i)
            state_qc.ry(self.theta, i)
            state_qc.rz(self.phi, i)
        return state_qc
    
    def add_key(self, state, round):
        U = np.cos(self.alpha[round]) * self.I - 1j * np.sin(self.alpha[round]) * self.H
        round_gate = UnitaryGate(U)
        for i in range(self.nqubits):
            if self.secret[KEY_INDEX[i%len(KEY_INDEX)]] == '1':
                state.append(round_gate, [i])              


    def apply_permutation(self, state):
        perm_gate = PermutationGate(PERMUTATION)
        state.append(perm_gate, list(range(self.nqubits)))
    
    def apply_measurement(self, state):
        for i in range(self.nqubits):
            state.rz(-self.phi, i)
            state.ry(-self.theta, i)
        state.measure(range(self.nqubits), range(self.nqubits))

    def encrypt(self, pt):
        
        ct = ''
        
        bits = bin(bytes_to_long(pt))[2:]
        bits = bits.rjust((len(bits)//self.nqubits + 1)*self.nqubits, '0')
        blocks = [bits[i:i+self.nqubits] for i in range(0, len(bits), self.nqubits)]
        
        for block in blocks:
            state_qc = self.state_from_string(block)
            for round in range(self.rounds):
                self.add_key(state_qc, round)
                self.apply_permutation(state_qc)
                continue
            
            self.apply_measurement(state_qc)

            tqc = transpile(state_qc, self.sampler)
            job = self.sampler.run(tqc, shots=1)
            results = job.result()
            block_bitstring = next(iter(results.get_counts()))

            ct += block_bitstring
        
        ct = long_to_bytes(int(ct, 2))
        
        return ct

def main():
    
    print('Welcome to my Improved Quantum Encryption Algorithm! I dare you to break it\nThis time I only give you the encrypted flag')
    
    queries_left = MAX_QUERIES
    qcipher = QCipher(NQUBITS, ROUNDS)

    ct = qcipher.encrypt(FLAG)
    print(f'Encrypted Flag = {ct.hex()}')
    print(f'Permutation = {PERMUTATION}')

if __name__ == '__main__':
    main()