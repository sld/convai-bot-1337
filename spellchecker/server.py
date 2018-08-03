import logging
import jamspell
from flask import Flask, request, jsonify

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger('spellchecker')

app = Flask(__name__)


@app.route("/respond", methods=['POST'])
def respond():
    # bot.reset() not work
    user_sentences = request.json['sentences']

    # make correction
    res = corrector.FixFragment(user_sentences)

    logger.info('original text: {}'.format(user_sentences))
    logger.info('corrected text: {}'.format(res))

    return jsonify({'message': res})


if __name__ == '__main__':
    corrector = jamspell.TSpellCorrector()
    corrector.LoadLangModel('/model/en.bin')
    app.run(debug=False, host='0.0.0.0', port=3050)
