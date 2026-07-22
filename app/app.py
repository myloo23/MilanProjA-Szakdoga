# app.py
from flask import Flask, jsonify, request
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
    data = request.json
    app.logger.info(f"Echo received: {data}")
    return jsonify(received=data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)