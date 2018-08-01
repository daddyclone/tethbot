from unittest import TestCase
from markov_bot import TethBot
from bot_command import parse_privmsg
import unittest.mock


class TestParse_privmsg(TestCase):

    def test_parse_privmsg_trigger(self):
        client = TethBot("test", bot_password="hello")
        client.message = unittest.mock.MagicMock()
        parse_privmsg(client, "nigger", "nibbler", "hello trigger all")
        # print(client.message.mock_calls)

    def test_parse_privmsg_help(self):
        client = TethBot("test", bot_password="hello")
        client.message = unittest.mock.MagicMock()
        parse_privmsg(client, "nigger", "nibbler", "hello -h")
        # print(client.message.mock_calls)
