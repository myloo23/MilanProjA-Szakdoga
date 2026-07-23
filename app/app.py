# app.py
from flask import Flask, jsonify, request
from werkzeug.exceptions import BadRequest
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

@app.route('/echo', methods=['POST'])
def echo():
    try:
        data = request.get_json()
    except BadRequest:
        app.logger.error("Invalid JSON payload received")
        return jsonify(error="Invalid JSON payload"), 400

    app.logger.info(f"Echo received: {data}")
    return jsonify(received=data)