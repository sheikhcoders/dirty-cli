#!/usr/bin/env python3
import argparse
import urllib.request
import urllib.parse
import os
import sys
import json
import mimetypes
import time

# ANSI Color Codes
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

DEFAULT_MODEL_URL = "https://huggingface.co/HuggingFaceTB/SmolLM2-135M/resolve/main/model.safetensors"
DEFAULT_WORKER_URL = "http://localhost:8787"

def log_info(msg):
    print(f"{Colors.BLUE}[INFO]{Colors.ENDC} {msg}")

def log_success(msg):
    print(f"{Colors.GREEN}[SUCCESS]{Colors.ENDC} {msg}")

def log_error(msg):
    print(f"{Colors.FAIL}[ERROR]{Colors.ENDC} {msg}")

def log_warn(msg):
    print(f"{Colors.WARNING}[WARN]{Colors.ENDC} {msg}")

def download_model(url, target_path):
    log_info(f"Downloading model from {Colors.CYAN}{url}{Colors.ENDC}...")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (DirtyCLI Installer)'})
        with urllib.request.urlopen(req) as response:
            total_size = int(response.info().get('Content-Length', 0))
            block_size = 1024 * 1024
            downloaded = 0
            start_time = time.time()

            with open(target_path, 'wb') as f:
                while True:
                    block = response.read(block_size)
                    if not block:
                        break
                    f.write(block)
                    downloaded += len(block)

                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        elapsed = time.time() - start_time
                        speed = downloaded / (elapsed if elapsed > 0 else 1) / (1024 * 1024)
                        # Simple progress bar
                        bar_len = 20
                        filled_len = int(bar_len * downloaded // total_size)
                        bar = '█' * filled_len + '-' * (bar_len - filled_len)
                        print(f"\r{Colors.CYAN}[{bar}]{Colors.ENDC} {percent:.1f}% ({speed:.2f} MB/s)", end="")

            print(f"\n{Colors.GREEN}Download complete!{Colors.ENDC}")
    except Exception as e:
        log_error(f"Download failed: {e}")
        sys.exit(1)

def ci_command(args):
    params = urllib.parse.urlencode({
        "repo": args.repo,
        "sandboxId": args.sandbox
    })
    url = f"{args.url}/ci?{params}"
    log_info(f"Triggering CI for {Colors.BOLD}{args.repo}{Colors.ENDC}...")

    try:
        with urllib.request.urlopen(url) as response:
            data = json.load(response)
            if data.get('overall_success'):
                log_success("CI Pipeline passed!")
            else:
                log_error("CI Pipeline failed.")
            print(json.dumps(data, indent=2))
    except Exception as e:
        log_error(f"Request failed: {e}")

def analyze_command(args):
    url = f"{args.url}/analyze?sandboxId={args.sandbox}"
    boundary = '----DirtyBoundary' + os.urandom(8).hex()
    body = []

    log_info(f"Preparing files and code for analysis...")

    for f_path in args.files:
        if not os.path.exists(f_path):
            log_warn(f"File {f_path} not found, skipping.")
            continue
        filename = os.path.basename(f_path)
        content_type = mimetypes.guess_type(f_path)[0] or 'application/octet-stream'
        body.append(f'--{boundary}'.encode())
        body.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"'.encode())
        body.append(f'Content-Type: {content_type}'.encode())
        body.append(b'')
        with open(f_path, 'rb') as f:
            body.append(f.read())
        body.append(b'')

    body.append(f'--{boundary}'.encode())
    body.append(f'Content-Disposition: form-data; name="code"'.encode())
    body.append(b'')
    body.append(args.code.encode())
    body.append(b'')
    body.append(f'--{boundary}--'.encode())
    body.append(b'')

    full_body = b'\r\n'.join(body)

    req = urllib.request.Request(url, data=full_body)
    req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')

    log_info(f"Running analysis in sandbox {Colors.BOLD}{args.sandbox}{Colors.ENDC}...")
    try:
        with urllib.request.urlopen(req) as response:
            result = json.load(response)
            if result.get('success'):
                log_success("Analysis complete.")
                if result.get('analysis_output'):
                    print(f"{Colors.BOLD}Results:{Colors.ENDC}")
                    print(json.dumps(result['analysis_output'], indent=2))
                if result.get('generated_plots'):
                    print(f"{Colors.BOLD}Generated Plots:{Colors.ENDC} {', '.join(result['generated_plots'])}")
            else:
                log_error(f"Analysis failed: {result.get('message')}")
                if 'stdout' in result:
                    print(result['stdout'])
    except Exception as e:
        log_error(f"Request failed: {e}")

def setup_command(args):
    target = args.target or "model.safetensors"
    download_model(args.model_url, target)
    log_success(f"Setup finished. Model saved to {Colors.BOLD}{target}{Colors.ENDC}")

def bootstrap_command(args):
    log_info(f"Bootstrapping sandbox {Colors.BOLD}{args.sandbox}{Colors.ENDC}...")
    # This command could pre-install common libraries in the sandbox
    # For now, we'll just test the connection
    url = f"{args.url}/analyze?sandboxId={args.sandbox}"

    boundary = '----DirtyBoundary' + os.urandom(8).hex()
    body = [
        f'--{boundary}'.encode(),
        b'Content-Disposition: form-data; name="code"',
        b'',
        b'import pandas as pd; import matplotlib.pyplot as plt; print("Environment Ready")',
        b'',
        f'--{boundary}--'.encode(),
        b''
    ]
    full_body = b'\r\n'.join(body)
    req = urllib.request.Request(url, data=full_body)
    req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')

    try:
        with urllib.request.urlopen(req) as response:
            res = json.load(response)
            if res.get('success'):
                log_success(f"Sandbox {args.sandbox} is ready.")
                print(res.get('stdout'))
            else:
                log_error("Bootstrap failed.")
    except Exception as e:
        log_error(f"Bootstrap failed: {e}")

def main():
    parser = argparse.ArgumentParser(
        description=f"{Colors.BOLD}{Colors.BLUE}Dirty CLI{Colors.ENDC} - Highly powerful Edge Services Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
{Colors.BOLD}Examples:{Colors.ENDC}
  dirty setup --target smol.safetensors
  dirty ci https://github.com/user/repo.git
  dirty analyze data.csv --code "print(df.describe())"
  dirty b --sandbox my-box
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # CI Command
    ci_parser = subparsers.add_parser("ci", aliases=["c"], help="Run CI/CD pipeline")
    ci_parser.add_argument("repo", help="Git repository URL")
    ci_parser.add_argument("--sandbox", default="default-sandbox", help="Sandbox ID")
    ci_parser.add_argument("--url", default=DEFAULT_WORKER_URL, help="Worker URL")

    # Analyze Command
    analyze_parser = subparsers.add_parser("analyze", aliases=["a"], help="Run AI Data Analysis")
    analyze_parser.add_argument("files", nargs="+", help="CSV files to upload")
    analyze_parser.add_argument("--code", required=True, help="Python code to execute")
    analyze_parser.add_argument("--sandbox", default="default-sandbox", help="Sandbox ID")
    analyze_parser.add_argument("--url", default=DEFAULT_WORKER_URL, help="Worker URL")

    # Setup Command
    setup_parser = subparsers.add_parser("setup", aliases=["s"], help="Download and setup SmolLM2 model")
    setup_parser.add_argument("--model-url", default=DEFAULT_MODEL_URL, help="Model URL")
    setup_parser.add_argument("--target", help="Target filename")

    # Bootstrap Command
    boot_parser = subparsers.add_parser("bootstrap", aliases=["b"], help="Prepare sandbox environment")
    boot_parser.add_argument("--sandbox", default="default-sandbox", help="Sandbox ID")
    boot_parser.add_argument("--url", default=DEFAULT_WORKER_URL, help="Worker URL")

    args = parser.parse_args()

    # Handle aliases manually if needed, but argparse subparsers with aliases do it for us
    # Note: aliases work in Python 3.2+

    if args.command in ["ci", "c"]:
        ci_command(args)
    elif args.command in ["analyze", "a"]:
        analyze_command(args)
    elif args.command in ["setup", "s"]:
        setup_command(args)
    elif args.command in ["bootstrap", "b"]:
        bootstrap_command(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
