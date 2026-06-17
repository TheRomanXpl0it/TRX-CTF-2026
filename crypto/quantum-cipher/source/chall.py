#!/usr/bin/env python3

from Crypto.Util.number import bytes_to_long, long_to_bytes
from os import urandom
import numpy as np

from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

FLAG = b'TRX{1NV4R14N7_5U85P4C35_4ND_UN174R17Y}' # Redacted
NQUBITS = 8
ROUNDS = 12
MAX_QUERIES = 1

KEY1_INDEX = [3, 1, 6, 0, 5, 4, 7, 2]
PERMUTATION = [5, 2, 7, 0, 3, 1, 4, 6]
RXZ_INTERACTION = [(0, 3), (4, 5), (7, 2), (1, 6)]


class QCipher():
    def __init__(self, nqubits, rounds):
        self.nqubits = nqubits
        self.rounds = rounds

        self.secret = urandom(self.rounds+1)
        self.index_ct = self.secret[-1]*2**self.nqubits

    def state_from_string(self, state):
        
        state_string = state[::-1] + bin(self.secret[0])[2:].rjust(8, '0')[::-1]
        state_qc = QuantumCircuit(len(state_string))

        for i, b in enumerate(state_string):
            if b=='1':
                state_qc.x(i)
        return state_qc
    
    def evolve_key(self, state, round):
        bit_prev = bin(self.secret[round])[2:].rjust(8, '0')
        bit_new = bin(self.secret[round+1])[2:].rjust(8, '0')
        for i in range(8):
            if bit_prev[-i-1] != bit_new[-i-1]:
                state.x(self.nqubits+i)
    
    def add_key(self, state):
        for i in range(self.nqubits):
            state.cry(np.pi/15, self.nqubits+KEY1_INDEX[i], i)

    def apply_permutation(self, state):
        for i in range(self.nqubits):
            state.iswap(PERMUTATION[i], PERMUTATION[(i+1)%self.nqubits])
    
    def apply_rxz_interaction(self, state):
        for i in range(len(RXZ_INTERACTION)):
            state.rzx(np.pi/np.e, RXZ_INTERACTION[i][0], RXZ_INTERACTION[i][1])

    def encrypt(self, pt):
        
        ct = []
        
        bits = bin(bytes_to_long(pt))[2:]
        bits = bits.rjust((len(bits)//self.nqubits + 1)*self.nqubits, '0')
        blocks = [bits[i:i+self.nqubits] for i in range(0, len(bits), self.nqubits)]
        
        for block in blocks:
            state_qc = self.state_from_string(block)
            for round in range(self.rounds):
                self.add_key(state_qc)
                self.apply_permutation(state_qc)
                self.apply_rxz_interaction(state_qc)
                self.evolve_key(state_qc, round)

            ct_c = Statevector.from_instruction(state_qc).data

            ct.extend(list(ct_c[self.index_ct:self.index_ct+256]))
        
        return ct

def print_menu():
    print('What do you wanna do?')
    print('1. Encrypt byte')
    print('2. Get Encrypted Flag')

def main():
    
    print('Welcome to my Quantum Encryption Algorithm! I dare you to break it\n You can encrypt an arbitrary byte or ask for the flag')
    
    queries_left = MAX_QUERIES
    qcipher = QCipher(NQUBITS, ROUNDS)

    while True:
        print_menu()
        option = input('> ')
        if option == '1':
            if queries_left<1:
                print("Sorry no queries left :'(")
                exit()
            message = input('What do you wanna encrypt? (one hex byte) ')
            try:
                pt = long_to_bytes(int(message, 16) & 0xff)
                ct = qcipher.encrypt(pt)
                print(ct)
                print(len(ct))
                queries_left-=1
            except Exception as e:
                print(e)
                print('Invalid input! Need one byte as int')
                continue
        
        if option == '2':
            ct = qcipher.encrypt(FLAG)
            print(ct)

if __name__ == '__main__':
    main()