"""Simulate many visitors browsing the site at once and report how fast it answers.

Uses only Python's standard library. Read-only: it never submits the enquiry form.

    python scripts/load_test.py http://127.0.0.1:8001 --users 50 --requests 10
    python scripts/load_test.py https://desiroots.co.uk --users 100 --requests 5

Only run it against our own site (this Mac, or our server after launch).
"""
import argparse
import random
import statistics
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

PAGES = ['/', '/products/', '/products/?page=2', '/products/?q=masala', '/products/?q=rice',
         '/products/?category=spices-masalas', '/products/?brand=heera', '/brands/', '/about/', '/contact/']


def visitor(base, count):
    timings, errors = [], 0
    for _ in range(count):
        url = base.rstrip('/') + random.choice(PAGES)
        start = time.perf_counter()
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'desi-roots-load-test'}),
                                        timeout=30) as response:
                response.read()
                if response.status != 200:
                    errors += 1
        except (urllib.error.URLError, TimeoutError, OSError):
            errors += 1
        timings.append(time.perf_counter() - start)
    return timings, errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('base_url')
    parser.add_argument('--users', type=int, default=50, help='visitors at the same time')
    parser.add_argument('--requests', type=int, default=10, help='pages each visitor opens')
    args = parser.parse_args()

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.users) as pool:
        results = list(pool.map(lambda _: visitor(args.base_url, args.requests), range(args.users)))
    elapsed = time.perf_counter() - started

    timings = sorted(t for result in results for t in result[0])
    errors = sum(result[1] for result in results)
    p95 = timings[int(len(timings) * 0.95) - 1]
    print(f'{args.users} visitors x {args.requests} pages = {len(timings)} page loads in {elapsed:.1f}s')
    print(f'pages per second: {len(timings) / elapsed:.1f}')
    print(f'typical page: {statistics.median(timings) * 1000:.0f} ms, slowest 5%: over {p95 * 1000:.0f} ms, '
          f'slowest: {timings[-1] * 1000:.0f} ms')
    print(f'errors: {errors}')


if __name__ == '__main__':
    main()
