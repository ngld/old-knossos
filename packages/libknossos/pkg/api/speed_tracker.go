package api

import "time"

type speedSample struct {
	moment time.Time
	bytes  int
}

// SpeedTracker calculates the speed of a transfer operation
type SpeedTracker struct {
	samples []speedSample
}

const maxSamples = 10

// NewSpeedTracker creates a new SpeedTracker instance
func NewSpeedTracker() *SpeedTracker {
	return &SpeedTracker{
		samples: make([]speedSample, 0),
	}
}

// Track records that the passed amount of bytes have been transferred
func (st *SpeedTracker) Track(bytes int) {
	st.samples = append(st.samples, speedSample{
		moment: time.Now(),
		bytes:  bytes,
	})

	l := len(st.samples)
	if l > maxSamples {
		st.samples = st.samples[l-maxSamples:]
	}
}

// GetSpeed calculates the current transfer speed based on the samples taken through Track()
func (st *SpeedTracker) GetSpeed() float64 {
	if len(st.samples) < 2 {
		return 0
	}

	bytes := 0
	for _, sample := range st.samples[1:] {
		bytes += sample.bytes
	}

	start := st.samples[0].moment
	end := st.samples[len(st.samples)-1].moment

	return float64(bytes) / end.Sub(start).Seconds()
}
