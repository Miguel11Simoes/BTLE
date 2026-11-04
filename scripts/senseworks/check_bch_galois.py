"""Check tag_bch.py against an independent BCH implementation, the galois library.

Author: Miguel Simões

For t = 8, 12 and 18: the generator polynomial of galois.BCH(255, k) against tag_bch.GENERATORS, the
parity of random messages (galois's systematic shortened encoder) against tag_bch.encode_bits, and
galois's decoder against tag_bch.decode_bits on words with 0 to 2t errors. galois is not one of the
repository's dependencies: run it with an interpreter that has it (pip install galois).

  python3 scripts/senseworks/check_bch_galois.py [--trials N]
"""

from __future__ import annotations

import argparse
from pathlib import Path
import random
import sys

import galois
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tag_bch  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--trials", type=int, default=500)
    args = parser.parse_args()
    rng = random.Random(20261104)
    print(f"galois {galois.__version__}, GF(2^8) irreducible polynomial {galois.GF(2**8).irreducible_poly}")
    assert int(galois.GF(2**8).irreducible_poly) == tag_bch.PRIMITIVE
    for t in tag_bch.TS:
        deg = tag_bch.degree(t)
        code = galois.BCH(255, 255 - deg)
        assert code.t == t, f"galois BCH(255, {255 - deg}) corrects {code.t}, not {t}"
        g = int(code.generator_poly)
        assert g == tag_bch.GENERATORS[t], f"t={t}: generator differs"
        n = tag_bch.MESSAGE_BITS + deg
        k = tag_bch.MESSAGE_BITS
        same_parity = decoded_same = 0
        for trial in range(args.trials):
            msg = [rng.getrandbits(1) for _ in range(k)]
            ours = msg + tag_bch.encode_bits(msg, t)
            theirs = code.encode(galois.GF2(np.array(msg, dtype=int)))   # shortened by 255 - deg - k
            assert len(theirs) == n
            assert [int(b) for b in theirs] == ours, f"t={t}: the parity differs"
            same_parity += 1
            w = trial % (2 * t + 1)
            bad = list(ours)
            for p in rng.sample(range(n), w):
                bad[p] ^= 1
            ours_out = tag_bch.decode_bits(bad, t)
            theirs_out, errors = code.decode(galois.GF2(np.array(bad, dtype=int)), output="codeword", errors=True)
            theirs_out = None if errors < 0 else [int(b) for b in theirs_out]
            assert ours_out == theirs_out, f"t={t}, {w} errors: the decoders differ"
            if w <= t:
                assert ours_out == ours
            decoded_same += 1
        print(f"t = {t:2}: generator equal (deg {deg}); {same_parity} messages, parity equal; "
              f"{decoded_same} words with 0..{2 * t} errors, both decoders give the same result")
    print("PASS")


if __name__ == "__main__":
    main()
