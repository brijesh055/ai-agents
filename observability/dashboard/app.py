"""Optional local web dashboard (stdlib http.server)."""

import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from observability.metrics import MetricsCollector
from observability.logger import AgentLogger
from observability.trace_viewer import TraceViewer
from core.cost_tracker import CostTracker

DASHBOARD_HTML = """<!DOCTYPE html>
<html>
<head>
<title>AI Agents Dashboard</title>
<meta charset="utf-8">
<meta http-equiv="refresh" content="10">
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; max-width: 1200px; margin: 0 auto; padding: 24px; background: #0f172a; color: #e2e8f0; }
h1 { color: #38bdf8; font-size: 28px; margin-bottom: 8px; }
h2 { color: #94a3b8; font-size: 16px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px; }
.card { background: #1e293b; border-radius: 10px; padding: 20px; margin: 16px 0; border: 1px solid #334155; }
.metric-row { display: flex; flex-wrap: wrap; gap: 12px; }
.metric { background: #334155; border-radius: 8px; padding: 14px 18px; min-width: 130px; }
.metric .value { font-size: 26px; font-weight: 700; color: #38bdf8; }
.metric .label { font-size: 11px; color: #94a3b8; margin-top: 2px; text-transform: uppercase; letter-spacing: 0.5px; }
.agent-list { display: flex; flex-wrap: wrap; gap: 8px; }
.agent-tag { background: #334155; padding: 6px 14px; border-radius: 20px; font-size: 14px; color: #38bdf8; border: 1px solid #475569; }
pre { background: #0f172a; padding: 12px; border-radius: 6px; overflow-x: auto; font-size: 13px; line-height: 1.6; color: #cbd5e1; }
.loading { color: #64748b; text-align: center; padding: 40px; font-size: 18px; }
.error { color: #f87171; }
</style>
</head>
<body>
<h1>&#9670; AI Agents Dashboard</h1>
<p style="color:#64748b;margin-bottom:20px;">Auto-refreshes every 10s</p>
<div id="content"><div class="loading">Loading...</div></div>
<script>
async function load() {
  try {
    const [metrics, costs, agents] = await Promise.all([
      fetch('/api/metrics').then(r=>r.json()),
      fetch('/api/costs').then(r=>r.json()),
      fetch('/api/agents').then(r=>r.json()),
    ]);
    let html = '';

    html += '<div class="card"><h2>Agents</h2><div class="agent-list">';
    (Array.isArray(agents) ? agents : []).forEach(a => {
      html += `<span class="agent-tag">${a}</span>`;
    });
    if (!agents.length) html += '<span style="color:#64748b">No agents found</span>';
    html += '</div></div>';

    html += '<div class="card"><h2>Session Costs</h2><div class="metric-row">';
    const c = costs || {};
    html += `<div class="metric"><div class="value">$${(c.session_cost || 0).toFixed(4)}</div><div class="label">Total Cost</div></div>`;
    html += `<div class="metric"><div class="value">${(c.tokens && c.tokens.total) || 0}</div><div class="label">Total Tokens</div></div>`;
    html += `<div class="metric"><div class="value">${c.calls || 0}</div><div class="label">LLM Calls</div></div>`;
    html += '</div></div>';

    html += '<div class="card"><h2>Per-Agent Metrics</h2>';
    const m = metrics || {};
    const agentKeys = Object.keys(m);
    if (agentKeys.length === 0) {
      html += '<div style="color:#64748b">No metrics yet</div>';
    } else {
      agentKeys.forEach(agent => {
        const d = m[agent];
        html += `<h3 style="color:#38bdf8;margin-top:12px;">${agent}</h3><div class="metric-row">`;
        html += `<div class="metric"><div class="value">${d.call_count}</div><div class="label">Calls</div></div>`;
        html += `<div class="metric"><div class="value">${d.error_count}</div><div class="label">Errors</div></div>`;
        html += `<div class="metric"><div class="value">${(d.error_rate * 100).toFixed(1)}%</div><div class="label">Error Rate</div></div>`;
        html += `<div class="metric"><div class="value">${d.avg_duration_ms}ms</div><div class="label">Avg Duration</div></div>`;
        html += `<div class="metric"><div class="value">${d.max_duration_ms}ms</div><div class="label">Max Duration</div></div>`;
        html += '</div>';
      });
    }
    html += '</div>';

    html += '<div class="card"><h2>Raw Metrics JSON</h2><pre>' + JSON.stringify(metrics, null, 2) + '</pre></div>';
    document.getElementById('content').innerHTML = html;
  } catch (e) {
    document.getElementById('content').innerHTML = '<div class="loading error">Error loading dashboard: ' 
        + e.message + '</div>';
  }
}
load();
</script>
</body>
</html>"""


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/metrics":
            self._json_response(MetricsCollector().get_all_metrics())
        elif self.path == "/api/costs":
            self._json_response(CostTracker().summary())
        elif self.path.startswith("/api/trace/"):
            agent = self.path.split("/api/trace/")[1].split("?")[0]
            viewer = TraceViewer()
            self._json_response({"trace": viewer.format_trace(agent)})
        elif self.path == "/api/agents":
            self._json_response(AgentLogger().get_all_agents())
        elif self.path == "/" or self.path == "/index.html":
            self._serve_html()
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "not found"}).encode())

    def _json_response(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2, default=str).encode())

    def _serve_html(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(DASHBOARD_HTML.encode("utf-8"))

    def log_message(self, format, *args):
        pass


def start_dashboard(host: str = "localhost", port: int = 8080):
    server = HTTPServer((host, port), DashboardHandler)
    print(f"Dashboard running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
