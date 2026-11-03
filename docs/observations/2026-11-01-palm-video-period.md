# Palm period in the original menu recording

The user supplied a 1600x1200 menu recording on 2026-11-01. VLC sampled the stationary menu at 400x300, ten samples per second over 26 seconds (261 samples). The VLC time readout ran from 28.652 to 54.402 seconds. Fits use the monotonic sampling clock at normal playback speed. Sub-second seek/readout uncertainty limits precision.

For each image patch, the green channel was aligned to the temporal median using a linearized two-axis translation with brightness and contrast terms. A least-squares sinusoid was fitted to both translation axes across 0.10 through 1.00 Hz at 0.002 Hz intervals. The table gives the best full-window period, the independent half-window fits and the fraction of displacement variance explained over the full window. Coordinates refer to the 400x300 analysis image, measured from its top left. The sampled regions can contain overlapping geometry.

| Region (x, y, width, height) | Full period | First / second half | Variance explained |
| --- | ---: | ---: | ---: |
| Left crown (103, 108, 36, 28) | 4.17 s | 4.20 / 4.17 s | 89% |
| Center-left fronds (136, 132, 36, 23) | 4.17 s | 4.13 / 4.24 s | 82% |

Fitted semi-amplitudes are 0.72 and 1.02 pixels respectively at the analysis resolution. A control on the logo lettering gives about 0.001 pixel and an unstable period between halves. The lower foreground leaf and upper-right foliage peak at the slow edge of the search range. Their period is unresolved in this measurement.

The two left-side measurements agree with the predicted 2*pi/1.5 = 4.19 seconds at normal effective engine time. Object identity, amplitude parity with the viewer, sign of motion and startup phase are still unverified. The recording and extracted frames are local research inputs.
