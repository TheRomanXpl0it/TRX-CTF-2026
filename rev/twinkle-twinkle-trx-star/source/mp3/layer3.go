package mp3

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/sha256"
	"encoding/binary"
	"fmt"
	"io"
	"math/rand"
	"time"
)

const SHINE_MAX_SAMPLES = 1152

type channel int

const (
	PCM_MONO   channel = 1
	PCM_STEREO channel = 2
)

type mpegVersion int

const (
	MPEG_25 mpegVersion = 0
	MPEG_II mpegVersion = 2
	MPEG_I  mpegVersion = 3
)

type mpegLayer int

// Only Layer III currently implemented
const LAYER_III mpegLayer = 1

var mpegGranulesPerFrame = [4]int{
	// MPEG 2.5
	1,
	// Reserved
	-1,
	// MPEG II
	1,
	// MPEG I
	2,
}

func getMpegVersion(sampleRateIndex int) mpegVersion {
	if sampleRateIndex < 3 {
		return MPEG_I
	} else if sampleRateIndex < 6 {
		return MPEG_II
	} else {
		return MPEG_25
	}
}

// findSampleRateIndex checks if a given sampleRate is supported by the encoder
func findSampleRateIndex(freq int) (int, error) {
	var i int
	for i = 0; i < 9; i++ {
		if freq == int(sampleRates[i]) {
			return i, nil
		}
	}
	return -1, fmt.Errorf("unsupported frequency: %v", freq)
}

// findBitrateIndex checks if a given bitrate is supported by the encoder
func findBitrateIndex(bitrate int, mpegVer mpegVersion) (int, error) {
	var i int
	for i = 0; i < 16; i++ {
		if bitrate == int(bitRates[i][mpegVer]) {
			return i, nil
		}
	}
	return -1, fmt.Errorf("unsupported bitrate: %v", bitrate)
}

// CheckConfig checks if a given bitrate and sampleRate is supported by the encoder
func CheckConfig(freq int, bitrate int) (mpegVersion, error) {
	sampleRateIndex, err := findSampleRateIndex(freq)
	if err != nil {
		return -1, err
	}
	mpegVer := getMpegVersion(sampleRateIndex)
	_, err = findBitrateIndex(bitrate, mpegVer)
	if err != nil {
		return -1, err
	}
	return mpegVer, nil
}

// samplesPerPass returns the audio samples expected in each frame.
func (enc *Encoder) samplesPerPass() int64 {
	return enc.Mpeg.GranulesPerFrame * GRANULE_SIZE
}

func patchFrameHeader(frame []uint8, padding int64, mainDataBegin int64) {
	if len(frame) < 6 {
		return
	}
	frame[0] = 0xFF
	frame[1] = 0xFB
	frame[2] = 0x90 | byte((padding&1)<<1)
	frame[3] = 0xC4
	frame[4] = byte((mainDataBegin >> 1) & 0xFF)
	frame[5] = (frame[5] & 0x7F) | byte((mainDataBegin&1)<<7)
}

