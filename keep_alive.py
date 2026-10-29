import random
from threading import Thread

from flask import Flask

app = Flask('')


@app.route('/')
def home():
    return 'Im in!'


def run():
    app.run(host='0.0.0.0', port=random.randint(2000, 9000))


def keep_alive():
    """Serve a tiny web page in the background so the host keeps the bot awake."""
    Thread(target=run, daemon=True).start()
