#!/usr/bin/env python3
"""Recompute every derived number quoted in the paper from the measured tables.

Inputs are the measured values of Tables III, V, VI, VII and VIII only. Nothing
here is a new measurement: the script reproduces the ratios in the text, the
latency model of Section V-B and the transport and link budgets of
Section VII, so that each can be checked or regenerated after a re-run.

Usage: python3 derive_numbers.py
"""
import math

# ---------------------------------------------------------------- measured
# Table III: pk, sk, sig (bytes); keygen, sign, verify (us); sign CV (%)
SIG = {
    "ML-DSA-44":    (1312, 2560, 2420, 21.2, 62.5, 21.1, 60.9),
    "ML-DSA-65":    (1952, 4032, 3309, 36.5, 100.3, 35.0, 60.7),
    "ML-DSA-87":    (2592, 4896, 4627, 64.2, 134.5, 62.1, 48.8),
    "Falcon-512":   (897, 1281, 752, 5011.0, 166.0, 29.7, 1.6),
    "Falcon-1024":  (1793, 2305, 1462, 14565.6, 331.5, 57.9, 0.9),
    "SLH-DSA-128f": (32, 64, 17088, 827.6, 18957.2, 1140.3, 2.8),
    "SLH-DSA-192f": (48, 96, 35664, 1221.7, 31993.6, 1652.4, 1.8),
    "SLH-DSA-256f": (64, 128, 49856, 3245.7, 66035.3, 1787.7, 1.2),
}
# Table V: keygen, encaps, decaps (us); pk, ct (bytes)
KEM = {
    "ML-KEM-512":  (6.7, 7.4, 8.6, 800, 768),
    "ML-KEM-768":  (10.6, 11.0, 13.3, 1184, 1088),
    "ML-KEM-1024": (14.4, 15.7, 18.9, 1568, 1568),
}
# Table VI: sign, verify (us); signature (bytes)
CLS = {
    "RSA-2048":    (480.6, 14.3, 256),
    "RSA-3072":    (1472.0, 30.7, 384),
    "RSA-4096":    (3367.0, 53.6, 512),
    "ECDSA P-256": (18.3, 57.4, 64),
    "ECDSA P-384": (540.4, 466.6, 96),
}
# Table VII: one ECDH derivation (us); public value (bytes)
ECDH = {"X25519": (26.9, 32), "ECDH P-256": (44.4, 64), "ECDH P-384": (511.8, 96)}
# Table VIII: PEM certificate size (bytes)
CERT = {"RSA-2048": 977, "RSA-4096": 1671, "Falcon-512": 2346, "Falcon-1024": 4393,
        "ML-DSA-44": 5311, "ML-DSA-65": 7383, "ML-DSA-87": 10032, "SLH-DSA-128f": 23434}
# FIPS 204, Table 1: expected number of repetitions of the signing loop
REPS = {"ML-DSA-44": 4.25, "ML-DSA-65": 5.1, "ML-DSA-87": 3.85}

# signature configuration, |pk_sig|, |sig|, key-share bytes sent by the server
FLIGHTS = [
    ("ECDSA P-256 + X25519",      64, 64, 32),
    ("RSA-2048 + X25519",         256, 256, 32),
    ("Falcon-512 + ML-KEM-512",   897, 752, 768),
    ("Falcon-1024 + ML-KEM-1024", 1793, 1462, 1568),
    ("ML-DSA-44 + ML-KEM-512",    1312, 2420, 768),
    ("ML-DSA-65 + ML-KEM-768",    1952, 3309, 1088),
    ("ML-DSA-87 + ML-KEM-1024",   2592, 4627, 1568),
    ("SLH-DSA-128f + ML-KEM-512", 32, 17088, 768),
]


def hdr(t):
    print("\n" + t + "\n" + "-" * len(t))


