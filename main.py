import logging

from transitions import Machine
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters


text =  ("The Notre Dame football team has a long history, first beginning"
         "when the Michigan Wolverines football team brought football to Notre Dame in"
         "1887 and played against a group of students. In the long history since then,"
         "13 Fighting Irish teams have won consensus national championships (although"
         "the university only claims 11), along with another nine teams being named"
         "national champion by at least one source. Additionally, the program has the"
         "most members in the College Football Hall of Fame, is tied with Ohio State"
         "University with the most Heisman Trophies won, and have the highest winning"
         "percentage in NCAA history. With the long history, Notre Dame has"
         "accumulated many rivals, and its annual game against USC for the Jeweled"
         "Shillelagh has been named by some as one of the most important in college"
         "football and is often called the greatest intersectional rivalry in college"
         "football in the country.")


class Bot:
    states = ['start', 'ask', 'long']

    def __init__(self):
        self.machine = Machine(model=self, state=Bot.states, initial='start')

        self.machine.add_transition('ask_question', 'start', 'ask')
        self.machine.add_transition('long_waiting', 'ask', 'long')
        self.machine.add_transition('too_long_waiting', 'long', 'long')


    def ask_question(self):
        print("How are you?")

    def long_waiting(self):
        print("Please, type something. I'm scaried.")

    def too_long_waiting(self):
        print("Why so silence?")


def start_cmd(bot, update):
    message = 'Hello Mighty {}!'.format(update.effective_user.first_name)
    update.message.reply_text(message)

    message = ("I'm Convai.io bot #1337. My main goal is to talk about the text"
               " I provided below. You can ask me questions about the text or I can do the same."
               " Type /help to get some more information.")
    update.message.reply_text(message)

    update.message.reply_text("The text: \"{}\"".format(text))
    update.message.reply_text("Also you can the get text by typing /text command")


def help_cmd(bot, update):
    message = """\start - shows greeting message
\\text - shows the text
\help - shows this message."""
    update.message.reply_text(message)


def text_cmd(bot, update):
    update.message.reply_text("The text: \"{}\"".format(text))


def main():
    token = "381793449:AAEogsUmzwqgBQiIz6OmdzWOY6iU_GwATeI"
    updater = Updater(token)

    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start_cmd))
    dp.add_handler(CommandHandler("help", help_cmd))
    dp.add_handler(CommandHandler("text", text_cmd))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()

