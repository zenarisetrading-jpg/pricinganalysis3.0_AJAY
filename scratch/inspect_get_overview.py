with open(r"d:\pricing_analysis\features\price_benchmarking\routes.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

start_idx = None
end_idx = None
for i, line in enumerate(lines):
    if "async def get_overview(" in line:
        start_idx = i
    if start_idx is not None and i > start_idx and "async def get_" in line:
        end_idx = i
        break

if start_idx is not None:
    if end_idx is None:
        end_idx = start_idx + 150
    print(f"Lines {start_idx+1} to {end_idx}:")
    for idx in range(start_idx, end_idx):
        print(f"{idx+1}: {lines[idx]}", end="")
else:
    print("Could not find get_overview")
