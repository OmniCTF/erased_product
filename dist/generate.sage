#!/usr/bin/env sage

import hashlib
import json
import operator
import os


N = 223
Q_BITS = 57
BOUND_BITS = 22
BOUND = 2^BOUND_BITS
HIDDEN_PER_POLY = 64


def xor_stream(key, data):
    stream = hashlib.shake_256(key).digest(len(data))
    return bytes(operator.xor(a, b) for a, b in zip(data, stream))


def small_coeff():
    x = ZZ.random_element(-BOUND, BOUND + 1)
    while x == 0:
        x = ZZ.random_element(-BOUND, BOUND + 1)
    return x


def interval_positions(start, count):
    start = int(start)
    return [(start + i) % int(N) for i in range(int(count))]


def cyclic_product(f, g, q):
    n = int(N)
    out = []
    for k in range(n):
        s = sum(f[i] * g[(k - i) % n] for i in range(n))
        out.append(int(s % q))
    return out


def make_partial(poly, hidden):
    hidden = set(hidden)
    return [None if i in hidden else int(poly[i]) for i in range(int(N))]


def make_instance(flag):
    q = random_prime(2^Q_BITS - 1, lbound=2^(Q_BITS - 1))

    f = [small_coeff() for _ in range(int(N))]
    g = [small_coeff() for _ in range(int(N))]

    f_start = ZZ.random_element(0, N)
    g_start = ZZ.random_element(0, N)
    hidden_f = interval_positions(f_start, HIDDEN_PER_POLY)
    hidden_g = interval_positions(g_start, HIDDEN_PER_POLY)

    h = cyclic_product(f, g, q)

    hidden_values = [f[i] for i in hidden_f] + [g[i] for i in hidden_g]
    material = ",".join(str(int(x)) for x in hidden_values).encode()
    key = hashlib.sha256(material).digest()

    return {
        "n": int(N),
        "q": int(q),
        "bound": int(BOUND),
        "bound_bits": int(BOUND_BITS),
        "hidden_per_poly": int(HIDDEN_PER_POLY),
        "ring": "F_q[x]/(x^n - 1)",
        "f": make_partial(f, hidden_f),
        "g": make_partial(g, hidden_g),
        "h": h,
        "flag_ciphertext": xor_stream(key, flag).hex(),
    }


def main():
    flag = os.environ.get("FLAG", "flag{dummy}")
    print(json.dumps(make_instance(flag.encode()), indent=2))


if __name__ == "__main__":
    main()
