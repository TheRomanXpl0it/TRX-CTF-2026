import numpy as np


class GF2Vector:
    def __init__(self, data: np.ndarray, verify: bool = True):
        if verify:
            if not isinstance(data, np.ndarray):
                raise TypeError("data must be a numpy array")
            if data.dtype != np.uint8:
                raise TypeError("data must be of type uint8")
            if data.ndim != 1:
                raise ValueError("data must be a 1D array")
            if np.any((data & 1) != data):
                raise ValueError("data must be binary (0 or 1)")
        self.data = data
    
    @property
    def parity(self):
        return np.bitwise_xor.reduce(self.data) & 1
    
    def __add__(self, other) -> 'GF2Vector':
        """ Addition between vectors """
        if isinstance(other, (int, np.integer)) and other & 1 == 0:
            return GF2Vector(self.data.copy(), verify=False)
        if not isinstance(other, GF2Vector):
            raise TypeError("other must be a GF2Vector")
        if self.data.shape != other.data.shape:
            raise ValueError("vectors must have the same shape")
        return GF2Vector(self.data ^ other.data, verify=False)
    
    __radd__ = __add__
    __sub__ = __add__
    __rsub__ = __add__
    
    def __mul__(self, other) -> 'GF2Vector':
        """ Scalar multiplication | Element-wise multiplication """
        if isinstance(other, (int, np.integer)):
            if other & 1 == 0:
                return GF2Vector(np.zeros_like(self.data), verify=False)
            else:
                return GF2Vector(self.data.copy(), verify=False)
        if not isinstance(other, GF2Vector):
            return NotImplemented
        if self.data.shape != other.data.shape:
            raise ValueError("vectors must have the same shape")
        return GF2Vector(self.data & other.data, verify=False)
    
    def __rmul__(self, other) -> 'GF2Vector':
        """ Scalar multiplication | Element-wise multiplication """
        return self.__mul__(other)
    
    def __str__(self):
        return "(" + ", ".join(map(str, self.data)) + ")"
    
    def __repr__(self):
        return self.__str__()

    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, index):
        if isinstance(index, (int, np.integer)):
            return self.data[index]
        elif isinstance(index, slice):
            return GF2Vector(self.data[index], verify=False)
        else:
            raise TypeError("index must be an int or slice")

    def __eq__(self, value):
        if not isinstance(value, GF2Vector):
            return False
        return np.array_equal(self.data, value.data)
    
    def __ne__(self, value):
        return not self.__eq__(value)

    def zeros(length: int) -> 'GF2Vector':
        if not isinstance(length, (int, np.integer)):
            raise TypeError("length must be an integer")
        if length < 0:
            raise ValueError("length must be non-negative")
        data = np.zeros(length, dtype=np.uint8)
        return GF2Vector(data, verify=False)

    def to_bytes(self) -> bytes:
        """ 
        Convert vector to bytes, with bits packed in little-endian order 
        (first element is least significant bit of first byte)
        """
        data = np.packbits(self.data, bitorder='little')
        return data.tobytes()

    @classmethod
    def from_bytes(cls, data: bytes, length: int = None):
        """
        Create a GF2Vector from bytes, with bits packed in little-endian order 
        (first element is least significant bit of first byte)
        """
        if not isinstance(data, bytes):
            raise TypeError("data must be bytes")
        if length is None:
            length = len(data) * 8
        if len(data) * 8 < length:
            raise ValueError("data is too short")
        data = np.frombuffer(data, dtype=np.uint8)
        data = np.unpackbits(data, count=length, bitorder='little')
        return cls(data, verify=False)
    
    @classmethod
    def from_list(cls, data: list[int]):
        """ Create a GF2Vector from a list of integers (0 or 1) """
        if not isinstance(data, list):
            raise TypeError("data must be a list")
        if not all(isinstance(x, (int, np.integer)) for x in data):
            raise TypeError("all elements of data must be integers")
        data = np.array(data, dtype=np.uint8)
        if np.any((data & 1) != data):
            raise ValueError("all elements of data must be binary (0 or 1)")
        return cls(data, verify=False)
    
    

