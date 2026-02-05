import os

def generate_worker():
    """
    Utility script to embed Python logic into the TypeScript Cloudflare Worker.
    This allows keeping Python logic in separate files for testing and linting
    while maintaining a single file for deployment.
    """
    with open('ci_pipeline.py', 'r') as f:
        ci_pipeline = f.read().replace('`', '\\`').replace('${', '\\${')

    with open('ai_data_analyzer.py', 'r') as f:
        ai_analyzer = f.read().replace('`', '\\`').replace('${', '\\${')

    worker_template = """// unified_worker.ts
import { getSandbox } from '@cloudflare/sandbox';

export interface Env {
  Sandbox: any; // Durable Object namespace for Sandbox
}

// Helper to load our Python scripts
const CI_PIPELINE_PY = `REPLACE_CI`;
const AI_DATA_ANALYZER_PY = `REPLACE_AI`;

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
"""
    final_worker = worker_template.replace('REPLACE_CI', ci_pipeline).replace('REPLACE_AI', ai_analyzer)

    with open('unified_worker.ts', 'w') as f:
        f.write(final_worker)
    print("unified_worker.ts generated successfully.")

if __name__ == "__main__":
    generate_worker()
