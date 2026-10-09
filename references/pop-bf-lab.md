# External reference: FulGerNet/pop-bf-lab

Reviewed 2026-10-09. Author/project: FulGerNet.
[Repository](https://github.com/FulGerNet/pop-bf-lab), pinned revision
`76ac78a10751a08fda67e8d5f711171e6f2d9605`, commit date 2026-09-27.

Reviewed portions: README, archive index parsing in
[`bf_lab/archives.py`](https://github.com/FulGerNet/pop-bf-lab/blob/76ac78a10751a08fda67e8d5f711171e6f2d9605/bf_lab/archives.py)
and related constants in config.py. The useful next observation was that the
metadata location can be calculated from capacity rather than a fixed address.
Local tests verify the resulting names, offsets and sizes on the PC GOG archive.

The README mentions research using Jade Engine source layout and binary
definitions. This reference is used as a source of hypotheses to verify against
data; no original engine code or upstream code files are included in OpenJade.
No licensing or clean-room certification is claimed. Mesh, texture, compression
and OVA capabilities advertised by that project have not been validated here.

Compression follow-up, 2026-10-09: inspected `archives.py` and
[`lzo.py`](https://github.com/FulGerNet/pop-bf-lab/blob/76ac78a10751a08fda67e8d5f711171e6f2d9605/bf_lab/lzo.py)
at the same pinned revision. Used the marker positions, little-endian size
pairs and 0x20000 block limit as hypotheses for an independently written
structural probe. [Local observations](../docs/observations/2026-10-09-big-compression.md)
support candidate envelopes, not codec correctness. No upstream decoder or
binary dependency was copied, executed or installed.
