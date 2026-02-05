import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for headless environment
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