// NewEncoder creates a new encoder with sensible encoding defaults
func NewEncoder(sampleRate, channels int) *Encoder {
	enc := new(Encoder)

	if channels > 1 {
		enc.Mpeg.Mode = STEREO
	} else {
		enc.Mpeg.Mode = MONO
	}

	enc.subbandInitialize()
	enc.mdctInitialize()
	enc.loopInitialize()
	enc.Wave.Channels = int64(channels)
	enc.Wave.SampleRate = int64(sampleRate)
	enc.Mpeg.Bitrate = 128
	enc.Mpeg.Emphasis = NONE
	enc.Mpeg.Copyright = 0
	enc.Mpeg.Original = 1
	enc.reservoirMaxSize = 0
	enc.reservoirSize = 0
	enc.Mpeg.Layer = int64(LAYER_III)
	enc.Mpeg.Crc = 0
	enc.Mpeg.Ext = 0
	enc.Mpeg.ModeExt = 0
	enc.Mpeg.BitsPerSlot = 8

	sampleRateIndex, _ := findSampleRateIndex(int(enc.Wave.SampleRate))
	enc.Mpeg.SampleRateIndex = int64(sampleRateIndex)

	enc.Mpeg.Version = getMpegVersion(int(enc.Mpeg.SampleRateIndex))

	bitrateIndex, _ := findBitrateIndex(int(enc.Mpeg.Bitrate), enc.Mpeg.Version)
	enc.Mpeg.BitrateIndex = int64(bitrateIndex)

	enc.Mpeg.GranulesPerFrame = int64(mpegGranulesPerFrame[enc.Mpeg.Version])
	avg_slots_per_frame := (float64(enc.Mpeg.GranulesPerFrame) * GRANULE_SIZE / (float64(enc.Wave.SampleRate))) * (float64(enc.Mpeg.Bitrate) * 1000 / float64(enc.Mpeg.BitsPerSlot))
	enc.Mpeg.WholeSlotsPerFrame = int64(avg_slots_per_frame)
	enc.Mpeg.FracSlotsPerFrame = avg_slots_per_frame - float64(enc.Mpeg.WholeSlotsPerFrame)
	enc.Mpeg.SlotLag = -enc.Mpeg.FracSlotsPerFrame
	if enc.Mpeg.FracSlotsPerFrame == 0 {
		enc.Mpeg.Padding = 0
	}
	enc.bitstream.open(BUFFER_SIZE)
	enc.Seed = time.Now().UnixMilli() % 1024
	enc.Rng = rand.New(rand.NewSource(enc.Seed))

	// determine the mean bitrate for main data
	if enc.Mpeg.GranulesPerFrame == 2 {
		// MPEG 1
		delta := 4 + 32
		if enc.Wave.Channels == 1 {
			delta = 4 + 17
		}
		enc.sideInfoLen = int64(8 * delta)
	} else {
		// MPEG 2
		delta := 4 + 17
		if enc.Wave.Channels == 1 {
			delta = 4 + 9
		}
		enc.sideInfoLen = int64(8 * delta)
	}
	return enc
}
func (enc *Encoder) encodeBufferInternal(stride int) ([]uint8, int) {
	slotLag := enc.Mpeg.SlotLag
	padding := enc.Mpeg.Padding
	reservoirSize := enc.reservoirSize
	mainDataBegin := enc.mainDataBegin
	sideInfo := enc.sideInfo
	buffer := enc.buffer
	subband := enc.subband
	subbandSamples := enc.l3SubbandSamples
	savedS := enc.S
	bufByteIdx := enc.bitstream.bufByteIdx
	bufBitIdx := enc.bitstream.bufBitIdx
	totBit := enc.bitstream.totBit

	retry := true
frame:
	if enc.Mpeg.FracSlotsPerFrame != 0 {
		if enc.Mpeg.SlotLag <= (enc.Mpeg.FracSlotsPerFrame - 1.0) {
			enc.Mpeg.Padding = 1
		} else {
			enc.Mpeg.Padding = 0
		}
		enc.Mpeg.SlotLag += float64(enc.Mpeg.Padding) - enc.Mpeg.FracSlotsPerFrame
	}
	enc.Mpeg.BitsPerFrame = (enc.Mpeg.WholeSlotsPerFrame + enc.Mpeg.Padding) * 8
	enc.meanBits = (enc.Mpeg.BitsPerFrame - enc.sideInfoLen) / enc.Mpeg.GranulesPerFrame
	currentTarget := int64(0)
	if enc.PlanIdx < len(enc.Plan) {
		currentTarget = enc.Plan[enc.PlanIdx]
	}
	enc.mainDataBegin = currentTarget
	if len(enc.Plan) > 0 {
		nextTarget := int64(0)
		if enc.PlanIdx+1 < len(enc.Plan) {
			nextTarget = enc.Plan[enc.PlanIdx+1]
		}
		mainBytes := (enc.Mpeg.BitsPerFrame - enc.sideInfoLen) / 8
		wantBytes := currentTarget + 32
		maxBytes := mainBytes - nextTarget
		if maxBytes < 32 {
			maxBytes = 32
		}
		if wantBytes > maxBytes {
			wantBytes = maxBytes
		}
		if wantBytes < 32 {
			wantBytes = 32
		}
		enc.meanBits = (wantBytes * 8) / enc.Mpeg.GranulesPerFrame
	}

	// apply mdct to the polyphase output
	enc.mdctSub(int64(stride))

	// bit and noise allocation
	enc.resvFrameBegin()
	enc.iterationLoop()

	// write the frame to the bitstream
	enc.formatBitstream()

	// Return data
	written := enc.bitstream.dataPosition
	enc.bitstream.dataPosition = 0
	if retry {
		retry = false
		enc.Mpeg.SlotLag = slotLag
		enc.Mpeg.Padding = padding
		enc.reservoirSize = reservoirSize
		enc.mainDataBegin = mainDataBegin
		enc.sideInfo = sideInfo
		enc.buffer = buffer
		enc.subband = subband
		enc.l3SubbandSamples = subbandSamples
		enc.S = savedS
		enc.bitstream.bufByteIdx = bufByteIdx
		enc.bitstream.bufBitIdx = bufBitIdx
		enc.bitstream.totBit = totBit
		goto frame
	}
	if enc.PlanIdx < len(enc.Plan) {
		enc.PlanIdx++
	}
	enc.bitstream.bufByteIdx = 0
	enc.bitstream.bufBitIdx = 8
	enc.bitstream.totBit = 0
	enc.bitstream.data[0] = 0
	return enc.bitstream.data, written
}

