package audio

import (
	"encoding/binary"
	"fmt"
	"os"
)

type RiffHeader struct {
	ChunkID   [4]byte
	ChunkSize uint32
	Format    [4]byte
}

type FmtSubchunk struct {
	ChunkID       [4]byte
	ChunkSize     uint32
	AudioFormat   uint16
	NumChannels   uint16
	SampleRate    uint32
	ByteRate      uint32
	BlockAlign    uint16
	BitsPerSample uint16
}

type DataSubchunk struct {
	ChunkID   [4]byte
	ChunkSize uint32
	Data      []byte
}

type Wavfile struct {
	RiffHeader   RiffHeader
	FmtSubchunk  FmtSubchunk
	DataSubchunk DataSubchunk
}

func (w Wavfile) WriteFile() {

	file, err := os.OpenFile("twinkle.wav", os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0644)
	if err != nil {
		fmt.Println("Error creating file:", err)
		panic(err)
	}
	defer file.Close()

	chunkIdErr := binary.Write(file, binary.LittleEndian, w.RiffHeader.ChunkID)
	chunkSizeErr := binary.Write(file, binary.LittleEndian, w.RiffHeader.ChunkSize)
	formatErr := binary.Write(file, binary.LittleEndian, w.RiffHeader.Format)

	fmtChunkIdErr := binary.Write(file, binary.LittleEndian, w.FmtSubchunk.ChunkID)
	fmtChunkSizeErr := binary.Write(file, binary.LittleEndian, w.FmtSubchunk.ChunkSize)
	audioFormatErr := binary.Write(file, binary.LittleEndian, w.FmtSubchunk.AudioFormat)
	numChannelsErr := binary.Write(file, binary.LittleEndian, w.FmtSubchunk.NumChannels)
	sampleRateErr := binary.Write(file, binary.LittleEndian, w.FmtSubchunk.SampleRate)
	byteRateErr := binary.Write(file, binary.LittleEndian, w.FmtSubchunk.ByteRate)
	blockAlignErr := binary.Write(file, binary.LittleEndian, w.FmtSubchunk.BlockAlign)
	bitsPerSampleErr := binary.Write(file, binary.LittleEndian, w.FmtSubchunk.BitsPerSample)

	dataChunkIdErr := binary.Write(file, binary.LittleEndian, w.DataSubchunk.ChunkID)
	dataChunkSizeErr := binary.Write(file, binary.LittleEndian, w.DataSubchunk.ChunkSize)
	dataErr := binary.Write(file, binary.LittleEndian, w.DataSubchunk.Data)

	if chunkIdErr != nil || chunkSizeErr != nil || formatErr != nil || fmtChunkIdErr != nil || fmtChunkSizeErr != nil || audioFormatErr != nil || numChannelsErr != nil || sampleRateErr != nil || byteRateErr != nil || blockAlignErr != nil || bitsPerSampleErr != nil || dataChunkIdErr != nil || dataChunkSizeErr != nil || dataErr != nil {
		panic("Error writing WAV file")
	}

}

func NewWavfile(song Song) Wavfile {

	pcm := song.ToPcm()

	dataSize := uint32(len(pcm))
	pad := dataSize % 2
	riffSize := 36 + dataSize + pad
	blockAlign := 1 * (16 / 8)
	byteRate := uint32(blockAlign) * 44100

	w := Wavfile{
		RiffHeader: RiffHeader{
			ChunkID:   [4]byte{'R', 'I', 'F', 'F'},
			ChunkSize: riffSize,
			Format:    [4]byte{'W', 'A', 'V', 'E'},
		},
		FmtSubchunk: FmtSubchunk{
			ChunkID:       [4]byte{'f', 'm', 't', ' '},
			ChunkSize:     16,
			AudioFormat:   1,
			NumChannels:   1,
			SampleRate:    44100,
			ByteRate:      byteRate,
			BlockAlign:    uint16(blockAlign),
			BitsPerSample: 16,
		},
		DataSubchunk: DataSubchunk{
			ChunkID:   [4]byte{'d', 'a', 't', 'a'},
			ChunkSize: dataSize,
			Data:      pcm,
		},
	}

	return w

}
