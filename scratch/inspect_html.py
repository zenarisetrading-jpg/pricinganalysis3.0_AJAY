import re

path = r"d:\pricing_analysis\dashboard\price_benchmarking.html"
with open(path, "r", encoding="utf-8") as f:
    html = f.read()

print("--- HEADERS & TABS ---")
for line in html.split("\n"):
    line_stripped = line.strip()
    if any(tag in line_stripped for tag in ["<h1", "<h2", "<h3", "role=\"tab\"", "class=\"nav-link", "id=\"tab-", "<title>"]):
        print(line_stripped)

print("\n--- SCRIPTS & APIS ---")
for line in html.split("\n"):
    if "fetch(" in line or "axios" in line or "/api/v1/" in line:
        print(line.strip())