func (enc *Encoder) EncodeBufferInterleaved(data []int16) ([]uint8, int) {
	enc.bufferData = data
	enc.buffer[0] = 0
	if enc.Wave.Channels == 2 {
		enc.buffer[1] = 1
	}
	return enc.encodeBufferInternal(int(enc.Wave.Channels))
}

func (enc *Encoder) frameBytes() int {
	return int(enc.Mpeg.WholeSlotsPerFrame + enc.Mpeg.Padding)
}

type mp3Frame struct {
	data   []byte
	used   int
	target int64
}

func makeReservoirReal(frames []mp3Frame, mainStart int) error {
	for i := range frames {
		target := int(frames[i].target)
		if target == 0 {
			continue
		}
		if i == 0 || target > 511 {
			return io.ErrShortBuffer
		}
		if frames[i].used < mainStart {
			frames[i].used = mainStart
		}
		if mainStart+target > frames[i].used {
			return io.ErrShortBuffer
		}
		dst := len(frames[i-1].data) - target
		if dst < frames[i-1].used {
			return io.ErrShortBuffer
		}
		moved := append([]byte(nil), frames[i].data[mainStart:mainStart+target]...)
		copy(frames[i-1].data[dst:], moved)
		copy(frames[i].data[mainStart:], frames[i].data[mainStart+target:frames[i].used])
		for j := frames[i].used - target; j < frames[i].used; j++ {
			frames[i].data[j] = 0
		}
		frames[i].used -= target
	}
	return nil
}