def main():
    # ------------------------------------------------------- ratios in the text
    hdr("Signature ratios (Sections V-A and VI-A)")
    s = lambda a: SIG[a][4]
    v = lambda a: SIG[a][5]
    print(f"SLH-128f / ML-DSA-44 sign      : {s('SLH-DSA-128f')/s('ML-DSA-44'):.0f}x")
    print(f"SLH-256f / ML-DSA-87 sign      : {s('SLH-DSA-256f')/s('ML-DSA-87'):.0f}x")
    print(f"Falcon-512 / ML-DSA-44 keygen  : {SIG['Falcon-512'][3]/SIG['ML-DSA-44'][3]:.0f}x")
    print(f"RSA-2048 / ML-DSA-44 sign      : {CLS['RSA-2048'][0]/s('ML-DSA-44'):.1f}x")
    print(f"RSA-3072 / ML-DSA-44 sign      : {CLS['RSA-3072'][0]/s('ML-DSA-44'):.1f}x")
    print(f"RSA-2048 / Falcon-512 sign     : {CLS['RSA-2048'][0]/s('Falcon-512'):.1f}x")
    print(f"RSA-3072 / Falcon-512 sign     : {CLS['RSA-3072'][0]/s('Falcon-512'):.1f}x")
    print(f"RSA-4096 / ML-DSA-87 sign      : {CLS['RSA-4096'][0]/s('ML-DSA-87'):.1f}x")
    print(f"ML-DSA-44 / P-256 sign         : {s('ML-DSA-44')/CLS['ECDSA P-256'][0]:.1f}x")
    print(f"P-256 / ML-DSA-44 verify       : {CLS['ECDSA P-256'][1]/v('ML-DSA-44'):.1f}x")
    print(f"P-384 / ML-DSA-65 sign, verify : {CLS['ECDSA P-384'][0]/s('ML-DSA-65'):.1f}x, {CLS['ECDSA P-384'][1]/v('ML-DSA-65'):.1f}x")
    print(f"Tier-1 lattice sig / P-256 sig : {SIG['Falcon-512'][2]/64:.1f}x .. {SIG['ML-DSA-44'][2]/64:.1f}x")

    hdr("ML-KEM (Sections V-C and VI-B)")
    for k, (kg, en, de, pk, ct) in KEM.items():
        print(f"{k:12s} exchange {kg+en+de:5.1f} us   decaps/encaps {de/en:.3f}")
    ks = list(KEM.values())
    for i in (0, 1):
        print(f"step {i}: time x{ks[i+1][0]/ks[i][0]:.2f} {ks[i+1][1]/ks[i][1]:.2f} {ks[i+1][2]/ks[i][2]:.2f}"
              f"   size x{ks[i+1][3]/ks[i][3]:.2f} {ks[i+1][4]/ks[i][4]:.2f}")
    x2 = 2 * ECDH["X25519"][0]
    print(f"X25519 one op / ML-KEM-512 encaps : {ECDH['X25519'][0]/KEM['ML-KEM-512'][1]:.1f}x")
    print(f"P-256  one op / ML-KEM-512 encaps : {ECDH['ECDH P-256'][0]/KEM['ML-KEM-512'][1]:.1f}x")
    print(f"X25519 exchange >= {x2:.1f} us ; / ML-KEM-768 exchange = {x2/sum(KEM['ML-KEM-768'][:3]):.2f}x")
    print(f"P-384 exchange >= {2*ECDH['ECDH P-384'][0]:.1f} us ; / ML-KEM-768 exchange = {2*ECDH['ECDH P-384'][0]/sum(KEM['ML-KEM-768'][:3]):.1f}x")
    print(f"hybrid X25519MLKEM768 >= {x2 + sum(KEM['ML-KEM-768'][:3]):.1f} us ; client share {KEM['ML-KEM-768'][3]+32} B, server share {KEM['ML-KEM-768'][4]+32} B")

    hdr("Certificates (Section VII-A)")
    for k, sz in CERT.items():
        print(f"{k:13s} {sz:6d} B  {sz/CERT['RSA-2048']:.1f}x RSA-2048")
    print(f"Falcon-512 / RSA-4096 certificate: {CERT['Falcon-512']/CERT['RSA-4096']:.1f}x")

    # ------------------------------------------------- latency model (Sec. V-B)
    hdr("ML-DSA signing-latency model: T = a + b*K, K ~ Geometric(1/r)")
    MODEL = {}
    for alg, r in REPS.items():
        mean, cv = SIG[alg][4], SIG[alg][6] / 100.0
        b = cv * mean / math.sqrt(r * (r - 1.0))     # sd(T) = b * sqrt(r(r-1))
        a = mean - b * r                             # E[T]  = a + b r
        p = 1.0 / r
        q = {}
        for name, qq in (("p95", 0.95), ("p99", 0.99), ("p99.9", 0.999)):
            k = math.ceil(math.log(1.0 - qq) / math.log(1.0 - p))
            q[name] = (k, a + b * k)
        MODEL[alg] = (a, b, p, q)
        kg, vf = SIG[alg][3], SIG[alg][5]
        print(f"{alg}: r={r}  a={a:.1f} us  b={b:.1f} us   a/verify={a/vf:.3f}  a/keygen={a/kg:.3f}")
        for name, (k, t) in q.items():
            print(f"     {name:6s} K={k:2d}  T={t:6.1f} us  = {t/mean:.2f} x mean")
    for pq, fal in (("ML-DSA-44", "Falcon-512"), ("ML-DSA-87", "Falcon-1024")):
        a, b, p, _ = MODEL[pq]
        kmin = math.floor((SIG[fal][4] - a) / b) + 1     # smallest K with T > Falcon mean
        print(f"P(T[{pq}] > mean T[{fal}] = {SIG[fal][4]} us) = P(K >= {kmin}) = {(1-p)**(kmin-1)*100:.1f}%")

    # ------------------------------------------ handshake payload (Sec. VII-B)
    hdr("TLS 1.3 server flight, B = 2|pk| + 3|sig| + |ct|  (two-certificate chain)")
    MSS, IW = 1460, 10 * 1460
    for name, pk, sg, ct in FLIGHTS:
        auth, B = 2 * pk + 3 * sg, 2 * pk + 3 * sg + ct
        print(f"{name:27s} auth {auth:6d}  total {B:6d} B = {B/1000:5.2f} kB   segments {math.ceil(B/MSS):2d}"
              f"   IW10 {'fits' if B <= IW else f'x{B/IW:.2f}'}   QUIC 3x1200 {'fits' if B <= 3600 else 'exceeds'}"
              f"   3x2400 {'fits' if B <= 7200 else 'exceeds'}")
    print(f"initial window = {IW} B ; QUIC budget = 3600 B (one 1200-B Initial), 7200 B (two)")

    # ---------------------------------------------- link budgets (Sec. VII-C)
    hdr("Frames needed per object: ceil(S / L)")
    LINKS = [("LoRaWAN DR0", 51), ("LoRaWAN DR5", 242), ("802.15.4", 102), ("IPv6 min-MTU/UDP", 1232), ("Ethernet MSS", 1460)]
    OBJ = [("ECDSA P-256 signature", 64), ("X25519 public value", 32),
           ("ML-KEM-512 ciphertext", 768), ("ML-KEM-768 ciphertext", 1088), ("ML-KEM-1024 ciphertext", 1568),
           ("ML-KEM-512 public key", 800), ("ML-KEM-768 public key", 1184),
           ("Falcon-512 signature", 752), ("Falcon-1024 signature", 1462),
           ("ML-DSA-44 signature", 2420), ("ML-DSA-65 signature", 3309), ("ML-DSA-87 signature", 4627),
           ("SLH-DSA-128f signature", 17088),
           ("Falcon-512 public key", 897), ("ML-DSA-44 public key", 1312)]
    print(f"{'object':26s} {'bytes':>6s} " + " ".join(f"{n:>17s}" for n, _ in LINKS) + "   airtime@250bit/s  @250kbit/s")
    for name, S in OBJ:
        print(f"{name:26s} {S:6d} " + " ".join(f"{math.ceil(S/L):17d}" for _, L in LINKS)
              + f"   {8*S/250:9.1f} s   {8*S/250e3*1e3:8.1f} ms")
    for name, S in (("ML-KEM-512 ciphertext", 768), ("ML-DSA-44 signature", 2420), ("SLH-DSA-128f signature", 17088)):
        air = 8 * S / 250
        print(f"{name}: airtime >= {air:.1f} s at 250 bit/s; elapsed >= {air/0.01/60:.0f} min under a 1% duty cycle")
    print("objects that fit one 1232-byte UDP payload:", [n for n, S in OBJ if S <= 1232])


if __name__ == "__main__":
    main()
