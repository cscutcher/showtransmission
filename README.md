showtransmission
================
Script to parse rss feed from ShowRSS and add to transmission via rpc.

install
-------
    python setup.py install

usage
-----
    usage: showtransmission [-h] [--debug] [--quiet] [--config CONFIG_LOCATION]
                            [--rss-location RSS_LOCATION]
                            [--transmission-rpc-url TRANSMISSION_RPC_URL]
                            [--output-options] [--reset-hashes]

    Script to parse rss feed from ShowRSS and add to transmission via rpc. Note
    that this script will always write to config location and will require the
    --rss-location and --transmission-rpc-url for the first run.

    optional arguments:
      -h, --help            show this help message and exit
      --debug, -d           Show debug messages
      --quiet, -q           Silence all but error messages
      --config CONFIG_LOCATION, -c CONFIG_LOCATION
                            Config file location. Default: ~/.showtransmission
      --rss-location RSS_LOCATION, -r RSS_LOCATION
                            Location of RSS feed for showRSS
      --transmission-rpc-url TRANSMISSION_RPC_URL, -t TRANSMISSION_RPC_URL
                            Location of transmission RPC URL. Usually this is
                            'http://localhost:9091/transmission/rpc'
      --output-options      Show config that would be used then exit
      --reset-hashes        Reset all hashes
