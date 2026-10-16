import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
start = int(sys.argv[1])
end = int(sys.argv[2])
path = sys.argv[3] if len(sys.argv) > 3 else 'app.py'
lines = open(path, encoding='utf-8').read().splitlines()
for i in range(start - 1, min(end, len(lines))):
    print(str(i + 1) + ': ' + lines[i])
