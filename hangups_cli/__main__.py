#!/usr/bin/env python

import sys, os, logging, argparse, asyncio

import appdirs
import hangups

# Basic settings
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

class Cli(object):
    """QHangups main widget (icon in system tray)"""
    def __init__(self, refresh_token_path):
        # self.set_language()

        self.refresh_token_path = refresh_token_path
        self.hangups_running = False
        self.client = None

        self.conv_list = None  # hangups.ConversationList
        self.user_list = None  # hangups.UserList

        try:
            cookies = hangups.auth.get_auth_stdin(refresh_token_path)
        except hangups.GoogleAuthError as e:
            sys.exit('Login failed ({})'.format(e))

        self.client = hangups.Client(cookies)
        self.client.on_connect.add_observer(self.on_connect)

        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.client.connect())
        except NotImplementedError:
            pass
        finally:
            loop.close()


    @asyncio.coroutine
    def on_connect(self):
        """Handle connecting for the first time (callback)"""
        print('Connected')
        self.user_list, self.conv_list = yield from hangups.build_user_conversation_list(
            self.client
        )

        print(self.conv_list.get_all())

        self.quit()

    def quit(self):
        future = asyncio.async(self.client.disconnect())
        future.add_done_callback(lambda future: future.result())


def main():
    """ Main Function """
    # Build default paths for files.
    dirs = appdirs.AppDirs('QHangups', 'QHangups')
    default_log_path = os.path.join(dirs.user_data_dir, 'hangups.log')
    default_token_path = os.path.join(dirs.user_data_dir, 'refresh_token.txt')

    # Setup command line argument parser
    parser = argparse.ArgumentParser(prog='qhangups',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-d', '--debug', action='store_true',
                        help='log detailed debugging messages')
    parser.add_argument('--log', default=default_log_path,
                        help='log file path')
    parser.add_argument('--token', default=default_token_path,
                        help='OAuth refresh token storage path')
    args = parser.parse_args()

    # Create all necessary directories.
    for path in [args.log, args.token]:
        directory = os.path.dirname(path)
        if directory and not os.path.isdir(directory):
            try:
                os.makedirs(directory)
            except OSError as e:
                sys.exit('Failed to create directory: {}'.format(e))

    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.WARNING
    logging.basicConfig(filename=args.log, level=log_level, format=LOG_FORMAT)
    # asyncio's debugging logs are VERY noisy, so adjust the log level
    logging.getLogger('asyncio').setLevel(logging.WARNING)

    cli = Cli(args.token)


if __name__ == "__main__":
    main()
