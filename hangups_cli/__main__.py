#!/usr/bin/env python

import sys, os, logging, argparse, asyncio

import appdirs
import hangups
from hangups.ui.utils import get_conv_name

# Basic settings
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
MESSAGE_TIME_FORMAT = '(%I:%M:%S %p)'
MESSAGE_DATETIME_FORMAT = '\n< %y-%m-%d >\n(%I:%M:%S %p)'

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
        # print('Connected')
        self.user_list, self.conv_list = yield from hangups.build_user_conversation_list(
            self.client
        )

        yield from self.print_output()

        self.quit()

    def get_conversations(self):
        convs = sorted(self.conv_list.get_all(), reverse=True, key=lambda c: c.last_modified)
        return "\n".join([str(conv.id_) + " : " + get_conv_name(conv) for conv in convs])

    @asyncio.coroutine
    def get_conversation(self, conversation_id):
        conversation = self.conv_list.get(conversation_id)
        print(get_conv_name(conversation))
        event0 = conversation._events[0]
        events = yield from conversation.get_events(event0.id_)
        events.append(event0)
        print(len(events))
        output = ""
        for event in events:
            ev = Message.from_conversation_event(conversation, event, None)
            if ev is not None:
                output += str(ev.text) + "\n"
        return output

    @asyncio.coroutine
    def print_output(self):
        output = None

        command = "get_conversations"

        if command == "get_conversations":
            output = self.get_conversations()
        elif command == 'get_conversation':
            convs = sorted(self.conv_list.get_all(), reverse=True, key=lambda c: c.last_modified)
            output = yield from self.get_conversation(convs[1].id_)

        print(output)


    def quit(self):
        future = asyncio.async(self.client.disconnect())
        future.add_done_callback(lambda future: future.result())

class Message(object):

    """Widget for displaying a single message in a conversation."""

    def __init__(self, timestamp, text, user=None, show_date=False):
        # Save the timestamp as an attribute for sorting.
        self.timestamp = timestamp
        text = [
            ('msg_date', self._get_date_str(timestamp,
                                            show_date=show_date) + ' '),
            ('msg_text', text)
        ]
        if user is not None:
            text.insert(1, ('msg_sender', user.first_name + ': '))

        self.user = user
        self.text = text


    @staticmethod
    def _get_date_str(timestamp, show_date=False):
        """Convert UTC datetime into user interface string."""
        fmt = MESSAGE_DATETIME_FORMAT if show_date else MESSAGE_TIME_FORMAT
        return timestamp.astimezone(tz=None).strftime(fmt)

    def __lt__(self, other):
        return self.timestamp < other.timestamp

    @staticmethod
    def from_conversation_event(conversation, conv_event, prev_conv_event):
        """Return MessageWidget representing a ConversationEvent.

        Returns None if the ConversationEvent does not have a widget
        representation.
        """
        user = conversation.get_user(conv_event.user_id)
        # Check whether the previous event occurred on the same day as this
        # event.
        if prev_conv_event is not None:
            is_new_day = (conv_event.timestamp.astimezone(tz=None).date() !=
                          prev_conv_event.timestamp.astimezone(tz=None).date())
        else:
            is_new_day = False
        if isinstance(conv_event, hangups.ChatMessageEvent):
            return Message(conv_event.timestamp, conv_event.text, user,
                                 show_date=is_new_day)
        elif isinstance(conv_event, hangups.RenameEvent):
            if conv_event.new_name == '':
                text = ('{} cleared the conversation name'
                        .format(user.first_name))
            else:
                text = ('{} renamed the conversation to {}'
                        .format(user.first_name, conv_event.new_name))
            return Message(conv_event.timestamp, text,
                                 show_date=is_new_day)
        elif isinstance(conv_event, hangups.MembershipChangeEvent):
            event_users = [conversation.get_user(user_id) for user_id
                           in conv_event.participant_ids]
            names = ', '.join([user.full_name for user in event_users])
            if conv_event.type_ == hangups.MEMBERSHIP_CHANGE_TYPE_JOIN:
                text = ('{} added {} to the conversation'
                        .format(user.first_name, names))
            else:  # LEAVE
                text = ('{} left the conversation'.format(names))
            return Message(conv_event.timestamp, text,
                                 show_date=is_new_day)
        else:
            return None



def main():
    """ Main Function """
    # Build default paths for files.
    dirs = appdirs.AppDirs('hangups_cli', 'hangups_cli')
    default_log_path = os.path.join(dirs.user_data_dir, 'hangups.log')
    default_token_path = os.path.join(dirs.user_data_dir, 'refresh_token.txt')

    # Setup command line argument parser
    parser = argparse.ArgumentParser(prog='hangups_cli',
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