class GF2Matrix:
    def __init__(self, data: np.ndarray, verify: bool = True):
        if verify:
            if not isinstance(data, np.ndarray):
                raise TypeError("data must be a numpy array")
            if data.dtype != np.uint8:
                raise TypeError("data must be of type uint8")
            if data.ndim != 2:
                raise ValueError("data must be a 2D array")
            if np.any((data & 1) != data):
                raise ValueError("data must be binary (0 or 1)")
        self.data = data

    def __add__(self, other) -> 'GF2Matrix':
        """ Addition between matrices """
        if not isinstance(other, GF2Matrix):
            raise TypeError("other must be a GF2Matrix")
        if self.data.shape != other.data.shape:
            raise ValueError("matrices must have the same shape")
        return GF2Matrix(self.data ^ other.data, verify=False)
    
    def __mul__(self, other) -> 'GF2Vector | GF2Matrix':
        """ Scalar multiplication | Matrix vector multiplication """
        if isinstance(other, (int, np.integer)):
            if other & 1 == 0:
                return GF2Matrix(np.zeros_like(self.data), verify=False)
            else:
                return GF2Matrix(self.data.copy(), verify=False)
        if isinstance(other, GF2Vector):
            if self.ncols != len(other):
                raise ValueError("matrix column count must match vector length")
            result_data = np.bitwise_xor.reduce(self.data & other.data, axis=0)
            return GF2Vector(result_data, verify=False)
        if isinstance(other, GF2Matrix):
            raise TypeError(f"matrix-matrix multiplication is not implemented")
        raise TypeError(f"invalid type {type(other)} for right multiplication")
    
    def __rmul__(self, other) -> 'GF2Vector | GF2Matrix':
        """ Scalar multiplication | Vector matrix multiplication """
        if isinstance(other, (int, np.integer)):
            if other & 1 == 0:
                return GF2Matrix(np.zeros_like(self.data), verify=False)
            else:
                return GF2Matrix(self.data.copy(), verify=False)
        if isinstance(other, GF2Vector):
            if self.nrows != len(other):
                raise ValueError("matrix row count must match vector length")
            result_data = np.bitwise_xor.reduce(self.data.T & other.data, axis=1)
            return GF2Vector(result_data, verify=False)
        if isinstance(other, GF2Matrix):
            raise TypeError(f"matrix-matrix multiplication is not implemented")
        raise TypeError(f"invalid type {type(other)} for left multiplication")

    @property
    def shape(self):
        return self.data.shape
    
    @property
    def nrows(self):
        return self.data.shape[0]
    
    @property
    def ncols(self):
        return self.data.shape[1]
    
    def __str__(self):
        return "\n".join("[" + " ".join(map(str, row)) + "]" for row in self.data)
    
    def __repr__(self):
        return self.__str__()

    def __getitem__(self, index) -> 'GF2Vector | GF2Matrix | int':
        integer = (int, np.integer)
        if isinstance(index, integer):
            return GF2Vector(self.data[index], verify=False)
        elif isinstance(index, slice):
            return GF2Matrix(self.data[index], verify=False)
        elif isinstance(index, tuple) and len(index) == 2:
            row_index, col_index = index
            if isinstance(row_index, integer) and isinstance(col_index, integer):
                return self.data[row_index, col_index]
            elif isinstance(row_index, integer):
                return GF2Vector(self.data[row_index, col_index].flatten(), verify=False)
            elif isinstance(col_index, integer):
                return GF2Vector(self.data[row_index, col_index].flatten(), verify=False)
            else:
                return GF2Matrix(self.data[row_index, col_index], verify=False)
        else:
            raise TypeError("index must be an int, slice, or tuple of two ints/slices")
    
    def __eq__(self, value):
        if not isinstance(value, GF2Matrix):
            return False
        return np.array_equal(self.data, value.data)
    
    def __ne__(self, value):
        return not self.__eq__(value)

    def zeros(nrows: int, ncols: int) -> 'GF2Matrix':
        if not isinstance(nrows, (int, np.integer)) or not isinstance(ncols, (int, np.integer)):
            raise TypeError("nrows and ncols must be integers")
        if nrows < 0 or ncols < 0:
            raise ValueError("nrows and ncols must be non-negative")
        data = np.zeros((nrows, ncols), dtype=np.uint8)
        return GF2Matrix(data, verify=False)

    def to_bytes(self) -> bytes:
        """ Convert matrix to bytes in column-major order, with each column packed into bits (little-endian) """
        data = np.packbits(self.data, axis=1, bitorder='little')
        return data.tobytes()
    
    @classmethod
    def from_bytes(cls, data: bytes, nrows: int, ncols: int):
        """ Create a GF2Matrix from bytes in column-major order, with each column packed into bits (little-endian) """
        if not isinstance(data, bytes):
            raise TypeError("data must be bytes")
        if len(data) * 8 < nrows * ncols:
            raise ValueError("data is too short")
        data = np.frombuffer(data, dtype=np.uint8).reshape((nrows, (ncols + 7) // 8))
        data = np.unpackbits(data, count=ncols, axis=1, bitorder='little')
        assert data.shape == (nrows, ncols)
        return cls(data, verify=False)

    @classmethod
    def from_rows(cls, rows):
        """ Create a GF2Matrix from an iterable of GF2Vector representing the rows of the matrix """
        if not hasattr(rows, "__iter__"):
            raise TypeError("rows must be an iterable of GF2Vector")
        data = []
        for row in rows:
            if not isinstance(row, GF2Vector):
                raise TypeError("each row must be a GF2Vector")
            data.append(row.data)
        data = np.vstack(data)
        return cls(data, verify=False)
    
    @classmethod
    def from_columns(cls, columns):
        """ Create a GF2Matrix from an iterable of GF2Vector representing the columns of the matrix """
        if not hasattr(columns, "__iter__"):
            raise TypeError("columns must be an iterable of GF2Vector")
        data = []
        for col in columns:
            if not isinstance(col, GF2Vector):
                raise TypeError("each column must be a GF2Vector")
            data.append(col.data)
        data = np.column_stack(data)
        return cls(data, verify=False)

    def row(self, index):
        if not isinstance(index, (int, np.integer)):
            raise TypeError("index must be an integer")
        if index < 0 or index >= self.nrows:
            raise IndexError("row index out of range")
        return GF2Vector(self.data[index], verify=False)

    def column(self, index):
        if not isinstance(index, (int, np.integer)):
            raise TypeError("index must be an integer")
        if index < 0 or index >= self.ncols:
            raise IndexError("column index out of range")
        return GF2Vector(self.data[:, index].flatten(), verify=False)
    
    def rows(self):
        return [GF2Vector(self.data[i], verify=False) for i in range(self.nrows)]

    def columns(self):
        return [GF2Vector(self.data[:, i].flatten(), verify=False) for i in range(self.ncols)]

    def transpose(self):
        return GF2Matrix(self.data.T, verify=False)
