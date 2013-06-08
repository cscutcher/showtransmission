#!/usr/bin/env python
import os.path
import json
import logging
import string
import sys
import argparse

import feedparser
from magicargumentparser import MagicArgumentParser
from transmission import TransmissionClient

logger = logging.getLogger("showtransmission")



class Episode(object):
    def __init__(self, feed_entry):
        self.published = feed_entry["published_parsed"]
        self.link = feed_entry["link"]
        self.episode = feed_entry["showrss_episode"]
        self.showrss_info_hash = feed_entry["showrss_info_hash"]
        self.show_name = feed_entry["showrss_showname"]
        self.show_id = feed_entry["showrss_showid"]
        self.title = feed_entry["title"]
        self.feed_entry = feed_entry

    def __str__(self):
        return self.title

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, repr(self.feed_entry))

    VALID_FILE_CHARS = "-_.() %s%s" % (string.ascii_letters, string.digits)

    def dir_name(self):
        dir_name = self.show_name.replace(" ", "_")
        dir_name = ''.join(char for char in dir_name if char in self.VALID_FILE_CHARS)
        return dir_name


class ShowTransmissionException(Exception):
    pass


class SetLogLevelAction(argparse.Action):
    def __init__(self, *args, **kwargs):
        super(SetLogLevelAction, self).__init__(*args, **kwargs)
        self.nargs = 0

    def __call__(self, parser, namespace, values, option_string=None):
        logging.getLogger().setLevel(self.const)

class ShowTransmission(object):
    DEFAULT_CONFIG_LOCATION = os.path.expanduser("~/.showtransmission")
    def __init__(self):
        self.config_location = None
        self.log_level = logging.INFO
        self.rss_location = None
        self.transmission_rpc_url = None
        self.output_options = False
        self.write_config = False
        self.hashes = set()

    @staticmethod
    def make_hash_set(value):
        hashes = set()
        for cs_hash in value.split(","):
            cs_hash.strip()
            if cs_hash:
                hashes.add(cs_hash)
        return hashes

    def parse_args(self, args=None):
        if args is None:
            args = sys.argv[1:]

        parser = argparse.ArgumentParser(
            description="Automates downloading torrents from showrss")
        parser.add_argument("--debug", "-d",
                            dest="log_level",
                            help="Show debug messages",
                            action=SetLogLevelAction,
                            const=logging.DEBUG)
        parser.add_argument("--quiet", "-q",
                            dest="log_level",
                            help="Silence all but error messages",
                            action=SetLogLevelAction,
                            const=logging.ERROR)
        parser.add_argument("--config", "-c",
                            dest="config_location",
                            default=self.DEFAULT_CONFIG_LOCATION,
                            help=("Config file location. Default: %s" %
                                    (self.DEFAULT_CONFIG_LOCATION,)))

        parser.add_argument("--rss-location", "-r",
                            dest="rss_location",
                            help="Location of RSS feed for showRSS")
        parser.add_argument("--transmission-rpc-url", "-t",
                            dest="transmission_rpc_url",
                            help=("Location of transmission RPC URL"),
                            default=None)

        parser.add_argument("--output-options",
                            dest="output_options",
                            help="Show config that would be used then exit",
                            action="store_true",
                            default=False)

        parser.add_argument("--write-config",
                            dest="write_config",
                            help="Write new config to config path when done",
                            action="store_true",
                            default=False)

        self.try_load_config(parser.parse_args(args).config_location)
        parser.parse_args(args=args, namespace=self)

    def try_load_config(self, config_path):
        try:
            config_file = json.load(file(config_path, 'r'))
        except IOError:
            return
        self.rss_location = config_file.get("rss_location", None)
        self.transmission_rpc_url = config_file.get("transmission_rpc_url", None)
        self.hashes = set(config_file.get("hashes", []))


    def make_config_dict(self, include_hashes=True):
        config_dict = {"rss_location": self.rss_location,
                       "transmission_rpc_url": self.transmission_rpc_url}
        if include_hashes:
            config_dict["hashes"] = list(self.hashes)
        return config_dict

    def make_config_json(self, include_hashes=True):
        return json.dumps(self.make_config_dict(include_hashes=include_hashes))

    def process(self):
        """Parse feed and add each magnet to transmission"""
        if self.output_options:
            print self.make_config_json()
            return

        episodes = []
        logger.info("Connecting to transmission at '%s'" % (self.transmission_rpc_url))
        transmission = TransmissionClient(self.transmission_rpc_url)
        transmission.check_connection()
        transmission_download_dir = transmission.get_download_dir()

        logger.info("Parsing feed '%s'" % (self.rss_location))
        for feed_entry in feedparser.parse(self.rss_location)["entries"]:
            episode = Episode(feed_entry)
            if episode.showrss_info_hash not in self.hashes:
                logger.info("Downloading '%s'" % (episode.title,))
                download_path = os.path.join(transmission_download_dir, episode.dir_name())
                transmission.add_torrent(episode.link, download_path)
                self.hashes.add(episode.showrss_info_hash)
            else:
                logger.debug("Ignoring episode for '%s' as hash is in set" % (str(episode),))


        if self.write_config:
            file(self.config_location, 'w').write(self.make_config_json())

def run_script(args=None):
    logging.basicConfig()
    s = ShowTransmission()
    s.parse_args(args)
    s.process()

if __name__ == "__main__":
    run_script()
