from flask import Flask, jsonify


app = Flask(__name__)


@app.route('/dialog_quality')
def dialog_quality():
    return jsonify(message='ok dialog', quality=0)


@app.route('/utterance_quality')
def utterance_quality():
    return jsonify(message='ok utterance', quality=0)


if __name__ == '__main__':
    app.run(debug=True)
