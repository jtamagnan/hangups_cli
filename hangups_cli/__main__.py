#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

import sys, os, logging, argparse, asyncio, argcomplete
import appdirs
import hangups
from hangups.ui.utils import get_conv_name

# Basic settings
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
MESSAGE_TIME_FORMAT = '(%I:%M:%S %p)'
MESSAGE_DATETIME_FORMAT = '< %y-%m-%d > (%I:%M:%S %p)'

class Cli(object):
    """QHangups main widget (icon in system tray)"""
    def __init__(self, refresh_token_path, conversation_path, user_path, command, optional_command):
        # self.set_language()

        self.refresh_token_path = refresh_token_path
        self.conversation_path = conversation_path
        self.user_path = user_path
        self.command = command
        self.optional_command = optional_command

        self.hangups_running = False
        self.client = None

        self.conv_list = None  # hangups.ConversationList
        self.user_list = None  # hangups.UserList

        try:
            cookies = hangups.auth.get_auth_stdin(refresh_token_path)
        except hangups.GoogleAuthError as err:
            sys.exit('Login failed ({})'.format(err))

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
        self.user_list, self.conv_list = yield from hangups.build_user_conversation_list( self.client )

        yield from self.parse_command()
        yield from self.parse_optional_command()

        self.quit()

    @asyncio.coroutine
    def parse_command(self):
        """Parse the command string"""
        if self.command[0] == 'get':
            yield from self.get(self.command[1])
        elif self.command[0] == 'send':
            yield from self.send(self.command[1], self.command[2])
        elif self.command[0] == 'all':
            yield from self.print_conversations()

    @asyncio.coroutine
    def parse_optional_command(self):
        """Parse the optional command string"""
        if "update_list" in self.optional_command:
            yield from self.save_conversations_list()

    @asyncio.coroutine
    def get(self, command):
        """Print out output from get command"""
        if command[0] == 'conversation':
            output = yield from self.get_conversation(command[1:])
            print(output)

    @asyncio.coroutine
    def send(self, to, message):
        """Send a message"""
        if to[0] == "conversation":
            yield from self.send_to_conversation(to[1], message[1])
        elif to[0] == "number":
            raise NotImplementedError("Send to number")
        elif to[0] == "user":
            raise NotImplementedError("Send to user")

    @asyncio.coroutine
    def save_conversations_list(self):
        """Save the list of conversations, useful for autocomplete"""
        with open(self.conversation_path, 'w') as conv_file:
            conv_file.write(self.get_conversations_with_id())
        with open(self.user_path, 'w') as user_file:
            user_file.write(self.get_users())

    def get_conversations_with_id(self):
        """Get the list of conversation as text"""
        convs = sorted(self.conv_list.get_all(), reverse=True, key=lambda c: c.last_modified)
        conversation_map = {}
        for conv in convs:
            value = get_conv_name(conv).replace(" ", "_")
            key = conv
            if value in conversation_map.values():
                count = 1
                while value + "_" +  str(count) in conversation_map.values():
                    count += 1
                conversation_map[key] = value + "_" + str(count)
            else:
                conversation_map[key] = value

        return "\n".join([conv.id_ + " : " + conversation_map[conv] for conv in convs])

    def print_conversations(self):
        """Get the list of conversation as text"""
        print(self.get_conversations_with_id())

    def get_users(self):
        """Get the list of users as text"""


        user_map = {}
        for user in self.user_list.get_all():
            key = user.id_
            value = user.full_name
            if key in user_map:
                count = 1
                while key + "_" +  str(count) in user_map:
                    count += 1
                user_map[key + "_" + str(count)] = value
            else:
                user_map[key] = value

        users = sorted(list(user_map.items()),
                              key=lambda x:'zzz' + x[1] if x[1][:7] == "Unknown" else x[1])

        return "\n".join([str(user[0]) + " : " + str(user[1]) for user in users])

    @asyncio.coroutine
    def get_conversation(self, get_info):
        """Get a conversation by id"""
        conversation_id = get_info[0]
        max_events = get_info[1]
        conversation = self.conv_list.get(conversation_id)
        event0 = conversation._events[0]
        events = yield from conversation.get_events(event0.id_, max_events)
        events.append(event0)
        output = ""
        for event in events:
            ev = Message.from_conversation_event(conversation, event, None)
            if ev is not None:
                output += str(ev) + "\n"
        return output

    @asyncio.coroutine
    def send_to_conversation(self, conversation_id, text):
        """Called when the user presses return on the send message widget."""
        conversation = self.conv_list.get(conversation_id)
        # Ignore if the user hasn't typed a message.
        if len(text) == 0:
            return
        elif text.startswith('/image') and len(text.split(' ')) == 2:
            # Temporary UI for testing image uploads
            filename = text.split(' ')[1]
            image_file = open(filename, 'rb')
            text = ''
        else:
            image_file = None
        # XXX: Exception handling here is still a bit broken. Uncaught
        # exceptions in _on_message_sent will only be logged.
        segments = hangups.ChatMessageSegment.from_str(text)

        yield from conversation.send_message(segments, image_file=image_file)

    def _on_message_sent(self, future):
        """Handle showing an error if a message fails to send."""
        try:
            future.result()
        except hangups.NetworkError:
            raise Exception('Failed to send message')


    def quit(self):
        """Quit out of the cli"""
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

    def __str__(self):
        output = "{} | {:10} | {}".format(self._get_date_str(self.timestamp, show_date=True),
                   self.text[1][1], self.text[2][1])
        return output

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

