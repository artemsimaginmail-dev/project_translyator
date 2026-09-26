from __future__ import annotations

import argparse
from pathlib import Path

from flask import Flask, render_template_string, request

from translator import VARIANT
from parse_module import translate

app = Flask(__name__)

CSS = 'body{font-family:Inter,Arial,sans-serif;background:#18181b;color:#fafafa;margin:0}.wrap{max-width:1260px;margin:24px auto;padding:0 20px}.panel{background:#27272a;border-radius:22px;padding:22px}.grid{display:grid;grid-template-columns:0.9fr 1.1fr;gap:18px}textarea,pre{width:100%;min-height:380px;box-sizing:border-box;background:#09090b;color:#fafafa;border:1px solid #52525b;border-radius:14px;padding:14px;font:14px SFMono-Regular,Menlo,monospace}button{background:#f97316;color:#111827;border:0;border-radius:12px;padding:11px 20px;font-weight:800}.bad{color:#fb7185}.ok{color:#34d399}' 

def default_source() -> str:
    path = Path(__file__).with_name("source.txt")
    return path.read_text(encoding="utf-8") if path.exists() else ""

TEMPLATE = """
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <title>{{ title }}</title>
  <style>{{ css }}</style>
  <style>textarea,pre{max-height:430px;overflow:auto}</style>
</head>
<body>
  <main class="wrap">
    <section class="panel">
      <h1>{{ title }}</h1>
      <p>Интерфейс транслятора</p>
      <form method="post">
        <div class="grid">
          <label>Исходная программа
            <textarea name="source">{{ source_text }}</textarea>
          </label>
          <label>Результат
            <pre>{{ output }}</pre>
          </label>
        </div>
        <p><button type="submit">Сформировать результат</button></p>
      </form>
      <h2>Диагностика</h2>
      {% if diagnostics %}
        <ul>{% for item in diagnostics %}<li class="bad">{{ item }}</li>{% endfor %}</ul>
      {% else %}
        <p class="ok">Ошибок не обнаружено</p>
      {% endif %}
    </section>
  </main>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def translate_page():
    source_text = request.form.get("source", default_source())
    result = translate(source_text, VARIANT)
    diagnostics = result.messages
    output = result.output
    if diagnostics:
        # при наличии ошибок результат трансляции не формируется
        output = "Трансляция не выполнена: устраните ошибки в исходном тексте и повторите запуск."   
    return render_template_string(
        TEMPLATE,
        title=VARIANT.title,        
        css=CSS,
        source_text=source_text,
        output=output,
        diagnostics=diagnostics,
    ) 

def main() -> int:
    parser = argparse.ArgumentParser(description="Translator Web Interface")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()
    app.run(host=args.host, port=args.port, debug=False, use_reloader=False)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())