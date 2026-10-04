# Source after setting repo. A diagnostic alone is never a successful run.
guard="$repo/scripts/validation/result_guard.py"
sim_pass() { python3 "$guard" pass "$@"; }
mutant_caught() { python3 "$guard" mutant "$@"; }
positive_counts() { python3 "$guard" positive "$@"; }
sby_pass() { python3 "$guard" sby-pass "$@"; }
sby_fail() { python3 "$guard" sby-fail "$@"; }
