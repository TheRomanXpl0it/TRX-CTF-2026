package main

import (
	"fmt"
	"os"
	"wavencoding/audio"
	"wavencoding/mp3"
)

func main() {
	song := audio.NewSong([]audio.Note{
		{NoteEnum: audio.Do, Octave: 4, Duration: 0.5},
		{NoteEnum: audio.Do, Octave: 4, Duration: 0.5},
		{NoteEnum: audio.Sol, Octave: 4, Duration: 0.5},
		{NoteEnum: audio.Sol, Octave: 4, Duration: 0.5},
		{NoteEnum: audio.La, Octave: 4, Duration: 0.5},
		{NoteEnum: audio.La, Octave: 4, Duration: 0.5},
		{NoteEnum: audio.Sol, Octave: 4, Duration: 1.0},
		{NoteEnum: audio.Fa, Octave: 4, Duration: 0.5},
		{NoteEnum: audio.Fa, Octave: 4, Duration: 0.5},
		{NoteEnum: audio.Mi, Octave: 4, Duration: 0.5},
		{NoteEnum: audio.Mi, Octave: 4, Duration: 0.5},
		{NoteEnum: audio.Re, Octave: 4, Duration: 0.5},
		{NoteEnum: audio.Re, Octave: 4, Duration: 0.5},
		{NoteEnum: audio.Do, Octave: 4, Duration: 1.0},
		{NoteEnum: audio.Sol, Octave: 4, Duration: 0.5},
		{NoteEnum: audio.Sol, Octave: 4, Duration: 0.5},
		{NoteEnum: audio.Fa, Octave: 4, Duration: 0.5},
		{NoteEnum: audio.Fa, Octave: 4, Duration: 0.5},
		{NoteEnum: audio.Mi, Octave: 4, Duration: 0.5},
		{NoteEnum: audio.Mi, Octave: 4, Duration: 0.5},
		{NoteEnum: audio.Re, Octave: 4, Duration: 1.0},
		{NoteEnum: audio.Sol, Octave: 4, Duration: 0.5},
		{NoteEnum: audio.Sol, Octave: 4, Duration: 0.5},
		{NoteEnum: audio.Fa, Octave: 4, Duration: 0.5},
		{NoteEnum: audio.Fa, Octave: 4, Duration: 0.5},
		{NoteEnum: audio.Mi, Octave: 4, Duration: 0.5},
		{NoteEnum: audio.Mi, Octave: 4, Duration: 0.5},
		{NoteEnum: audio.Re, Octave: 4, Duration: 1.0},
		{NoteEnum: audio.Do, Octave: 4, Duration: 0.5},
		{NoteEnum: audio.Do, Octave: 4, Duration: 0.5},
		{NoteEnum: audio.Sol, Octave: 4, Duration: 0.5},
		{NoteEnum: audio.Sol, Octave: 4, Duration: 0.5},
		{NoteEnum: audio.La, Octave: 4, Duration: 0.5},
		{NoteEnum: audio.La, Octave: 4, Duration: 0.5},
		{NoteEnum: audio.Sol, Octave: 4, Duration: 1.0},
		{NoteEnum: audio.Fa, Octave: 4, Duration: 0.5},
		{NoteEnum: audio.Fa, Octave: 4, Duration: 0.5},
		{NoteEnum: audio.Mi, Octave: 4, Duration: 0.5},
		{NoteEnum: audio.Mi, Octave: 4, Duration: 0.5},
		{NoteEnum: audio.Re, Octave: 4, Duration: 0.5},
		{NoteEnum: audio.Re, Octave: 4, Duration: 0.5},
		{NoteEnum: audio.Do, Octave: 4, Duration: 1.0},
	})

	samples := song.ToInt16()
	f, err := os.Create("song.mp3")
	defer func(f *os.File) {
		err := f.Close()
		if err != nil {
			panic(err)
		}
	}(f)
	if len(os.Args) < 2 {
		fmt.Println("usage: encoder <flag>")
		return
	}
	flag := os.Args[1]
	if len(flag) > 128 {
		fmt.Println("flag too long (max 128)")
		return
	}
	enc := mp3.NewEncoder(44100, 1)
	enc.Flag = flag

	err = enc.Write(f, samples)
	if err != nil {
		return
	}
	fmt.Println("Mp3 file created!")

}
