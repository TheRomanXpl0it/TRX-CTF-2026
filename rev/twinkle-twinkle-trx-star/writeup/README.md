# Twinkle Twinkle TRX Star

This is a reverse engineering challenge written in Go and obfuscated with garble.

The binary is basically a custom MP3 encoder. It produces the sine wave of `Twinkle Twinkle Little Star` and encodes it in MP3 format.

The binary generates 1024 possible AES keys and produces a different MP3 on each run by slightly changing the MDCT coefficients. The values are then summed to derive the AES key, while the IV is 16 `0x67` bytes.

The ciphertext is then hidden in the bit reservoir of the MP3 file, where the reservoir value keeps a cumulative sum of the ciphertext bytes. A zero is used as a flush to reset the sum, while two zeroes in a row encode an actual zero byte.

The flag can then be recovered by trying one of the 1024 keys on the ciphertext.
