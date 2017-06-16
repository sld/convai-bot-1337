import logging
import threading
import telegram

from time import sleep
from transitions.extensions import LockedMachine as Machine
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters


# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


class BotFSM:
    states = ['init', 'started', 'asked', 'waiting', 'classifying']

    def __init__(self, bot):
        self.machine = Machine(model=self, states=BotFSM.states, initial='init')

        self.machine.add_transition('start', 'init', 'started', after='wait_for_user_typing')
        self.machine.add_transition('ask_question', 'started', 'asked', after='ask_question_to_user')
        self.machine.add_transition('classifying', 'asked', 'classifying')
        self.machine.add_transition('long_waiting', 'asked', 'waiting', after='say_user_about_long_waiting')
        self.machine.add_transition('too_long_waiting', 'waiting', 'waiting')
        self._chat = None
        self._bot = bot

    def wait_for_user_typing(self):
        def _wait():
            slept = 0

            while True:
                sleep(1)
                slept += 1
                if self.is_started() and slept > 10:
                    self.ask_question()
                    slept = 0

        t = threading.Thread(target=_wait)
        t.start()

    def ask_question_to_user(self):
        def _wait():
            slept = 0

            while True:
                sleep(1)
                slept += 1
                if self.is_asked() and slept > 15:
                    self.long_waiting()
                    slept = 0
        self._bot.send_message(self._chat.id, "I'm working!! And asking you a question...")
        self._bot.send_message(self._chat.id, "How are you?")

        t = threading.Thread(target=_wait)
        t.start()

    def say_user_about_long_waiting(self):
        self._bot.send_message(self._chat.id, "Why you're not answering? Am I bother you?(")

    def too_long_waiting(self):
        print("Why so silence?")


class Bot:
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
        self._fsm = BotFSM(self._bot)
        self._updater = Updater(bot=self._bot)

        dp = self._updater.dispatcher
        dp.add_handler(CommandHandler("start", self._start_cmd))
        dp.add_handler(CommandHandler("help", self._help_cmd))
        dp.add_handler(CommandHandler("text", self._text_cmd))

        dp.add_handler(MessageHandler(Filters.text, self._echo_cmd))
        dp.add_error_handler(self._error)

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

        update.message.reply_text("The text: \"{}\"".format(Bot.text))
        update.message.reply_text("Also you can the get text by typing /text command")

        self._fsm = BotFSM(self._bot)
        self._fsm._chat = update.effective_chat
        self._fsm.start()


    def _help_cmd(self, bot, update):
        message = ("\start - shows greeting message\n"
                   "\\text - shows the text\n"
                   "\help - shows this message.")
        update.message.reply_text(message)

    def _text_cmd(self, bot, update):
        update.message.reply_text("The text: \"{}\"".format(Bot.text))

    def _echo_cmd(self, bot, update):
        self._save_chat_info(update)

        if self._fsm.is_init():
            update.message.reply_text(
                "{}, please type /start to begin the journey.".format(self._user_first_name)
            )
        elif self._fsm.is_asked():
            self._fsm.classifying()
            update.message.reply_text("Thanks for the answer! {}, now wait!".format(self._user_first_name))
        else:
            update.message.reply_text("You type me: {}".format(update.message.text))

    def _save_chat_info(self, update):
        self._user_first_name = update.effective_user.first_name

    def _error(self, bot, update, error):
        logger.warn('Update "%s" caused error "%s"' % (update, error))


if __name__ == '__main__':
    bot = Bot()
    bot.start()

