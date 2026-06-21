# Intended Solve

For coefficient `k`,

```text
h_k = sum_{i+j=k mod n} f_i g_j mod q.
```

Let `E_f` and `E_g` be the erased positions.  If

```text
k not in E_f + E_g mod n,
```

then the coefficient equation for `h_k` has no product of two hidden
coefficients.  Such positions give a modular linear system

```text
A z = b mod q.
```

The system is intentionally underdetermined.  Compute an affine solution
space and use LLL/Babai to find the representative whose coordinates are
small integers in `[-bound, bound]`.

## Usage

Solve the bundled JSON:

```sh
sage solve.py
```

Solve a server challenge:

```sh
sage solve.py --host 127.0.0.1 --port 1337
```

The server mode opens a new TCP connection for each attempt.  Since the
small-vector recovery is probabilistic for these parameters, it retries up to
10 fresh instances automatically.
