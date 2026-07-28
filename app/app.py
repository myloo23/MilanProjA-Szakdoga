# app.py
from flask import Flask, jsonify, request
from werkzeug.exceptions import BadRequest, UnsupportedMediaType
import logging


app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route('/')
def home():
    app.logger.info("Home route called")
    return "Hello from Flask!"

@app.route('/health')
def health():
    return jsonify(status="UP")

@app.route('/ready')
def ready():
    # no external deps yet; when you add one (DB/registry),
    # check it here and return 503 if it's unreachable
    return jsonify(status="READY")

@app.route('/echo', methods=['POST'])
def echo():
    try:
        data = request.get_json()
    except (BadRequest, UnsupportedMediaType):
        app.logger.error("Invalid JSON payload received")
        return jsonify(error="Invalid JSON payload"), 400

    app.logger.info(f"Echo received: {data}")
    return jsonify(received=data)