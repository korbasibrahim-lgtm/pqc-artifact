#!/usr/bin/env bash
# run_campaign.sh -- re-run the measurement campaign of the paper with the
# controls a reviewer will ask for: one pinned core, a recorded CPU governor,
# repeated windows, certificate sizes in DER as well as PEM, certificate
# timing over many runs, and per-signature latency distributions.
#
# This script follows the protocol described in Section IV of the paper
# (liboqs speed_sig / speed_kem, openssl speed -seconds 3, openssl req -x509).
# Reconcile the algorithm names below with your builds before running:
#   <liboqs>/build/tests/speed_sig --algs
#   openssl list -signature-algorithms -provider oqsprovider
#
# Usage:
#   LIBOQS_BUILD=/path/to/liboqs/build CORE=2 ./run_campaign.sh
#
# Recommended before running (needs root):
#   cpupower frequency-set -g performance
# On hybrid CPUs choose CORE on a performance core (lscpu --extended).
set -euo pipefail

LIBOQS_BUILD=${LIBOQS_BUILD:?set LIBOQS_BUILD to the liboqs build directory}
CORE=${CORE:-2}                 # logical CPU the benchmarks are pinned to
DURATION=${DURATION:-3}         # seconds per operation window (paper: 3)
REPS=${REPS:-5}                 # repetitions of each window
CERT_RUNS=${CERT_RUNS:-30}      # certificate generations per algorithm
LAT_SAMPLES=${LAT_SAMPLES:-200000}
OPENSSL=${OPENSSL:-openssl}
PROVIDER_ARGS=${PROVIDER_ARGS:--provider oqsprovider -provider default}
OUT=${OUT:-results_$(date +%Y%m%d_%H%M%S)}

SIG_ALGS=${SIG_ALGS:-"ML-DSA-44 ML-DSA-65 ML-DSA-87 Falcon-512 Falcon-1024 SLH_DSA_PURE_SHA2_128F SLH_DSA_PURE_SHA2_192F SLH_DSA_PURE_SHA2_256F"}
KEM_ALGS=${KEM_ALGS:-"ML-KEM-512 ML-KEM-768 ML-KEM-1024"}
CLASSICAL=${CLASSICAL:-"rsa2048 rsa3072 rsa4096 ecdsap256 ecdsap384 ecdhp256 ecdhp384 ecdhx25519"}
# -newkey arguments; append the SLH-DSA name your provider lists
CERT_ALGS=${CERT_ALGS:-"rsa:2048 rsa:4096 falcon512 falcon1024 mldsa44 mldsa65 mldsa87"}
LAT_ALGS=${LAT_ALGS:-"ML-DSA-44 ML-DSA-65 ML-DSA-87 Falcon-512 Falcon-1024"}

HERE=$(cd "$(dirname "$0")" && pwd)
PIN="taskset -c $CORE"
mkdir -p "$OUT"/{pq,classical,certs,latency}

# ---------------------------------------------------------------- environment
{
  echo "date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "kernel: $(uname -srm)"
  echo "cpu: $(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2- | xargs)"
  echo "pinned core: $CORE"
  g=/sys/devices/system/cpu/cpu$CORE/cpufreq/scaling_governor
  echo "governor: $([ -r "$g" ] && cat "$g" || echo unavailable)"
  t=/sys/devices/system/cpu/intel_pstate/no_turbo
  echo "intel_pstate no_turbo: $([ -r "$t" ] && cat "$t" || echo unavailable)"
  echo "gcc: $(gcc --version | head -1)"
  echo "openssl: $($OPENSSL version)"
  src=$(dirname "$LIBOQS_BUILD")
  echo "liboqs: $(git -C "$src" describe --tags --always 2>/dev/null || echo unknown)"
  echo "duration: $DURATION s, repetitions: $REPS"
} | tee "$OUT/environment.txt"

# ------------------------------------------------- post-quantum primitives
for alg in $SIG_ALGS; do
  for r in $(seq 1 "$REPS"); do
    $PIN "$LIBOQS_BUILD/tests/speed_sig" --info --duration "$DURATION" "$alg" > "$OUT/pq/sig_${alg}_r$r.txt"
  done
done
for alg in $KEM_ALGS; do
  for r in $(seq 1 "$REPS"); do
    $PIN "$LIBOQS_BUILD/tests/speed_kem" --info --duration "$DURATION" "$alg" > "$OUT/pq/kem_${alg}_r$r.txt"
  done
done

# ------------------------------------------------------ classical baselines
for r in $(seq 1 "$REPS"); do
  # shellcheck disable=SC2086
  $PIN $OPENSSL speed -seconds "$DURATION" $CLASSICAL > "$OUT/classical/speed_r$r.txt" 2>&1
done

# ------------------------------------------------------------- certificates
# Wall-clock time per generation in nanoseconds (not /usr/bin/time, whose
# resolution is 10 ms), and the certificate size in PEM and in DER.
echo "alg,run,time_ns,pem_bytes,der_bytes" > "$OUT/certs/certs.csv"
tmp=$(mktemp -d)
for alg in $CERT_ALGS; do
  prov=$PROVIDER_ARGS
  case $alg in rsa:*) prov="" ;; esac
  for r in $(seq 1 "$CERT_RUNS"); do
    t0=$(date +%s%N)
    # shellcheck disable=SC2086
    $PIN $OPENSSL req -x509 -new -newkey "$alg" -nodes -keyout "$tmp/k.pem" -out "$tmp/c.pem" \
        -subj "/CN=pqc-benchmark" -days 365 $prov 2>/dev/null
    t1=$(date +%s%N)
    pem=$(wc -c < "$tmp/c.pem")
    # shellcheck disable=SC2086
    der=$($OPENSSL x509 -in "$tmp/c.pem" -outform DER $prov | wc -c)
    echo "$alg,$r,$((t1 - t0)),$pem,$der" >> "$OUT/certs/certs.csv"
  done
done
rm -rf "$tmp"

# ------------------------------------------- per-signature latency samples
if [ ! -x "$HERE/sig_latency" ]; then
  cc -O2 -Wall -I"$LIBOQS_BUILD/include" "$HERE/sig_latency.c" "$LIBOQS_BUILD/lib/liboqs.a" \
     -lcrypto -lm -o "$HERE/sig_latency"
fi
for alg in $LAT_ALGS; do
  $PIN "$HERE/sig_latency" "$alg" "$LAT_SAMPLES" "$OUT/latency/$alg.ns" | tee -a "$OUT/latency/summary.txt"
done

echo "done: results in $OUT"
echo "next: python3 plot_latency.py $OUT/latency   (measured percentiles against the model)"
