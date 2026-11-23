# Artefact

Scripts that regenerate every derived number and figure of the paper, re-run the
measurement campaign, and record per-signature latency.

For double-blind review, publish this directory through an anonymising service
(for example anonymous.4open.science) and cite that URL in the paper. Do not
link a personal or institutional repository.

| File | Purpose |
|---|---|
| `derive_numbers.py` | Holds the measured tables of the paper and recomputes every ratio quoted in the text, the ML-DSA latency model (Table IV), the TLS server-flight payloads (Fig. 4) and the frame counts (Table IX). |
| `make_figures.py` | Draws Figs. 2, 3 and 4 as vector PDFs from the same tables. |
| `run_campaign.sh` | Re-runs the campaign on one pinned core with repeated windows; records the CPU governor, certificate sizes in PEM and DER, and certificate timing over many runs. |
| `sig_latency.c` | Records every signing time of a liboqs signature algorithm and reports mean, CV and percentiles. |
| `plot_latency.py` | Compares the measured ML-DSA latency distribution with the model and draws the measured histogram over it. |

## Regenerating numbers and figures

```sh
python3 derive_numbers.py                 # prints every derived number
python3 make_figures.py ../figures        # writes fig_size_speed, fig_level_match, fig_handshake
```

Requires Python 3 with NumPy and Matplotlib. After a re-run, update the tables at
the top of `derive_numbers.py`; the text values and the figures follow from them.
Figs. 1 and 5 are TikZ drawings; their sources are in `figures/src`.

## Re-running the measurements

```sh
sudo cpupower frequency-set -g performance      # recommended
LIBOQS_BUILD=/path/to/liboqs/build CORE=2 ./run_campaign.sh
```

Choose `CORE` on a performance core (`lscpu --extended`). Check the algorithm
names at the top of the script against `speed_sig --algs` and
`openssl list -signature-algorithms -provider oqsprovider`.

## Measured latency against the model

```sh
cc -O2 -Wall -I$LIBOQS_BUILD/include sig_latency.c $LIBOQS_BUILD/lib/liboqs.a -lcrypto -lm -o sig_latency
taskset -c 2 ./sig_latency ML-DSA-44 200000 latency/ML-DSA-44.ns
python3 plot_latency.py latency
```

`plot_latency.py` prints measured and model quantiles as LaTeX table rows and
writes `fig_latency.pdf`. It fits the model twice: from the mean and CV, as in
the paper, and from the latency levels themselves. The two agree on a quiet
host; a warning is printed when timing noise inflates the standard deviation.
