from __future__ import annotations

import argparse
from pathlib import Path

from flask import Flask, render_template_string, request

from translator import VARIANT
from parse_module import translate

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def translate_page():
    return "Translator Web Interface"

