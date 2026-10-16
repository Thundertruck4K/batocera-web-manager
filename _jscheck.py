"""Extrae los bloques <script> de templates/index.html para validarlos con node --check."""
import re
from pathlib import Path

html = Path("templates/index.html").read_text(encoding="utf-8")
scripts = re.findall(r"<script>(.*?)</script>", html, re.S)
Path("_extracted.js").write_text("\n;\n".join(scripts), encoding="utf-8")
print("bloques <script>:", len(scripts), "| caracteres:", sum(len(s) for s in scripts))
