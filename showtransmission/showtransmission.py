#!/usr/bin/env python
import os.path
import json
import logging
import string
import sys
import argparse

import feedparser
from transmission import TransmissionClient

logger = logging.getLogger("showtransmission")


class Episode(object):
    """Store each episode retrieved from ShowRSS feed"""
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
        """Convert the show name to string suitable for use in filename"""
        dir_name = self.show_name.replace(" ", "_")
        dir_name = ''.join(char for char in dir_name if char in self.VALID_FILE_CHARS)
        return dir_name


class ShowTransmissionException(Exception):
    """Used for exceptions generated from ShowTransmission object"""
    pass


class SetLogLevelAction(argparse.Action):
    """argparse action that handles setting log levels"""
    def __init__(self, *args, **kwargs):
        super(SetLogLevelAction, self).__init__(*args, **kwargs)
        self.nargs = 0

    def __call__(self, parser, namespace, values, option_string=None):
        logging.getLogger().setLevel(self.const)


class ShowTransmission(object):
    """
    Object used to download ShowRSS feed and add each new magnet link to transmission via
    transmission RPC api.
    A config file is used to store already uploaded hashes.
    TODO: Probably need to change this to be based on dates instead so the config doesn't grow too
    massive. That or track last N hashes

    """
    DEFAULT_CONFIG_LOCATION = os.path.expanduser("~/.showtransmission")

    def __init__(self):
        self.config_location = None
        self.log_level = logging.INFO
        self.rss_location = None
        self.transmission_rpc_url = None
        self.output_options = False
        self.hashes = set()

    @staticmethod
    def make_hash_set(value):
        """
        Used to create set from comma seperated hashes as passed on command line
        Used in arg parser in ShowTransmission.parse_args
        """
        hashes = set()
        for cs_hash in value.split(","):
            cs_hash.strip()
            if cs_hash:
                hashes.add(cs_hash)
        return hashes

    def parse_args(self, args=None):
        """
        Configure this ShowTransmission object by reading args.
        :param args: Arguments to pass. If not set then use sys.arv[1:]
        """
        if args is None:
            args = sys.argv[1:]

        parser = argparse.ArgumentParser(
            description=("Script to parse rss feed from ShowRSS and add to transmission via rpc.\n"
                         "Note that this script will always write to config location and will  "
                         "require the --rss-location and --transmission-rpc-url for the first run."
                         ))
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
                            help=("Location of transmission RPC URL. Usually this is "
                                  "'http://localhost:9091/transmission/rpc'"),
                            default=None)

        parser.add_argument("--output-options",
                            dest="output_options",
                            help="Show config that would be used then exit",
                            action="store_true",
                            default=False)

        parser.add_argument("--reset-hashes",
                            dest="hashes",
                            help="Reset all hashes",
                            action="store_const",
                            const=set())

        self.config_location = parser.parse_args(args).config_location
        self.try_load_config(self.config_location)
        parser.parse_args(args=args, namespace=self)
        logger.debug("Got config '%s'" % (self.make_config_json(include_hashes=False),))

    def try_load_config(self, config_path):
        """
        Try and load config from json file at config_path.
        This overwrites any config attributes already set in this instance of ShowTransmission
        """
        logger.info("Trying to load config from '%s'" % (config_path,))
        try:
            config_file = json.load(file(config_path, 'r'))
        except IOError:
            return
        self.rss_location = config_file.get("rss_location", None)
        self.transmission_rpc_url = config_file.get("transmission_rpc_url", None)
        self.hashes = set(config_file.get("hashes", []))

    def make_config_json(self, include_hashes=True):
        """Create json suitable for saving as config filei to preserve settings and hashes
        in this instance of ShowTransmission"""
        config_dict = {"rss_location": self.rss_location,
                       "transmission_rpc_url": self.transmission_rpc_url}
        if include_hashes:
            config_dict["hashes"] = list(self.hashes)
        return json.dumps(config_dict)

    def is_episode_downloaded(self, episode):
        """Check if this episode has already been added to transmission"""
        return episode.showrss_info_hash in self.hashes

    def mark_episode_downloaded(self, episode):
        """Mark an episode as downloaded"""
        self.hashes.add(episode.showrss_info_hash)

    def process(self):
        """Parse feed and add each magnet to transmission"""
        if self.output_options:
            print self.make_config_json()
            return

        logger.info("Connecting to transmission at '%s'" % (self.transmission_rpc_url))
        transmission = TransmissionClient(self.transmission_rpc_url)
        transmission.check_connection()
        transmission_download_dir = transmission.get_download_dir()

        logger.info("Parsing feed '%s'" % (self.rss_location))
        add_count = 0
        ignore_count = 0
        for feed_entry in feedparser.parse(self.rss_location)["entries"]:
            episode = Episode(feed_entry)
            if self.is_episode_downloaded(episode):
                ignore_count += 1
                logger.debug("Ignoring episode for '%s' as hash is in set" % (str(episode),))
            else:
                logger.info("Downloading '%s'" % (episode.title,))
                download_path = os.path.join(transmission_download_dir, episode.dir_name())
                transmission.add_torrent(episode.link, download_path)
                self.mark_episode_downloaded(episode)
                add_count += 1

        logger.info("Found %d feeds. %d added to transmission. %d ignored as already added." %
                    (add_count + ignore_count, add_count, ignore_count))

        logger.info("Writing config to %s" % (self.config_location))
        file(self.config_location, 'w').write(self.make_config_json())

        logger.info("Completed successfully")


def run_script(args=None):
    logging.basicConfig(level=logging.INFO)
    s = ShowTransmission()
    s.parse_args(args)
    s.process()

if __name__ == "__main__":
    run_script()
