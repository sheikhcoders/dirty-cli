# Dirty CLI & Edge Services

Leverages the Cloudflare Sandbox SDK to provide two powerful, production-ready services running in isolated, edge-based Linux environments:

1. **Automated Testing Pipeline (CI/CD):** Automates the entire workflow of cloning Git repositories, installing dependencies, and running tests.
2. **AI Data Analysis Engine:** Processes CSV files, executes AI-generated analysis code, and generates visualizations.

Both services are designed for security, scalability, and ease of integration.

## Architecture

### System Components

The system is composed of three primary layers:

**Layer 1: Python Execution Engines**
- `ci_pipeline.py`: Handles Git cloning, dependency detection, and test execution.
- `ai_data_analyzer.py`: Processes CSV files and executes custom analysis code with matplotlib support.

**Layer 2: Cloudflare Worker Bridge**
- `unified_worker.ts`: TypeScript interface that manages sandbox lifecycle and routes requests to the appropriate engine.

**Layer 3: Sandbox SDK**
- Provides isolated Linux environments with full filesystem and process management capabilities.

### Security Model

Each request is assigned a unique `sandboxId` to ensure strict multi-tenant isolation. The sandbox environment:
- Runs in a dedicated container with restricted filesystem access.
- Prevents network access to unauthorized destinations.
- Enforces resource limits (CPU, memory) to prevent denial-of-service attacks.
- Automatically cleans up resources after execution.

## CI/CD Pipeline

### Features

The CI/CD pipeline automates the following workflow:

1. **Git Clone:** Clones the target repository into a unique temporary directory.
2. **Dependency Detection:** Automatically detects project type (Node.js or Python).
3. **Dependency Installation:** Runs `npm install` or `pip install -r requirements.txt`.
4. **Test Execution:** Runs `npm test` or `pytest` based on project configuration.
5. **Result Reporting:** Returns structured JSON with detailed logs for each step.

### Usage

```typescript
// Endpoint: /ci?repo=<repository_url>&sandboxId=<unique_id>
const response = await fetch('/ci?repo=https://github.com/owner/repo.git&sandboxId=user-123');
const result = await response.json();
// Returns: { repo_url, clone, install_deps, run_tests, overall_success }
```

### Response Structure

```json
{
  "repo_url": "https://github.com/owner/repo.git",
  "clone": { "success": true, "output": "..." },
  "install_deps": { "success": true, "output": "..." },
  "run_tests": { "success": true, "output": "..." },
  "overall_success": true
}
```

## AI Data Analysis Engine

### Features

The data analysis engine provides:

1. **CSV Processing:** Accepts multi-file uploads and parses them with pandas.
2. **Stateful Execution:** Maintains dataframe state across multiple operations.
3. **Custom Analysis:** Executes user-provided Python code with automatic context setup.
4. **Visualization:** Generates plots using matplotlib and returns them as PNG/SVG.
5. **Automatic Capture:** Returns the result of the last expression for interactive analysis.

### Usage

```typescript
// Endpoint: POST /analyze
const formData = new FormData();
formData.append('file', csvFile);
formData.append('code', `
results['analysis_output'] = df.describe().to_dict()
plt.bar(df['col1'], df['col2'])
plt.savefig('chart.png')
`);

const response = await fetch('/analyze', { method: 'POST', body: formData });
const result = await response.json();
// Returns: { success, message, analysis_output, generated_plots }
```

### Response Structure

```json
{
  "success": true,
  "message": "Analysis completed successfully.",
  "analysis_output": { "total_sales": 450, "avg_profit": 31.25 },
  "generated_plots": ["chart.png"]
}
```

## Implementation Details

### Sandbox SDK Methods Used

| Method | Purpose |
| :--- | :--- |
| `getSandbox(env.Sandbox, sandboxId)` | Retrieve or create a sandbox instance. |
| `exec(command)` | Execute shell commands (e.g., git, npm, pytest). |
| `writeFile(path, content)` | Upload files to the sandbox. |
| `readFile(path)` | Retrieve generated files from the sandbox. |
| `mkdir(path, { recursive: true })` | Create directory structures. |

### Error Handling

Both engines implement comprehensive error handling:
- **Clone Failures:** Detected and reported with stderr output.
- **Dependency Installation Errors:** Captured and returned for debugging.
- **Test Failures:** Logs are preserved and returned to the user.
- **Analysis Errors:** Traceback information is included in the response.

## Dirty CLI

The `dirty.py` CLI provides a powerful interface to the edge services and includes a model installer. It is designed to be lightweight and compatible with Termux.

### Features
- **Zero Dependencies:** Uses only Python standard libraries.
- **Fast Model Setup:** Download models directly to your environment.
- **Concise Commands:** Use aliases like `s` for setup, `c` for CI, and `a` for analyze.
- **Colorized Output:** Clear and readable logs.

### Usage

```bash
# Setup: Download the SmolLM2 model
./dirty.py setup

# CI/CD: Run a pipeline for a repo
./dirty.py ci https://github.com/owner/repo.git

# Analysis: Run data analysis on a CSV
./dirty.py analyze data.csv --code "print(df.head())"

# Viewing graphical output (Termux/Linux/macOS)
./dirty.py view chart.png

# Bootstrap: Check if sandbox is ready
./dirty.py bootstrap
```

## Termux & Graphical Support (X11/VNC)

Dirty CLI is optimized for Termux. While the edge environment is headless, you can view generated visualizations locally:

### 1. Enable X11 Repository
To access X11 packages in Termux, run:
```bash
pkg install x11-repo
```

### 2. View Output
Use the `view` (or `v`) command to automatically fetch a file from the sandbox and open it with your local system's default viewer:
```bash
./dirty.py view my_plot.png
```
*In Termux, this leverages `termux-open` to pass the file to an external image viewer.*

### 3. VNC Setup (Optional)
For a full desktop experience in Termux:
1. Install a VNC server: `pkg install tigervnc`
2. Start the server: `vncserver`
3. Connect using a VNC client application (e.g., VNC Viewer) to `localhost:1`.

## Quick Setup

Run the automated installer to set up the CLI and prepare the worker bridge:

```bash
chmod +x installer.sh
./installer.sh
```

The installer will:
1. Verify Python and npm dependencies.
2. Set correct permissions for the CLI.
3. Synchronize the Python logic with the Cloudflare Worker.
4. Optionally download the SmolLM2 model.

## Deployment

### Prerequisites

- Cloudflare Workers account with Durable Objects enabled.
- Node.js 16+ for building the TypeScript worker.

### Deployment Steps

1. Install dependencies: `npm install @cloudflare/sandbox`
2. Build the worker: `npm run build`
3. Deploy to Cloudflare: `wrangler publish`

Note: If you modify the Python scripts (`ci_pipeline.py` or `ai_data_analyzer.py`), run `python3 generate_worker.py` to update the embedded code in `unified_worker.ts` before deploying.

### Configuration

Update `wrangler.toml` to include:

```toml
[env.production]
durable_objects.bindings = [
  { name = "Sandbox", class_name = "Sandbox" }
]
```
