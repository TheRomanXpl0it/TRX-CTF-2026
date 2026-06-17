// Layer3 bit reservoir: Described in C.1.5.4.2.2 of the IS
package mp3

func (enc *Encoder) resvFrameBegin() {
	frameLength := enc.Mpeg.BitsPerFrame / 8
	meanBits := (frameLength - (enc.sideInfoLen / 8)) / enc.Mpeg.GranulesPerFrame
	resvLimit := (int64(8) * 256) * enc.Mpeg.GranulesPerFrame
	maxmp3buf := int64(8) * 1951
	enc.reservoirMaxSize = 0
	if frameLength > 7680 {
		enc.reservoirMaxSize = maxmp3buf - frameLength
	}
	if enc.reservoirMaxSize > resvLimit {
		enc.reservoirMaxSize = resvLimit
	}
	if enc.reservoirMaxSize > maxmp3buf-((enc.sideInfoLen/8)+int64(6*enc.Mpeg.GranulesPerFrame))*8 {
		enc.reservoirMaxSize = maxmp3buf - ((enc.sideInfoLen/8)+int64(6*enc.Mpeg.GranulesPerFrame))*8
	}
	if enc.reservoirMaxSize < 0 {
		enc.reservoirMaxSize = 0
	}
	_ = meanBits
}

// maxReservoirBits is called at the beginning of each granule to get the max bit
// allowance for the current granule based on reservoir size and perceptual entropy.
func (enc *Encoder) maxReservoirBits(perceptualEntropy *float64) int64 {
	meanBits := enc.meanBits

	meanBits /= enc.Wave.Channels
	maxBits := meanBits
	if maxBits > 4095 {
		maxBits = 4095
	}
	if enc.reservoirMaxSize == 0 {
		return maxBits
	}
	moreBits := int64(*perceptualEntropy*3.1 - float64(meanBits))
	addBits := int64(0)
	if moreBits > 100 {
		var frac int64 = (enc.reservoirSize * 6) / 10
		if frac < moreBits {
			addBits = frac
		} else {
			addBits = moreBits
		}
	}
	overBits := enc.reservoirSize - (enc.reservoirMaxSize<<3)/10 - addBits
	if overBits > 0 {
		addBits += overBits
	}
	maxBits += addBits
	if maxBits > 4095 {
		maxBits = 4095
	}
	if len(enc.Plan) > 0 && maxBits > meanBits {
		maxBits = meanBits
	}
	return maxBits
}

// reservoirAdjust is called after a granule's bit allocation. It readjusts the size of
// the reservoir to reflect the granule's usage.
func (enc *Encoder) reservoirAdjust(gi *GranuleInfo) {
	enc.reservoirSize -= int64(gi.Part2_3Length)
}

func (enc *Encoder) reservoirFrameEnd() {
	sideInfo := &enc.sideInfo
	sideInfo.ReservoirDrainPre = 0
	sideInfo.ReservoirDrainPost = 0
	enc.reservoirSize += (enc.meanBits / enc.Wave.Channels) * enc.Mpeg.GranulesPerFrame

	ancillaryPad := int64(0)
	if enc.Wave.Channels == 2 && (enc.meanBits&1) != 0 {
		enc.reservoirSize += 1
	}
	overBits := enc.reservoirSize - enc.reservoirMaxSize
	if overBits < 0 {
		overBits = 0
	}
	enc.reservoirSize -= overBits
	stuffingBits := overBits + ancillaryPad

	overBits = enc.reservoirSize % 8
	if overBits != 0 {
		stuffingBits += overBits
		enc.reservoirSize -= overBits
	}
	if len(enc.Plan) > 0 && enc.PlanIdx+1 < len(enc.Plan) {
		reserveBits := enc.Plan[enc.PlanIdx+1] * 8
		if reserveBits > stuffingBits {
			reserveBits = stuffingBits
		}
		stuffingBits -= reserveBits
	}

	if stuffingBits != 0 {
		granInfo := &(sideInfo.Granules[0].Channels[0]).Tt
		if granInfo.Part2_3Length+uint64(stuffingBits) < 4095 {
			granInfo.Part2_3Length += uint64(stuffingBits)
		} else {
			for gr := int64(0); gr < enc.Mpeg.GranulesPerFrame; gr++ {
				for ch := int64(0); ch < enc.Wave.Channels; ch++ {
					granInfo := &(sideInfo.Granules[gr].Channels[ch]).Tt
					if stuffingBits == 0 {
						break
					}
					extraBits := int64(4095 - granInfo.Part2_3Length)
					bitsThisGranule := int64(0)
					if extraBits < stuffingBits {
						bitsThisGranule = extraBits
					} else {
						bitsThisGranule = stuffingBits
					}
					granInfo.Part2_3Length += uint64(bitsThisGranule)
					stuffingBits -= bitsThisGranule
				}
			}
			sideInfo.ReservoirDrain = stuffingBits
			sideInfo.ReservoirDrainPost = stuffingBits
		}
	}
}
