// unified_worker.ts
import { getSandbox } from '@cloudflare/sandbox';

export interface Env {
  Sandbox: any; // Durable Object namespace for Sandbox
}

// Helper to load our Python scripts
const CI_PIPELINE_PY = `import subprocess
import os
import json
import sys

def run_command(command, cwd=None):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=cwd)
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
        subprocess.run(f"rm -rf {target_dir}", shell=True)

    # 1. Git Clone
    clone_res = run_command(f"git clone {repo_url} {target_dir}")
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
`;
const AI_DATA_ANALYZER_PY = `import pandas as pd
import matplotlib.pyplot as plt
import os
import sys
import json
import pickle
import traceback
import io
import ast

STATE_FILE = "analyzer_state.pkl"

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'rb') as f:
                return pickle.load(f)
        except:
            pass
    return {"dfs": {}, "results": {}}

def save_state(state):
    with open(STATE_FILE, 'wb') as f:
        pickle.dump(state, f)

def execute_with_last_expr(code, global_vars, local_vars):
    """Executes a block of code and returns the result of the last expression."""
    tree = ast.parse(code)
    if not tree.body:
        return None

    last_node = tree.body[-1]
    if isinstance(last_node, ast.Expr):
        # Execute everything except the last expression
        if len(tree.body) > 1:
            exec_code = compile(ast.Module(body=tree.body[:-1], type_ignores=[]), "<string>", "exec")
            exec(exec_code, global_vars, local_vars)

        # Evaluate the last expression
        eval_code = compile(ast.Expression(body=last_node.value), "<string>", "eval")
        return eval(eval_code, global_vars, local_vars)
    else:
        # Execute the whole block
        exec_code = compile(tree, "<string>", "exec")
        exec(exec_code, global_vars, local_vars)
        return None

def main():
    try:
        if not sys.stdin.isatty():
            input_data = json.load(sys.stdin)
        else:
            input_data = {}
    except Exception as e:
        input_data = {}

    code = input_data.get("code", "")
    files = input_data.get("files", [])

    state = load_state()

    # Load new files into state['dfs']
    for file in files:
        if (file.endswith('.csv')) and os.path.exists(file):
            try:
                df_name = os.path.splitext(os.path.basename(file))[0]
                state['dfs'][df_name] = pd.read_csv(file)
            except Exception as e:
                print(f"Error loading {file}: {e}", file=sys.stderr)

    # Context for execution
    exec_locals = {
        "plt": plt,
        "pd": pd,
        "results": state['results']
    }
    for name, df in state['dfs'].items():
        exec_locals[name] = df

    if len(state['dfs']) == 1 and 'df' not in exec_locals:
        exec_locals['df'] = list(state['dfs'].values())[0]

    captured_output = io.StringIO()
    original_stdout = sys.stdout
    sys.stdout = captured_output

    success = True
    message = "Analysis completed successfully."
    last_expr_result = None

    try:
        if code:
            last_expr_result = execute_with_last_expr(code, {}, exec_locals)
    except Exception as e:
        success = False
        message = str(e)
        traceback.print_exc()

    sys.stdout = original_stdout

    # Update state
    for name in list(state['dfs'].keys()) + (['df'] if 'df' in exec_locals else []):
        if name in exec_locals and isinstance(exec_locals[name], pd.DataFrame):
            if name == 'df' and len(state['dfs']) == 1:
                real_name = list(state['dfs'].keys())[0]
                state['dfs'][real_name] = exec_locals[name]
            elif name in state['dfs']:
                state['dfs'][name] = exec_locals[name]

    state['results'] = exec_locals.get('results', {})
    if last_expr_result is not None:
        # If it's a simple type, put it in results if not already there or just return it
        if isinstance(last_expr_result, (dict, list, int, float, str, bool)):
            state['results']['last_expression'] = last_expr_result
        else:
            state['results']['last_expression'] = str(last_expr_result)

    save_state(state)

    generated_plots = [f for f in os.listdir('.') if f.endswith('.png') or f.endswith('.svg')]

    print(json.dumps({
        "success": success,
        "message": message,
        "analysis_output": state['results'],
        "generated_plots": generated_plots,
        "stdout": captured_output.getvalue()
    }))

if __name__ == "__main__":
    main()
`;

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const sandboxId = url.searchParams.get('sandboxId');

    if (!sandboxId) {
      return new Response(JSON.stringify({ error: "Missing sandboxId" }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const sandbox = await getSandbox(env.Sandbox, sandboxId);

    // Ensure scripts are in the sandbox
    await sandbox.writeFile('ci_pipeline.py', CI_PIPELINE_PY);
    await sandbox.writeFile('ai_data_analyzer.py', AI_DATA_ANALYZER_PY);

    if (url.pathname === '/ci') {
      const repo = url.searchParams.get('repo');
      if (!repo) {
        return new Response(JSON.stringify({ error: "Missing repo parameter" }), {
          status: 400,
          headers: { 'Content-Type': 'application/json' }
        });
      }

      const result = await sandbox.exec(`python3 ci_pipeline.py "${repo}"`);
      return new Response(result.stdout, {
        headers: { 'Content-Type': 'application/json' }
      });
    }

    if (url.pathname === '/analyze' && request.method === 'POST') {
      const formData = await request.formData();
      const code = (formData.get('code') as string) || "";
      const files = formData.getAll('file') as any[];

      const filenames = [];
      for (const file of files) {
        if (file instanceof File) {
          const content = await file.arrayBuffer();
          await sandbox.writeFile(file.name, new Uint8Array(content));
          filenames.push(file.name);
        }
      }

      const input = JSON.stringify({ code, files: filenames });
      const result = await sandbox.exec('python3 ai_data_analyzer.py', {
        stdin: input
      });

      try {
        const analysisResult = JSON.parse(result.stdout);
        return new Response(JSON.stringify(analysisResult), {
          headers: { 'Content-Type': 'application/json' }
        });
      } catch (e) {
        return new Response(JSON.stringify({
          success: false,
          message: "Failed to parse analysis result",
          output: result.stdout,
          stderr: result.stderr
        }), {
          headers: { 'Content-Type': 'application/json' }
        });
      }
    }

    return new Response(JSON.stringify({ error: "Not Found" }), {
      status: 404,
      headers: { 'Content-Type': 'application/json' }
    });
  },
};
