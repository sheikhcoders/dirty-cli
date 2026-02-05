import json
import subprocess
import os

def test_ai_analyzer_agg():
    print("Testing ai_data_analyzer.py with Agg backend...")
    # Create a dummy CSV
    with open("test.csv", "w") as f:
        f.write("a,b\n1,2\n3,4")

    input_data = {
        "code": "import matplotlib.pyplot as plt; plt.plot([1, 2], [1, 2]); plt.savefig('test_plot.png'); results['plot_done'] = True",
        "files": ["test.csv"]
    }

    res = subprocess.run(["python3", "ai_data_analyzer.py"], input=json.dumps(input_data), capture_output=True, text=True)
    try:
        data = json.loads(res.stdout)
        assert data["success"] is True
        assert data["analysis_output"]["plot_done"] is True
        assert "test_plot.png" in data["generated_plots"]
        assert os.path.exists("test_plot.png")
        print("ai_data_analyzer.py Agg backend test passed.")
    except Exception as e:
        print(f"ai_data_analyzer.py test failed: {e}")
        print(f"Stdout: {res.stdout}")
        print(f"Stderr: {res.stderr}")
    finally:
        if os.path.exists("test.csv"): os.remove("test.csv")
        if os.path.exists("analyzer_state.pkl"): os.remove("analyzer_state.pkl")
        if os.path.exists("test_plot.png"): os.remove("test_plot.png")

if __name__ == "__main__":
    test_ai_analyzer_agg()