def one(*args):
    """Return true if only one arg is None false otherwise"""
    return 1 == sum([x is not None for x in args])

def main():
    """ Main Function """
    # Build default paths for files.
    dirs = appdirs.AppDirs('hangups_cli', 'hangups_cli')
    default_log_path = os.path.join(dirs.user_data_dir, 'hangups.log')
    default_token_path = os.path.join(dirs.user_data_dir, 'refresh_token.txt')
    conversation_path = os.path.join(dirs.user_data_dir, 'conversation_list.txt')
    user_path = os.path.join(dirs.user_data_dir, 'user_list.txt')

    conversation_map = {}
    try:
        with open(conversation_path, 'r') as conv_file:
            for line in conv_file.readlines():
                split = line.split(':')
                key = split[1].strip().replace(" ", "_")
                value = split[0].strip()
                conversation_map[key] = value
    except FileNotFoundError as err:
        pass

    user_map = {}
    try:
        with open(user_path, 'r') as user_file:
            for line in user_file.readlines():
                split = line.split(':')
                key = split[1].strip().replace(" ", "_")
                value = split[0].strip()
                user_map[key] = value
    except FileNotFoundError as err:
        pass

    conversation_choices = sorted(list(conversation_map.keys()),
                                  key=lambda x:'zzz' + x if x[:7] == "Unknown" else x)
    user_choices = sorted(list(user_map.keys()),
                          key=lambda x:'zzz' + x if x[:7] == "Unknown" else x)

    # Setup command line argument parser
    parser = argparse.ArgumentParser(prog='hangups_cli',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.set_defaults(which='None')


    subparsers = parser.add_subparsers(help="sub-command help")

    send_message = subparsers.add_parser("send", help="Send Message")
    send_message.set_defaults(which='send')

    choice = send_message.add_argument_group("Choose one sending medium")
    choice.add_argument("-c", '--conversation', choices=conversation_choices,
                        help="Which Conversation To Message",
                        metavar="Conversation")
    choice.add_argument('-u', '--user', choices=user_choices,
                        help="Which User To Message",
                        metavar="User")
    choice.add_argument("-n", '--number',
                        help="Which phone number To Message",
                        metavar="Number")
    required = send_message.add_argument_group("Required")
    required.add_argument('-m', '--message', help="The message to send", required=True)


    get_message = subparsers.add_parser("get", help="Get Messages")
    get_message.set_defaults(which='get')
    get_message.add_argument('-n', '--number', help="Number of texts to get", default=50, type=int)
    required = get_message.add_argument_group("Required")
    required.add_argument("-c", '--conversation', choices=conversation_choices,
                          help="Which Conversation To Read",
                          metavar="Conversation", required=True)


    parser.add_argument('-d', '--debug', action='store_true',
                        help='log detailed debugging messages')
    parser.add_argument('-U', '--update', action='store_false',
                        help='Do not refresh stored conversation list')
    parser.add_argument('--log', default=default_log_path,
                        help='log file path')


    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    # print(args)

    command = []
    if args.which == 'send':
        command.append('send')
        if one([args.number, args.user, args.conversation]):
            if args.number:
                command.append(['number', args.number])
            elif args.user:
                command.append(['user', user_map[args.user]])
            elif args.conversation:
                command.append(['conversation', conversation_map[args.conversation]])
        else:
            raise argparse.ArgumentError('Only one option can be chosen')
        command.append(['message', args.message])
    elif args.which == 'get':
        command.append('get')
        command.append(['conversation', conversation_map[args.conversation], args.number])
    else:
        command.append(['all'])

    optional_command = set()
    if args.update is not None:
        optional_command.add("update_list")

    # print(command)

    # Create all necessary directories.
    for path in [args.log, default_token_path, conversation_path, user_path]:
        directory = os.path.dirname(path)
        if directory and not os.path.isdir(directory):
            try:
                os.makedirs(directory)
            except OSError as err:
                sys.exit('Failed to create directory: {}'.format(err))

    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.WARNING
    logging.basicConfig(filename=args.log, level=log_level, format=LOG_FORMAT)
    # asyncio's debugging logs are VERY noisy, so adjust the log level
    logging.getLogger('asyncio').setLevel(logging.WARNING)

    unused_cli = Cli(default_token_path, conversation_path, user_path, command, optional_command)

if __name__ == "__main__":
    main()
