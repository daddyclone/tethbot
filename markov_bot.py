import logging
import random
import re
import string
import collections

import nltk
import pydle
import crazy_text


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
        self.line_counter = collections.Counter()
        self.mention_count = collections.Counter()
        self.word_split_pattern = re.compile(r"\s+")
        self.punctuation_table = str.maketrans(dict.fromkeys(string.punctuation))
        self.startup_channels = kwargs.get("channels", [])
        self.model = kwargs.get("model", None)
        self.bully = kwargs.get("bully", "teth")
        self.ignore_nicks = kwargs.get("ignore_nicks", [])
        self.bot_password = kwargs.get("bot_password", "nigger6")
        logging.info(f"Channels {self.startup_channels}")
        super(pydle.Client, self).__init__(*args, **kwargs)

    @pydle.coroutine
    def on_connect(self):
        logging.info(f" In connect and my channels are {self.startup_channels}")
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
        logging.info("Timers.")

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

    # @pydle.coroutine
    # def on_join(self, channel, nick):
    #     if self.is_same_nick(self.nickname, nick):
    #         self.eventloop.schedule(
    #             lambda: self.message(channel, self._gen_random_sentence())
    #         )

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

        # public message
        logging.info(
            f"Lines since Blog {self.line_counter[source]}, Mentions: {self.mention_count[source]}"
        )
        try:
            self.line_counter[source] += 1
            lcm = message.lower()
            is_mentioned = self.bully in lcm and f".{self.bully}" not in lcm
            if is_mentioned:
                self.mention_count[source] += 1
            if (
                self.line_counter[source] % 20 == 0
                or (is_mentioned and self.mention_count[source] % 5 == 0)
                or f"!{self.bully}" in lcm
            ):
                self.line_counter[source] = 0
                self.mention_count[source] = 0

                self.eventloop.schedule(self._blog_task, message, source, target)
        except:
            logging.exception("some gay shit")

    def _blog_task(self, message, source, target):
        # Try to generate one based on context...
        # Search for a few seconds, if nothing is found, just use a random quip.
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

    def _search(self, message, nouns, source, target):
        return self._gen_related_sentence(nouns, source, target)

    def _nouns_in_sentence(self, message):
        tokens = nltk.word_tokenize(message)
        logging.info(f"Tokens '{tokens}'")
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
        logging.info(f"Nouns: {nouns}")
        return nouns

    def _gen_related_sentence(self, nouns, source, target):
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
        logging.warning("Using total random one")
        sentence = self.model.make_sentence()
        while sentence is None or sentence == "None":
            sentence = self.model.make_sentence()
        return sentence

    def on_ctcp_version(self, source, target, contents):
        self.ctcp_reply(source, "VERSION", self._version_string())

    def _version_string(self):
        return f"{self.bully}BOT v{self.__version__}"