func (enc *Encoder) writePass(out io.Writer, data []int16) error {
	samplesPerPass := int(enc.samplesPerPass()) * int(enc.Wave.Channels)
	samplesRead := len(data)
	fi := 0
	frames := []mp3Frame{}
	mainStart := int(enc.sideInfoLen / 8)

	for i := 0; i < samplesRead; i += samplesPerPass {
		end := i + samplesPerPass
		if end > samplesRead {
			end = samplesRead
		}
		outputData, written := enc.EncodeBufferInterleaved(data[i:end])
		frameBytes := enc.frameBytes()
		used := written
		if written > frameBytes {
			written = frameBytes
		}
		if used > frameBytes {
			used = frameBytes
		}
		if written < frameBytes {
			for j := written; j < frameBytes; j++ {
				outputData[j] = 0
			}
			written = frameBytes
		}
		_ = fi
		fi++
		patchFrameHeader(outputData[:written], enc.Mpeg.Padding, enc.mainDataBegin)
		if out != nil {
			frame := make([]byte, written)
			copy(frame, outputData[:written])
			frames = append(frames, mp3Frame{data: frame, used: used, target: enc.mainDataBegin})
		}
	}
	if out != nil {
		if err := makeReservoirReal(frames, mainStart); err != nil {
			return err
		}
		for _, frame := range frames {
			if err := binary.Write(out, binary.LittleEndian, frame.data); err != nil {
				return err
			}
		}
	}
	return nil
}

func (enc *Encoder) Write(out io.Writer, data []int16) error {
	samples_per_pass := int(enc.samplesPerPass())
	samplesRead := len(data)
	totalFrames := 0

	for i := 0; i < samplesRead; i += samples_per_pass * int(enc.Wave.Channels) {
		end := i + samples_per_pass*int(enc.Wave.Channels)
		if end > samplesRead {
			end = samplesRead
		}
		chunk := data[i:end]
		enc.EncodeBufferInterleaved(chunk)
		totalFrames++
	}

	enc.resetForSecondPass()
	if err := enc.writePass(nil, data); err != nil {
		return err
	}
	keyS := enc.S
	enc.buildPlan(totalFrames)
	enc.resetForSecondPass()
	if err := enc.writePass(out, data); err != nil {
		return err
	}
	enc.S = keyS
	return nil
}

func (enc *Encoder) buildPlan(totalFrames int) {
	var keyMaterial [8]byte
	binary.LittleEndian.PutUint64(keyMaterial[:], uint64(enc.S))
	sum := sha256.Sum256(keyMaterial[:])
	block, _ := aes.NewCipher(sum[:16])
	iv := []byte{0x67, 0x67, 0x67, 0x67, 0x67, 0x67, 0x67, 0x67, 0x67, 0x67, 0x67, 0x67, 0x67, 0x67, 0x67, 0x67}
	stream := cipher.NewCTR(block, iv)
	pt := []byte(enc.Flag)
	ct := make([]byte, len(pt))
	stream.XORKeyStream(ct, pt)

	plan := make([]int64, 0, 2*len(ct)+1)
	plan = append(plan, 0)
	prev := int64(0)
	for _, b := range ct {
		target := prev + int64(b)
		if target > 255 {
			plan = append(plan, 0)
			prev = 0
			target = int64(b)
		}
		if len(plan) > 0 && plan[len(plan)-1]+target > 255 {
			plan = append(plan, 0)
			prev = 0
			target = int64(b)
		}
		if target == 0 {
			plan = append(plan, 0, 0)
			prev = 0
			continue
		}
		plan = append(plan, target)
		prev = target
	}
	enc.Plan = plan
	enc.PlanIdx = 0
}

func (enc *Encoder) resetForSecondPass() {
	enc.S = 0
	enc.Rng = rand.New(rand.NewSource(enc.Seed))
	enc.reservoirSize = 0
	enc.mainDataBegin = 0
	enc.bitstream.dataPosition = 0
	enc.bitstream.bufByteIdx = 0
	enc.bitstream.bufBitIdx = 8
	enc.bitstream.totBit = 0
	enc.bitstream.data[0] = 0
	enc.Mpeg.SlotLag = -enc.Mpeg.FracSlotsPerFrame
	enc.Mpeg.Padding = 0
	for ch := 0; ch < MAX_CHANNELS; ch++ {
		for g := 0; g < MAX_GRANULES+1; g++ {
			for k := 0; k < 18; k++ {
				for b := 0; b < SUBBAND_LIMIT; b++ {
					enc.l3SubbandSamples[ch][g][k][b] = 0
				}
			}
		}
	}
	enc.subband = Subband{}
	enc.subbandInitialize()
}
