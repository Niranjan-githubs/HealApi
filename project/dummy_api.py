from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/welcome', methods=['GET'])
def welcome():
    return jsonify({"minor": "Hello, world!", "extra": "42"})

@app.route('/fail', methods=['GET'])
def fail():
    return jsonify({"status": "complete"}), 200

@app.route('/added', methods=['GET'])
def added():
    return jsonify({"new": "This is a new endpoint"})

@app.route('/salute', methods=['GET'])
def salute():
    return jsonify({"msg": "Hi!"})

@app.route('/')
def home():
    return 'API is running!'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
