from __future__ import annotations

import argparse
from pathlib import Path

from flask import Flask, render_template_string, request

from translator import VARIANT
from parse_module import translate

app = Flask(__name__)

def default_source() -> str:
    path = Path(__file__).with_name("source.txt")
    return path.read_text(encoding="utf-8") if path.exists() else ""

TEMPLATE = """
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <title>{{ title }}</title>
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