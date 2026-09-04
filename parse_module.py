from __future__ import annotations
import argparse
from pathlib import Path
from flask import Flask, render_template_string, request
from translator import VARIANT, translate

app = Flask(__name__)

CSS = """body{font-family:Inter,Arial,sans-serif;background:#18181b;color:#fafafa;margin:0}
.wrap{max-width:1260px;margin:24px auto;padding:0 20px}
.panel{background:#27272a;border-radius:22px;padding:22px}
.grid{display:grid;grid-template-columns:0.9fr 1.1fr;gap:18px}
textarea,pre{width:100%;min-height:380px;box-sizing:border-box;background:#09090b;color:#fafafa;
border:1px solid #52525b;border-radius:14px;padding:14px;font:14px SFMono-Regular,Menlo,monospace}
button{background:#f97316;color:#111827;border:0;border-radius:12px;padding:11px 20px;font-weight:800}
.bad{color:#fb7185}.ok{color:#34d399}"""