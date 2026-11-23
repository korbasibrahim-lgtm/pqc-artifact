/*
 * sig_latency.c -- per-operation signing-latency distribution for a liboqs
 * signature algorithm.
 *
 * The liboqs speed_sig utility reports only the mean and the population
 * standard deviation of each operation. This harness records every signing
 * time individually so that percentiles and the full distribution can be
 * reported, which is what a latency budget needs for schemes whose signing
 * time is not constant (ML-DSA).
 *
 * Build (static liboqs, OpenSSL back end for SHA-2):
 *   cc -O2 -Wall -I<liboqs>/build/include sig_latency.c \
 *      <liboqs>/build/lib/liboqs.a -lcrypto -lm -o sig_latency
 *
 * Run (pin to one performance core, e.g. core 2):
 *   taskset -c 2 ./sig_latency ML-DSA-44 200000 mldsa44.ns
 *
 * Output: one summary line on stdout; optional raw samples (ns, one per
 * line) in the file given as third argument.
 */
#define _POSIX_C_SOURCE 200809L
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include <oqs/oqs.h>

#define MSG_LEN 50 /* same message length as liboqs speed_sig */

static inline uint64_t now_ns(void) {
	struct timespec ts;
	clock_gettime(CLOCK_MONOTONIC_RAW, &ts);
	return (uint64_t)ts.tv_sec * 1000000000ull + (uint64_t)ts.tv_nsec;
}

static int cmp_u64(const void *a, const void *b) {
	uint64_t x = *(const uint64_t *)a, y = *(const uint64_t *)b;
	return (x > y) - (x < y);
}

static double pct(const uint64_t *sorted, size_t n, double q) {
	/* nearest-rank percentile */
	size_t k = (size_t)ceil(q * (double)n);
	if (k < 1) {
		k = 1;
	}
	if (k > n) {
		k = n;
	}
	return (double)sorted[k - 1] / 1000.0; /* microseconds */
}

int main(int argc, char **argv) {
	if (argc < 3) {
		fprintf(stderr, "usage: %s <alg> <samples> [raw_output_file]\n", argv[0]);
		return EXIT_FAILURE;
	}
	const char *alg = argv[1];
	size_t n = (size_t)strtoull(argv[2], NULL, 10);
	const char *dump = argc > 3 ? argv[3] : NULL;
	if (n < 1000) {
		fprintf(stderr, "need at least 1000 samples\n");
		return EXIT_FAILURE;
	}

	OQS_init();
	OQS_SIG *sig = OQS_SIG_new(alg);
	if (sig == NULL) {
		fprintf(stderr, "algorithm %s not enabled in this liboqs build\n", alg);
		return EXIT_FAILURE;
	}

	uint8_t *pk = malloc(sig->length_public_key);
	uint8_t *sk = malloc(sig->length_secret_key);
	uint8_t *sm = malloc(sig->length_signature);
	uint64_t *t = malloc(n * sizeof(uint64_t));
	uint8_t msg[MSG_LEN];
	size_t smlen = 0;
	if (!pk || !sk || !sm || !t) {
		fprintf(stderr, "allocation failed\n");
		return EXIT_FAILURE;
	}

	OQS_randombytes(msg, MSG_LEN);
	if (OQS_SIG_keypair(sig, pk, sk) != OQS_SUCCESS) {
		fprintf(stderr, "keypair failed\n");
		return EXIT_FAILURE;
	}

	/* warm-up: caches, frequency scaling, lazy initialisation */
	for (size_t i = 0; i < 2000; i++) {
		OQS_SIG_sign(sig, sm, &smlen, msg, MSG_LEN, sk);
	}

	for (size_t i = 0; i < n; i++) {
		uint64_t t0 = now_ns();
		OQS_STATUS rc = OQS_SIG_sign(sig, sm, &smlen, msg, MSG_LEN, sk);
		uint64_t t1 = now_ns();
		if (rc != OQS_SUCCESS) {
			fprintf(stderr, "sign failed at sample %zu\n", i);
			return EXIT_FAILURE;
		}
		t[i] = t1 - t0;
	}

	if (OQS_SIG_verify(sig, msg, MSG_LEN, sm, smlen, pk) != OQS_SUCCESS) {
		fprintf(stderr, "self-check failed: last signature does not verify\n");
		return EXIT_FAILURE;
	}

	if (dump != NULL) {
		FILE *f = fopen(dump, "w");
		if (f == NULL) {
			perror(dump);
			return EXIT_FAILURE;
		}
		for (size_t i = 0; i < n; i++) {
			fprintf(f, "%llu\n", (unsigned long long)t[i]);
		}
		fclose(f);
	}

	double sum = 0.0, sumsq = 0.0;
	for (size_t i = 0; i < n; i++) {
		double us = (double)t[i] / 1000.0;
		sum += us;
		sumsq += us * us;
	}
	double mean = sum / (double)n;
	double sd = sqrt(sumsq / (double)n - mean * mean); /* population s.d. */

	qsort(t, n, sizeof(uint64_t), cmp_u64);
	printf("alg=%s n=%zu mean_us=%.2f sd_us=%.2f cv_pct=%.1f min_us=%.2f "
	       "p50_us=%.2f p90_us=%.2f p95_us=%.2f p99_us=%.2f p99.9_us=%.2f max_us=%.2f\n",
	       alg, n, mean, sd, 100.0 * sd / mean, (double)t[0] / 1000.0,
	       pct(t, n, 0.50), pct(t, n, 0.90), pct(t, n, 0.95), pct(t, n, 0.99),
	       pct(t, n, 0.999), (double)t[n - 1] / 1000.0);

	free(pk);
	free(sk);
	free(sm);
	free(t);
	OQS_SIG_free(sig);
	OQS_destroy();
	return EXIT_SUCCESS;
}
