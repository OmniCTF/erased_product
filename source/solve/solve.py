from sage.all import *
import argparse
import hashlib
import json
import operator
import socket
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "dist" / "challenge.json"
DEFAULT_PORT = 1337
NETWORK_ATTEMPTS = 10


def xor_stream(key, data):
    stream = hashlib.shake_256(key).digest(len(data))
    return bytes(operator.xor(a, b) for a, b in zip(data, stream))


def center_mod(x, q):
    x = ZZ(x)
    if x > q // 2:
        x -= q
    return ZZ(x)


def safe_indices(n, hidden_f, hidden_g):
    hidden_f = set(hidden_f)
    hidden_g = set(hidden_g)
    safe = []
    for k in range(n):
        if not any(((k - i) % n) in hidden_g for i in hidden_f):
            safe.append(k)
    return safe


def build_linear_system(chal):
    n = int(chal["n"])
    q = ZZ(chal["q"])
    f = chal["f"]
    g = chal["g"]
    h = [ZZ(x) for x in chal["h"]]

    hidden_f = [i for i, x in enumerate(f) if x is None]
    hidden_g = [i for i, x in enumerate(g) if x is None]
    variables = [("f", i) for i in hidden_f] + [("g", i) for i in hidden_g]
    var_index = {v: i for i, v in enumerate(variables)}
    hidden_f_set = set(hidden_f)
    hidden_g_set = set(hidden_g)

    rows = []
    rhs = []
    used = []

    for k in safe_indices(n, hidden_f, hidden_g):
        row = [ZZ(0)] * len(variables)
        known = ZZ(0)
        for i in range(n):
            j = (k - i) % n
            f_hidden = i in hidden_f_set
            g_hidden = j in hidden_g_set
            if f_hidden and g_hidden:
                raise ValueError("unsafe coefficient was selected")
            if f_hidden:
                row[var_index[("f", i)]] += ZZ(g[j])
            elif g_hidden:
                row[var_index[("g", j)]] += ZZ(f[i])
            else:
                known += ZZ(f[i]) * ZZ(g[j])

        rows.append([int(x % q) for x in row])
        rhs.append(int((h[k] - known) % q))
        used.append(k)

    return variables, used, Matrix(GF(q), rows), vector(GF(q), rhs)


def independent_lll_basis(rows, dimension):
    reduced = Matrix(ZZ, rows).LLL()
    basis = []
    for row in reduced.rows():
        if not any(row):
            continue
        candidate = basis + [list(row)]
        if Matrix(ZZ, candidate).rank() > len(basis):
            basis.append(list(row))
        if len(basis) == dimension:
            return basis
    raise ValueError("lattice basis is not full rank")


def babai_closest_vector(basis, target):
    precision = 200
    R = RealField(precision)
    b = [vector(R, row) for row in basis]

    bstar = []
    for i, row in enumerate(b):
        v = vector(R, row)
        for j in range(i):
            denom = bstar[j].dot_product(bstar[j])
            v -= (row.dot_product(bstar[j]) / denom) * bstar[j]
        bstar.append(v)

    y = vector(R, target)
    coeffs = [ZZ(0)] * len(basis)
    for i in reversed(range(len(basis))):
        denom = bstar[i].dot_product(bstar[i])
        c = ZZ(round(y.dot_product(bstar[i]) / denom))
        coeffs[i] = c
        y -= c * b[i]

    closest = vector(ZZ, [0] * len(target))
    for c, row in zip(coeffs, basis):
        closest += c * vector(ZZ, row)
    return closest


def recover_hidden(chal):
    q = ZZ(chal["q"])
    bound = ZZ(chal["bound"])
    variables, used, A, b = build_linear_system(chal)
    m = len(variables)

    rank = A.rank()
    print(f"linear coefficients: {len(used)}", file=sys.stderr)
    print(f"unknowns: {m}", file=sys.stderr)
    print(f"rank: {rank}", file=sys.stderr)
    print(f"kernel dimension: {m - rank}", file=sys.stderr)

    z0 = A.solve_right(b)
    kernel = A.right_kernel().basis()

    lattice_rows = []
    for v in kernel:
        lattice_rows.append([center_mod(x, q) for x in v])
    for i in range(m):
        row = [ZZ(0)] * m
        row[i] = q
        lattice_rows.append(row)

    basis = independent_lll_basis(lattice_rows, m)
    target = vector(ZZ, [-center_mod(x, q) for x in z0])
    close = babai_closest_vector(basis, target)
    z = vector(ZZ, [center_mod(x, q) for x in z0]) + close

    if any(abs(x) > bound for x in z):
        raise ValueError("recovered vector is outside the coefficient bound")

    return variables, [ZZ(x) for x in z]


def cyclic_product(f, g, q):
    n = len(f)
    out = []
    for k in range(n):
        out.append(sum(f[i] * g[(k - i) % n] for i in range(n)) % q)
    return out


def read_challenge_file(path):
    return json.loads(Path(path).read_text())


def read_challenge_socket(host, port, timeout):
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.settimeout(timeout)
        chunks = []
        while True:
            try:
                chunk = sock.recv(65536)
            except socket.timeout:
                break
            if not chunk:
                break
            chunks.append(chunk)

    data = b"".join(chunks).decode()
    start = data.find("{")
    end = data.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"response did not contain JSON: {data!r}")
    return json.loads(data[start : end + 1])


def solve_challenge(chal):
    q = ZZ(chal["q"])
    f = [None if x is None else ZZ(x) for x in chal["f"]]
    g = [None if x is None else ZZ(x) for x in chal["g"]]

    variables, values = recover_hidden(chal)
    for (which, idx), value in zip(variables, values):
        if which == "f":
            f[idx] = value
        else:
            g[idx] = value

    if cyclic_product(f, g, q) != [ZZ(x) for x in chal["h"]]:
        raise ValueError("product check failed")

    hidden_f = [i for i, x in enumerate(chal["f"]) if x is None]
    hidden_g = [i for i, x in enumerate(chal["g"]) if x is None]
    hidden_values = [f[i] for i in hidden_f] + [g[i] for i in hidden_g]
    material = ",".join(str(int(x)) for x in hidden_values).encode()
    key = hashlib.sha256(material).digest()
    ciphertext = bytes.fromhex(chal["flag_ciphertext"])
    return xor_stream(key, ciphertext).decode()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Solve Erased Product from a local JSON file or nc-style TCP server."
    )
    parser.add_argument(
        "challenge",
        nargs="?",
        default=str(DATA),
        help="challenge JSON path for file mode (default: dist/challenge.json)",
    )
    parser.add_argument("--host", help="connect to a challenge server")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=20.0)
    return parser.parse_args()


def main():
    args = parse_args()

    if args.host is None:
        print(solve_challenge(read_challenge_file(args.challenge)))
        return

    last_error = None
    for attempt in range(1, NETWORK_ATTEMPTS + 1):
        print(f"attempt {attempt}/{NETWORK_ATTEMPTS}", file=sys.stderr)
        try:
            flag = solve_challenge(read_challenge_socket(args.host, args.port, args.timeout))
        except Exception as e:
            last_error = e
            print(f"attempt {attempt} failed: {type(e).__name__}: {e}", file=sys.stderr)
            continue

        print(flag)
        return

    raise SystemExit(f"all attempts failed: {last_error}")


if __name__ == "__main__":
    main()
