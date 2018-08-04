import logging
import random
import re
import string
import collections
import attr
import typing

import nltk
import pydle
import crazy_text


@attr.s(frozen=True, slots=True)
class BanEntry(object):
    mask: str = attr.ib()
    responsible: str = attr.ib()
    ts: int = attr.ib(converter=int)


class TethFactory(object):

    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        self.args = args
        self.markov = kwargs.get("markov", "MarkovTeth")
        self.bot_password = kwargs.get("bot_password", "nigger6")
        self.ignore_nicks = kwargs.get("ignore_nicks", ["Hunk"])
        self.nick = kwargs.get("nick", "default-teth")
        self.server = kwargs.get("server", "irc.rizon.net")
        self.corpus = kwargs.get("corpus", "teth_chat")
        self.port = kwargs.get("port", 6697)
        self.state_size = kwargs.get("state_size", 3)
        self.channels = kwargs.get("channels", ["#teth-test"])
        self.tls = kwargs.get("tls", True)
        self.tls_verify = kwargs.get("tls_verify", False)
        self.bully = kwargs.get("bully", "teth")

    def __call__(self):
        while True:
            try:
                client = TethBot(
                    self.nick,
                    model=getattr(crazy_text, self.markov)(
                        self.corpus, self.state_size
                    ).model,
                    channels=self.channels,
                    bot_password=self.bot_password,
                    bully=self.bully,
                    **self.kwargs,
                )
                client.connect(
                    self.server,
                    self.port,
                    tls=self.tls,
                    tls_verify=self.tls_verify,
                    **self.kwargs,
                )
                client.handle_forever()
            except AttributeError as e:
                logging.exception("Bad Model")
                break
            except KeyboardInterrupt:
                logging.info("Exiting")
                break
            except RuntimeError as e:
                logging.exception("bad")
            except:
                logging.exception("Respawned")


