import subprocess
import os
import json
import sys
import shlex

def run_command(command, cwd=None):
    try:
        if isinstance(command, str):
            command = shlex.split(command)
        result = subprocess.run(command, capture_output=True, text=True, cwd=cwd)
        return {
            "success": result.returncode == 0,
            "output": result.stdout + result.stderr
        }
    except Exception as e:
        return {
            "success": False,
            "output": str(e)
        }

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No repository URL provided"}))
        sys.exit(1)

    repo_url = sys.argv[1]
    # Use a unique directory if possible, but for simplicity in this script:
    repo_name = repo_url.split('/')[-1].replace('.git', '')
    target_dir = f"/tmp/{repo_name}"

    # Cleanup if exists
    if os.path.exists(target_dir):
        import shutil
        shutil.rmtree(target_dir)

    # 1. Git Clone
    clone_res = run_command(["git", "clone", repo_url, target_dir])
    if not clone_res["success"]:
        print(json.dumps({
            "repo_url": repo_url,
            "clone": clone_res,
            "overall_success": False
        }))
        sys.exit(0)

    # 2. Dependency Detection & Installation
    install_res = {"success": False, "output": "No supported project detected"}
    run_tests_res = {"success": False, "output": "Tests not run"}

    if os.path.exists(os.path.join(target_dir, "package.json")):
        # Node.js
        install_res = run_command("npm install", cwd=target_dir)
        if install_res["success"]:
            # Check for test script
            package_json_path = os.path.join(target_dir, "package.json")
            with open(package_json_path, 'r') as f:
                package_data = json.load(f)
                if 'scripts' in package_data and 'test' in package_data['scripts']:
                    run_tests_res = run_command("npm test", cwd=target_dir)
                else:
                    run_tests_res = {"success": True, "output": "No test script found in package.json"}
    elif os.path.exists(os.path.join(target_dir, "requirements.txt")) or any(f.endswith('.py') for f in os.listdir(target_dir)):
        # Python
        if os.path.exists(os.path.join(target_dir, "requirements.txt")):
            install_res = run_command("pip install -r requirements.txt", cwd=target_dir)
        else:
            install_res = {"success": True, "output": "No requirements.txt found, skipping installation"}

        if install_res["success"]:
            # Try running pytest, fallback to unittest
            pytest_check = run_command("pytest --version")
            if pytest_check["success"]:
                run_tests_res = run_command("pytest", cwd=target_dir)
            else:
                run_tests_res = run_command("python3 -m unittest discover", cwd=target_dir)

    overall_success = clone_res["success"] and install_res["success"] and run_tests_res["success"]

    print(json.dumps({
        "repo_url": repo_url,
        "clone": clone_res,
        "install_deps": install_res,
        "run_tests": run_tests_res,
        "overall_success": overall_success
    }))

if __name__ == "__main__":
    main()
