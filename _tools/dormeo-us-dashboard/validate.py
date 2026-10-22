#!/usr/bin/env python3
"""Check a rendered dashboard before it is pushed. Usage: validate.py <index.html>"""
import json, re, subprocess, sys, tempfile
s = open(sys.argv[1], encoding="utf8").read(); bad = []
if re.search(r"\{\{[A-Z_0-9]+\}\}", s): bad.append("unfilled placeholders")
for i, js in enumerate(re.findall(r"<script>(.*?)</script>", s, re.S)):
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f: f.write(js)
    r = subprocess.run(["node", "--check", f.name], capture_output=True, text=True)
    if r.returncode: bad.append(f"script {i}: {r.stderr.strip().splitlines()[-1] if r.stderr else 'syntax error'}")
for name in ("PL", "PRODUCTS", "ADS", "CAMP", "INV", "REC"):
    if not re.search(r"(const|let) %s ?= ?" % name, s): bad.append("missing " + name)
m = re.search(r"let ADS=(\[\[.*?\]\])", s)
if m and len(json.loads(m.group(1))) < 30: bad.append("fewer than 30 days of ads")
for w in ("Forgotten", "Deodorant"):
    if w in s: bad.append("template leak: " + w)
print("VALID" if not bad else "INVALID: " + "; ".join(bad)); sys.exit(1 if bad else 0)
