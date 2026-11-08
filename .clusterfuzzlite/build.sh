#!/bin/bash -eu
cd "$SRC/waveplan"
export PYTHONPATH="$SRC/waveplan/scripts${PYTHONPATH:+:$PYTHONPATH}"
compile_python_fuzzer .clusterfuzzlite/fuzz_waveplan.py
zip -q -j "$OUT/fuzz_waveplan_seed_corpus.zip" examples/plan.json
printf '[libfuzzer]\nmax_len=16384\n' > "$OUT/fuzz_waveplan.options"
