package mp3

const BUFFER_SIZE = 4096

type bitstream struct {
	data         []uint8
	dataSize     int
	dataPosition int
	bufByteIdx   int
	bufBitIdx    int
	totBit       int64
}

func (bs *bitstream) open(size int) {
	bs.data = make([]uint8, size)
	bs.dataSize = size
	bs.dataPosition = 0
	bs.bufByteIdx = 0
	bs.bufBitIdx = 8
	bs.totBit = 0
}

func (bs *bitstream) ensure(n int) {
	for bs.bufByteIdx+n >= bs.dataSize {
		newCapacity := bs.dataSize + (bs.dataSize >> 1)
		newSlice := make([]byte, newCapacity)
		copy(newSlice, bs.data)
		bs.data = newSlice
		bs.dataSize = newCapacity
	}
}

func (bs *bitstream) putBits(val uint32, n uint) {
	j := int(n)
	for j > 0 {
		if bs.bufBitIdx == 0 {
			bs.bufByteIdx++
			bs.ensure(1)
			bs.data[bs.bufByteIdx] = 0
			bs.bufBitIdx = 8
		}
		k := j
		if bs.bufBitIdx < k {
			k = bs.bufBitIdx
		}
		j -= k
		bs.bufBitIdx -= k
		bs.data[bs.bufByteIdx] |= byte((val >> uint(j)) << uint(bs.bufBitIdx))
		bs.totBit += int64(k)
		if bs.dataPosition < bs.bufByteIdx+1 {
			bs.dataPosition = bs.bufByteIdx + 1
		}
	}
}

func (bs *bitstream) getBitsCount() int {
	return int(bs.totBit)
}