class TethBot(pydle.Client):
    __version__ = 43.3

    def __init__(self, *args, **kwargs):
        self.line_counter: collections.Counter = collections.Counter()
        self.mention_count: collections.Counter = collections.Counter()
        self.word_split_pattern: typing.Pattern = re.compile(r"\s+")
        self.punctuation_table: typing.Dict[str, str] = str.maketrans(
            dict.fromkeys(string.punctuation)
        )
        self.startup_channels: typing.List[str] = kwargs.get("channels", [])
        self.model: crazy_text.RandomModel = kwargs.get("model", None)
        self.bully: str = kwargs.get("bully", "teth")
        self.ignore_nicks: typing.List[str] = kwargs.get("ignore_nicks", [])
        self.bot_password: str = kwargs.get("bot_password", "nigger6")
        self.ban_lists: typing.Dict[str, typing.Set[BanEntry]] = {}
        self.ban_lists_waiting: typing.Dict[str, bool] = {}
        self.public_chattiness: int = kwargs.get("public_chattiness", 20)
        self.mention_chattiness: int = kwargs.get("mention_chattiness", 5)
        logging.debug(f"Channels {self.startup_channels}")
        super(pydle.Client, self).__init__(*args, **kwargs)

    @pydle.coroutine
    def on_connect(self):
        logging.debug(f" In connect and my channels are {self.startup_channels}")
        for channel in self.startup_channels:
            logging.info(f"Joining {channel}")
            self.eventloop.schedule(self.join, channel)

        # monitor whomever we're cyberbullying
        if not self.is_same_nick(self.bully, self.nickname):
            self.eventloop.schedule(self.monitor, self.bully)

        # Run Timers
        self.eventloop.schedule_periodically(10.0, self.timers)

    @pydle.coroutine
    def timers(self):
        logging.debug("Timers.")

        # check if we're still joined to channels or if we've been emo-kicked...
        for x in set(self.startup_channels) - set(self.channels.keys()):
            self.eventloop.schedule(self.join, x)

    @pydle.coroutine
    def on_user_online(self, nick):
        for channel in self.channels.keys():
            self.eventloop.schedule(
                self.message, channel, f"ALERT THE REAL {nick} JUST LOGGED IN [AMSG]"
            )

    @pydle.coroutine
    def on_invite(self, channel, by):
        logging.info(f"Invited to {channel} by {by}. Joining!")
        self.eventloop.schedule(self.join, channel)
        self.startup_channels.append(channel)

    @pydle.coroutine
    def on_raw_473(self, message):
        """Cannot join channel, invite only, knock"""
        self.rawmsg("knock", message.params[1])

    @pydle.coroutine
    def on_raw_474(self, message):
        """Cannot join channel, banned. Trigger getting banlist """
        channel = message.params[1]
        if channel in self.ban_lists_waiting:
            # Already requesting banlist
            return
        self.ban_lists[channel] = set()
        self.ban_lists_waiting[channel] = True
        self.rawmsg("mode", channel, "+b")

    @pydle.coroutine
    def on_raw_367(self, message):
        """ getting banlist entry... """
        if len(message.params) < 5:
            logging.debug("Ban list has wrong number of parameters")
            return
        channel = message.params[1]
        mask = message.params[2]
        emo = message.params[3]
        ts = message.params[4]
        self.ban_lists[channel].add(BanEntry(mask=mask, responsible=emo, ts=ts))

    @pydle.coroutine
    def on_raw_368(self, message):
        """ done getting banlist """
        channel = message.params[1]
        if channel in self.ban_lists:
            logging.debug(self.ban_lists[channel])
        if channel in self.ban_lists_waiting:
            del self.ban_lists_waiting[channel]

    @pydle.coroutine
    def on_raw_404(self, message):
        """Cannot send to channel, banned or moderated. Send random privmsg to random if cannot evade"""
        random_nick = random.choice(
            list(
                self.channels[message.params[1]]["users"]
                - ({self.nickname} | set(self.ignore_nicks))
            )
        )
        sentence = self._gen_random_sentence()
        self.eventloop.schedule(self.message, random_nick, sentence)

    @pydle.coroutine
    def on_message(self, source, target, message):
        # public message
        if any(map(lambda x: self.is_same_nick(target, x), self.ignore_nicks)):
            return
        if self.is_same_nick(target, self.nickname):
            return

        # is it a private message.
        if not source.startswith("#"):
            from bot_command import parse_privmsg

            self.eventloop.schedule(parse_privmsg, self, source, target, message)
            return

        # CAW CAW
        if self.is_same_nick(source, self.nickname):
            self.message(target, message)
            return

        # public message
        logging.debug(
            f"Lines since Blog {self.line_counter[source]}, Mentions: {self.mention_count[source]}"
        )
        try:
            self.line_counter[source] += 1
            lcm = message.lower()
            is_mentioned = self.bully in lcm and f".{self.bully}" not in lcm
            if is_mentioned:
                self.mention_count[source] += 1
            if (
                self.line_counter[source] % self.public_chattiness == 0
                or (
                    is_mentioned
                    and self.mention_count[source] % self.mention_chattiness == 0
                )
                or f"!{self.bully}" in lcm
            ):
                self.line_counter[source] = 0
                self.mention_count[source] = 0

                self.eventloop.schedule(self._blog_task, message, source, target)
        except:
            logging.exception("some gay shit")

    def _blog_task(self, message : str, source : str, target : str):
        """
        Try to generate one based on context...
        Search for a few seconds, if nothing is found, just use a random quip.

        :param message:
        :param source:
        :param target:
        :return:
        """
        for idx in range(random.randint(1, 3)):
            nouns = self._nouns_in_sentence(message)
            if len(nouns) > 0:
                message = self._search(message, nouns, source, target)
            else:
                sentence = self._gen_random_sentence()
                message = sentence
                heading = random.choices(
                    ["", f"{target}: ", f"{target}, "], [.5, .3, .2]
                )[0]
                self.message(source, f"{heading}{sentence}")

    def _search(self, message : str, nouns : typing.List[str], source : str, target : str):
        """
        Search for a sentence that contains nouns
        :param message:
        :param nouns: List of topics
        :param source: Channel
        :param target: Person
        :return:
        """
        return self._gen_related_sentence(nouns, source, target)

    def _nouns_in_sentence(self, message : str):
        """
        Return
        :param message:
        :return:
        """
        tokens = nltk.word_tokenize(message)
        logging.debug(f"Tokens '{tokens}'")
        nouns = list(
            map(
                lambda y: y[0],
                filter(
                    lambda x: x[1] in ["NN", "NNP", "NNS", "NNS"], nltk.pos_tag(tokens)
                ),
            )
        )
        nouns = list(map(lambda x: x.translate(self.punctuation_table), nouns))
        nouns = list(filter(lambda x: x != self.bully, nouns))
        logging.debug(f"Nouns: {nouns}")
        return nouns

    def _gen_related_sentence(self, nouns : typing.List[str], source : str, target : str):
        flag_found = False
        idx = 0
        s = ""
        heading = (
            random.choices(["", f"{target}: ", f"{target}, "], [.5, .3, .2])[0]
            if target != ""
            else ""
        )
        while True:
            idx += 1
            trial_sentence = self.model.make_sentence()
            if trial_sentence is None:
                continue
            normalized_trial_sentence = trial_sentence.lower().translate(
                self.punctuation_table
            )
            for noun in nouns:
                if noun in normalized_trial_sentence:
                    s = normalized_trial_sentence
                    self.message(source, f"{heading}{normalized_trial_sentence}")
                    logging.warning(
                        f"Found good sentence on trial {idx} matched {noun}"
                    )
                    flag_found = True
                    break
            if flag_found:
                break
            if idx > 4096:
                s = self._gen_random_sentence()
                self.message(source, f"{heading}{s}")
                break
        return s

    def _gen_random_sentence(self):
        logging.debug("Using total random one")
        sentence = self.model.make_sentence()
        while sentence is None or sentence == "None":
            sentence = self.model.make_sentence()
        return sentence

    def on_ctcp_version(self, source, target, contents):
        self.ctcp_reply(source, "VERSION", self._version_string())

    def _version_string(self):
        return f"{self.bully}BOT v{self.__version__}"
