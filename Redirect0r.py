import requests
import argparse
import time
import os
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

def load_payloads(payload_file):
    with open(payload_file, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

def rate_limited(max_per_second):
    min_interval = 1.0 / max_per_second
    def decorate(func):
        last_time = [0.0]
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_time[0]
            left_to_wait = min_interval - elapsed
            if left_to_wait > 0:
                time.sleep(left_to_wait)
            ret = func(*args, **kwargs)
            last_time[0] = time.time()
            return ret
        return wrapper
    return decorate

def test_redirect(url_template, payload, session):
    test_url = url_template + payload
    try:
        r = session.get(test_url, allow_redirects=False, timeout=10)
        if 300 <= r.status_code < 400:
            location = r.headers.get('Location', '')
            return True, test_url, location
        return False, test_url, None
    except requests.RequestException as e:
        print(f"[x] Request xətası: {e}")
        return False, test_url, None

def extract_redirect_param_template(full_url):
    parsed = urlparse(full_url)
    qs = parse_qs(parsed.query)
    redirect_param = None
    for key, value in qs.items():
        if any(val.startswith('http') or val.startswith('//') for val in value):
            redirect_param = key
            break
    if redirect_param is None:
        raise ValueError("Redirect URL parametri tapılmadı!")
    new_qs = {k: v for k, v in qs.items()}
    new_qs[redirect_param] = ['']
    new_query = urlencode(new_qs, doseq=True)
    new_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
    return new_url

def print_banner():
    banner = r'''
  _____          _ _               _    ___
 |  __ \        | (_)             | |  / _ \
 | |__) |___  __| |_ _ __ ___  ___| |_| | | |_ __
 |  _  // _ \/ _` | | '__/ _ \/ __| __| | | | '__|
 | | \ \  __/ (_| | | | |  __/ (__| |_| |_| | |
 |_|  \_\___|\__,_|_|_|  \___|\___|\__|\___/|_|


                 Author: Gulmmdoff v1.0
    '''
    print(banner)

def main():
    print_banner()
    parser = argparse.ArgumentParser(
        description="Redirect0r - Open Redirect Scanner",
        formatter_class=argparse.RawTextHelpFormatter
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-u', '--url', help='Tam URL daxil edin, məsələn: http://example.com?redirect=http://site.com')
    group.add_argument('-f', '--file', help='Fayl daxilində URL-lər (Hər sətrdə biri)')
    parser.add_argument('-p', '--payloads', required=True, help='Payload siyahısı olan fayl')
    parser.add_argument('-rl', '--rate_limit', type=int, default=5, help='Saniyədə maksimum request (default 5)')
    args = parser.parse_args()

    payloads = load_payloads(args.payloads)
    urls = []

    if args.url:
        try:
            extracted_url = extract_redirect_param_template(args.url.strip())
            urls = [extracted_url]
        except ValueError as e:
            print(f"[x] Xəta: {e}")
            return

    elif args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    url_template = extract_redirect_param_template(line)
                    urls.append(url_template)
                except ValueError as e:
                    print(f"[x] URL atlındı: {line} -> {e}")

    session = requests.Session()
    limited_test_redirect = rate_limited(args.rate_limit)(test_redirect)

    found_count = 0
    for base_url in urls:
        found_in_this_url = False
        for payload in payloads:
            test_url = base_url + payload
            print(f"[+] Yoxlanılır: {test_url}")
            found, test_url, location = limited_test_redirect(base_url, payload, session)
            if found:
                found_count += 1
                filename = f"redirect_found_{found_count}.txt"
                while os.path.exists(filename):
                    found_count += 1
                    filename = f"redirect_found_{found_count}.txt"
                with open(filename, 'w', encoding='utf-8') as fw:
                    fw.write(f"[URL Template]\n{base_url}\n")
                    fw.write(f"[Full Request URL]\n{test_url}\n")
                    fw.write(f"[Redirect Location]\n{location}\n")
                    fw.write(f"[Payload]\n{payload}\n")
                print(f"[+] Redirect TAPILDI! → {location}")
                print(f"[*] Saxlanıldı: {filename}\n")
                found_in_this_url = True
                break
        if not found_in_this_url:
            print("[-] Redirect tapılmadı.\n")

if __name__ == '__main__':
    main()
