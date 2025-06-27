from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route('/greeting', methods=['GET'])
def greeting():
    # Now returns 'minor' and 'extra' as strings
    return jsonify({"minor": "Hello, world!", "extra": "42"})

@app.route('/fail', methods=['GET'])
def fail():
    # Now returns 200 with 'result' as integer
    return jsonify({"result": 123}), 200

@app.route('/added', methods=['GET'])
def added():
    # New endpoint as per new spec
    return jsonify({"new": True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
