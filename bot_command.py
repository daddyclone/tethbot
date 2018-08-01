import argparse
import contextlib
import io
import logging
import shlex
import sys

from markov_bot import TethBot


@contextlib.contextmanager
def dup2(stream):
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = stream
    sys.stderr = stream

    def null_exit(status):
        pass

    sys.exit = null_exit
    try:
        yield
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr


class BotCommand(object):

    def __init__(
            self, name: str, bot: TethBot, parser_root: argparse._SubParsersAction
    ):
        self.bot = bot
        self.parser = parser_root.add_parser(name)
        self.parser.set_defaults(func=self.execute)

    def execute(self, namespace):
        print(f"Command {self.__class__}:{namespace}")

class SayCommand(BotCommand):

    def __init__(self, bot: TethBot, parser_root: argparse._SubParsersAction):
        super().__init__("say", bot, parser_root)
        self.parser.add_argument("target")
        self.parser.add_argument("what")

    def execute(self, namespace):
        if "target" in namespace and "what" in namespace:
            self.bot.eventloop.schedule(
                self.bot.message, namespace.target, namespace.what
            )


class TriggerCommand(BotCommand):

    def __init__(self, bot: TethBot, parser_root: argparse._SubParsersAction):
        super().__init__("trigger", bot, parser_root)
        self.parser.add_argument("--target")
        self.parser.add_argument("--subject")
        self.parser.add_argument("--length", type=int)

    def execute(self, namespace):
        # Random or not.
        if "subject" not in namespace or namespace.subject is None:
            f = lambda t: self.bot.eventloop.schedule(
                self.bot.message, t, self.bot._gen_random_sentence()
            )
        else:
            f = lambda t: self.bot.eventloop.schedule(
                self.bot._gen_related_sentence(namespace.subject.split(), t, "")
            )

        # Targeted or all?
        if "target" not in namespace or namespace.target is None:
            # All channels
            for channel in self.bot.channels.keys():
                f(channel)
        else:
            f(namespace.target)


class JoinCommand(BotCommand):
    def __init__(self, bot: TethBot, parser_root: argparse._SubParsersAction):
        super().__init__("join", bot, parser_root)
        self.parser.add_argument("target")

    def execute(self, namespace):
        self.bot.eventloop.schedule(self.bot.join, namespace.target)


class CycleCommand(BotCommand):

    def __init__(self, bot: TethBot, parser_root: argparse._SubParsersAction):
        super().__init__("cycle", bot, parser_root)
        self.parser.add_argument("target")

    def execute(self, namespace):
        self.bot.eventloop.schedule(self.bot.part, namespace.target)
        self.bot.eventloop.schedule(self.bot.join, namespace.target)


class PartCommand(BotCommand):
    def __init__(self, bot: TethBot, parser_root: argparse._SubParsersAction):
        super().__init__("part", bot, parser_root)
        self.parser.add_argument("target")
        self.parser.add_argument("--message", type=str)

    def execute(self, namespace):
        msg = namespace.message if 'message' in namespace else None
        self.bot.eventloop.schedule(self.bot.part, namespace.target, message=msg)

class NickCommand(BotCommand):
    def __init__(self, bot: TethBot, parser_root: argparse._SubParsersAction):
        super().__init__("nick", bot, parser_root)
        self.parser.add_argument("newnick")

    def execute(self, namespace):
        self.bot.eventloop.schedule(self.bot.set_nickname, namespace.newnick)

def parse_privmsg(bot: TethBot, source: str, target: str, message: str):
    # First argument is password.
    arguments = shlex.split(message)
    if arguments[0] != bot.bot_password:
        logging.info(f"Regular PrivMSG: '{source}':'{message}'")
        sentence = bot._gen_random_sentence()
        bot.message(target, sentence)
        return
    del arguments[0]

    # Parse rest...
    top_parser = argparse.ArgumentParser(add_help=True)
    top_parser.set_defaults(bot=bot)
    subparsers = top_parser.add_subparsers(help="command")

    modules = [
        SayCommand(bot, subparsers),
        JoinCommand(bot, subparsers),
        CycleCommand(bot, subparsers),
        PartCommand(bot, subparsers),
        TriggerCommand(bot, subparsers),
        NickCommand(bot, subparsers),
    ]

    # process command. Send any help back out back to the caller.
    sstring = io.StringIO()
    with dup2(sstring):
        try:
            parse_known_args = top_parser.parse_args(arguments)
        except:
            top_parser.print_usage()
            return
        else:
            command = parse_known_args
    print(command)
    sstring.seek(0)
    privmsgd_lines = 0
    for s in sstring.readlines():
        s = s.replace("\n", "")
        if len(s) > 0:
            privmsgd_lines += 1
            bot.message(target, s)

    # Execute Command
    if privmsgd_lines == 0 and "func" in command:
        command.func(command)
