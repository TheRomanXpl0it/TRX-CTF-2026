package audio

import (
	"encoding/binary"
	"math"
)

type NoteEnum int

const (
	Do NoteEnum = iota
	Re
	Mi
	Fa
	Sol
	La
	Si
)

var NoteToFrequency = map[NoteEnum]float64{
	Do:  261.63,
	Re:  293.66,
	Mi:  329.63,
	Fa:  349.23,
	Sol: 392.00,
	La:  440.00,
	Si:  493.88,
}

func (n NoteEnum) String() string {
	switch n {
	case Do:
		return "Do"
	case Re:
		return "Re"
	case Mi:
		return "Mi"
	case Fa:
		return "Fa"
	case Sol:
		return "Sol"
	case La:
		return "La"
	case Si:
		return "Si"
	default:
		return "Do"
	}
}

func (n NoteEnum) FromString(str string) NoteEnum {
	switch str {
	case "Do":
		return Do
	case "Re":
		return Re
	case "Mi":
		return Mi
	case "Fa":
		return Fa
	case "Sol":
		return Sol
	case "La":
		return La
	case "Si":
		return Si
	default:
		return Do
	}
}

type Note struct {
	NoteEnum NoteEnum
	Octave   int
	Duration float64
}

type Song []float64

func (s Song) ToPcm() []byte {
	pcm := make([]byte, len(s)*2)

	for i, sample := range s {
		if sample > 1 {
			sample = 1
		}
		if sample < -1 {
			sample = -1
		}

		pcmSample := int16(sample * 32767)
		binary.LittleEndian.PutUint16(pcm[i*2:], uint16(pcmSample))
	}

	return pcm
}

func (s Song) ToInt16() []int16 {
	pcm := make([]int16, len(s))

	for i, sample := range s {
		if sample > 1 {
			sample = 1
		}
		if sample < -1 {
			sample = -1
		}

		pcm[i] = int16(sample * 32767)
	}

	return pcm
}

func SineWave(freq float64, duration float64, sampleRate int) []float64 {
	n := int(duration * float64(sampleRate))
	out := make([]float64, n)
	const amplitude = 0.7

	for i := 0; i < n; i++ {
		t := float64(i) / float64(sampleRate)
		out[i] = amplitude * math.Sin(2*math.Pi*freq*t)
	}

	return out
}

func NewSong(notes []Note) Song {

	var song Song
	for _, note := range notes {
		freq := NoteToFrequency[note.NoteEnum] * math.Pow(2, float64(note.Octave-4))
		samples := SineWave(freq, float64(note.Duration), 44100)
		song = append(song, samples...)
	}
	return song

}
