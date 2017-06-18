import logging
import telegram

from time import sleep
from fsm import FSM
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)
version = "1 (18.06.2017)"


class DialogTracker:
    text =  ("The Notre Dame football team has a long history, first beginning"
         " when the Michigan Wolverines football team brought football to Notre Dame in"
         " 1887 and played against a group of students. In the long history since then,"
         " 13 Fighting Irish teams have won consensus national championships (although"
         " the university only claims 11), along with another nine teams being named"
         " national champion by at least one source. Additionally, the program has the"
         " most members in the College Football Hall of Fame, is tied with Ohio State"
         " University with the most Heisman Trophies won, and have the highest winning"
         " percentage in NCAA history. With the long history, Notre Dame has"
         " accumulated many rivals, and its annual game against USC for the Jeweled"
         " Shillelagh has been named by some as one of the most important in college"
         " football and is often called the greatest intersectional rivalry in college"
         " football in the country.")

    def __init__(self):
        token = "381793449:AAEogsUmzwqgBQiIz6OmdzWOY6iU_GwATeI"
        self._bot = telegram.Bot(token)
        self._updater = Updater(bot=self._bot)

        dp = self._updater.dispatcher
        dp.add_handler(CommandHandler("start", self._start_cmd))
        dp.add_handler(CommandHandler("help", self._help_cmd))
        dp.add_handler(CommandHandler("text", self._text_cmd))

        dp.add_handler(MessageHandler(Filters.text, self._echo_cmd))

        dp.add_handler(CallbackQueryHandler(self._button))
        dp.add_error_handler(self._error)

        self._users_fsm = {}
        self._users = {}

    def start(self):
        self._updater.start_polling()
        self._updater.idle()

    def _start_cmd(self, bot, update):
        message = 'Hello Mighty {}!'.format(update.effective_user.first_name)
        update.message.reply_text(message)

        message = ("I'm Convai.io bot #1337. My main goal is to talk about the text"
                   " I provided below. You can ask me questions about the text or I can do the same."
                   " Type /help to get some more information.")
        update.message.reply_text(message)

        update.message.reply_text("The text: \"{}\"".format(DialogTracker.text))
        update.message.reply_text("Also you can the get text by typing /text command")

        self._add_fsm_and_user(update, True)
        fsm = self._users_fsm[update.effective_user.id]
        fsm.start()

    def _help_cmd(self, bot, update):
        self._add_fsm_and_user(update)

        message = ("/start - starts the chat\n"
                   "/text - shows a text to discuss\n"
                   "/help - shows this message.\n"
                   "\n"
                   "Version: {}".format(version))
        update.message.reply_text(message)

    def _text_cmd(self, bot, update):
        self._add_fsm_and_user(update)

        update.message.reply_text("The text: \"{}\"".format(DialogTracker.text))

    def _echo_cmd(self, bot, update):
        self._add_fsm_and_user(update)

        username = self._user_name(update)
        fsm = self._users_fsm[update.effective_user.id]
        fsm._last_user_message = update.message.text

        if fsm.is_init():
            update.message.reply_text(
                "{}, please type /start to begin the journey.".format(username)
            )
            update.message.reply_text("Also, you can type /help to get help")
        elif fsm.is_asked():
            fsm.classify()
        else:
            fsm.classify()

    def _button(self, bot, update):
        query = update.callback_query

        bot.edit_message_text(text="Thank you, {}!".format(self._user_name(update)),
                              chat_id=query.message.chat_id,
                              message_id=query.message.message_id)
        self._users_fsm[update.effective_user.id].go_from_choices(query.data)

    def _add_fsm_and_user(self, update, hard=False):
        if hard or update.effective_user.id not in self._users_fsm:
            fsm = FSM(self._bot, update.effective_chat, update.effective_user, DialogTracker.text)
            self._users_fsm[update.effective_user.id] = fsm
            self._users[update.effective_user.id] = update.effective_user

    def _error(self, bot, update, error):
        logger.warn('Update "%s" caused error "%s"' % (update, error))

    def _user_name(self, update):
        return self._users[update.effective_user.id].first_name


if __name__ == '__main__':
    dt = DialogTracker()
    dt.start()

