import logging
import telegram
import json

from random import sample
from time import sleep
from fsm import FSM
from sys import argv
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

logger_bot = logging.getLogger('bot')
bot_file_handler = logging.FileHandler("bot.log")
bot_log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
bot_file_handler.setFormatter(bot_log_formatter)
if not logger_bot.handlers:
    logger_bot.addHandler(bot_file_handler)

version = "2 (19.07.2017)"


def load_text_and_qas(filename):
    with open(filename, 'r') as f:
        return json.load(f)


class DialogTracker:
    def __init__(self, token):
        self._bot = telegram.Bot(token)
        self._updater = Updater(bot=self._bot)

        dp = self._updater.dispatcher
        dp.add_handler(CommandHandler("start", self._start_cmd))
        dp.add_handler(CommandHandler("reset", self._reset_cmd))
        dp.add_handler(CommandHandler("stop", self._reset_cmd))
        dp.add_handler(CommandHandler("factoid_question", self._factoid_question_cmd))
        dp.add_handler(CommandHandler("help", self._help_cmd))
        dp.add_handler(CommandHandler("text", self._text_cmd))

        dp.add_handler(MessageHandler(Filters.text, self._echo_cmd))

        dp.add_handler(CallbackQueryHandler(self._button))
        dp.add_error_handler(self._error)

        self._users_fsm = {}
        self._users = {}
        self._text_and_qas = load_text_and_qas('data/squad-25-qas.json')
        self._text_ind = 0

    def start(self):
        self._updater.start_polling()
        self._updater.idle()

    def _reset_cmd(self, bot, update):
        self._log_user('_reset_cmd', update)

        self._add_fsm_and_user(update)
        fsm = self._users_fsm[update.effective_user.id]
        fsm.return_to_init()
        username = self._user_name(update)
        update.message.reply_text(
            "{}, please type /start to begin the journey {}".format(username, telegram.Emoji.MOUNTAIN_RAILWAY)
        )
        update.message.reply_text("Also, you can type /help to get help")


    def _factoid_question_cmd(self, bot, update):
        self._log_user('_factoid_question_cmd', update)

        self._add_fsm_and_user(update)

        username = self._user_name(update)
        fsm = self._users_fsm[update.effective_user.id]
        fsm._last_user_message = update.message.text

        if fsm.is_init():
            update.message.reply_text(
                "{}, please type /start to begin the journey {}".format(username, telegram.Emoji.MOUNTAIN_RAILWAY)
            )
            update.message.reply_text("Also, you can type /help to get help")
        else:
            fsm.return_to_start()
            fsm.ask_question()

    def _start_cmd(self, bot, update):
        self._log_user('_start_cmd', update)

        self._text_ind += 1

        logger_bot.info("BOT[_start_cmd] text_id: {}".format(self._text_ind))

        message = 'Hi {}!'.format(update.effective_user.first_name)
        update.message.reply_text(message)

        message = ("I'm Convai.io bot#1337. My main goal is to talk about the text"
                   " provided below. You can ask me questions about the text,"
                   " give answers to my questions and even chit-chat about anything."
                   " Type /help to get some more information.")
        update.message.reply_text(message)

        update.message.reply_text("The text: \"{}\"".format(self._text()))
        update.message.reply_text("Also you can the get text by using /text command")
        update.message.reply_text("Ask me something or I'll do it in 45 seconds")

        self._add_fsm_and_user(update, True)
        fsm = self._users_fsm[update.effective_user.id]
        fsm.start()

    def _help_cmd(self, bot, update):
        self._log_user('_help_cmd', update)

        self._add_fsm_and_user(update)

        message = ("/start - starts the chat\n"
                   "/text - shows current text to discuss\n"
                   "/factoid_question - bot asks factoid question about text\n"
                   "/help - shows this message\n"
                   "/reset - reset the bot\n"
                   "/stop - stop the bot\n"
                   "\n"
                   "Version: {}".format(version))
        update.message.reply_text(message)

    def _text_cmd(self, bot, update):
        self._log_user('_text_cmd', update)

        self._add_fsm_and_user(update)

        update.message.reply_text("The text: \"{}\"".format(self._text()))

    def _echo_cmd(self, bot, update):
        self._log_user('_echo_cmd', update)

        self._add_fsm_and_user(update)

        username = self._user_name(update)
        fsm = self._users_fsm[update.effective_user.id]
        fsm._last_user_message = update.message.text

        if fsm.is_init():
            update.message.reply_text(
                "{}, please type /start to begin the journey {}.".format(username, telegram.Emoji.MOUNTAIN_RAILWAY)
            )
            update.message.reply_text("Also, you can type /help to get help")
        elif fsm.is_asked():
            fsm.check_user_answer_on_asked()
        else:
            fsm.classify()

    def _button(self, bot, update):
        query = update.callback_query
        logger_bot.info("USER[_button]: {}".format(query.data))
        bot.edit_message_text(text="...", chat_id=query.message.chat_id, message_id=query.message.message_id)

        self._users_fsm[update.effective_user.id].go_from_choices(query.data)

    def _log_user(self, cmd, update):
        logger_bot.info("USER[{}]: {}".format(cmd, update.message.text))

    def _add_fsm_and_user(self, update, hard=False):
        if update.effective_user.id not in self._users_fsm:
            fsm = FSM(self._bot, update.effective_chat, update.effective_user, self._text_and_qa())
            self._users_fsm[update.effective_user.id] = fsm
            self._users[update.effective_user.id] = update.effective_user
        elif update.effective_user.id in self._users_fsm and hard:
            self._users_fsm[update.effective_user.id].set_text_and_qa(self._text_and_qa())
            self._users_fsm[update.effective_user.id].clear_all()

    def _error(self, bot, update, error):
        logger.warn('Update "%s" caused error "%s"' % (update, error))

    def _user_name(self, update):
        return self._users[update.effective_user.id].first_name

    def _text(self):
        return self._text_and_qa()['text']

    def _text_and_qa(self):
        return self._text_and_qas[self._text_ind % len(self._text_and_qas)]


if __name__ == '__main__':
    if argv[1] == 'test':
        token = "447990426:AAH4OvsshJi_YVEKDeoosaRlQYhbzNfwtDU"
    else:
        token = "381793449:AAEogsUmzwqgBQiIz6OmdzWOY6iU_GwATeI"
    dt = DialogTracker(token)
    dt.start()
