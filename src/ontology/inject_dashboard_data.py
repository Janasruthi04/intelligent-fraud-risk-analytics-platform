"""
inject_dashboard_data.py
--------------------------
Embeds dashboard/dashboard_data.json directly into dashboard/index.html
(inside the <script id="dashboard-data" type="application/json"> tag) so the
dashboard is a single self-contained file that works when opened directly
from disk (file://), with no local server and no CORS issues.

Run this after any pipeline re-run that changes dashboard_data.json.
"""
import argparse
import re


def inject(html_path: str, data_path: str):
    with open(data_path) as f:
        data_str = f.read()
    with open(html_path) as f:
        html = f.read()

    pattern = r'(<script id="dashboard-data" type="application/json">)(.*?)(</script>)'
    replacement = r'\1' + data_str.replace("\\", "\\\\") + r'\3'
    new_html, n = re.subn(pattern, lambda m: m.group(1) + data_str + m.group(3), html, flags=re.S)

    if n == 0:
        raise RuntimeError("Could not find dashboard-data script tag in index.html")

    with open(html_path, "w") as f:
        f.write(new_html)
    print(f"Injected {len(data_str):,} bytes of dashboard data into {html_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--html", default="../../dashboard/index.html")
    parser.add_argument("--data", default="../../dashboard/dashboard_data.json")
    args = parser.parse_args()
    inject(args.html, args.data)
