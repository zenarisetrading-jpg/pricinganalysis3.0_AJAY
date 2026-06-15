with open('scratch/uvicorn.combined.log', 'r', encoding='utf-16') as f:
    lines = f.readlines()
print(f"Read {len(lines)} lines from uvicorn.combined.log:")
for l in lines[-40:]: # print last 40 lines
    print(l.strip())
