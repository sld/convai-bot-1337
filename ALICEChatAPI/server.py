#!/usr/bin/env python

from flask import Flask, request, jsonify
from flask import render_template
import ai

app = Flask(__name__)


@app.route("/respond", methods=['POST'])
def respond():
    # bot.reset() not work
    user_sentences = request.json['sentences']
    print(user_sentences)
    response = "..."
    for s in user_sentences:
        response = bot.respond(s).replace("\n", "")
    return jsonify({'message': response})

if __name__ == '__main__':
    bot = ai.Chatbot()
    bot.initialize("aiml-dir")
    app.run(debug=False, host='0.0.0.0', port=3000)
