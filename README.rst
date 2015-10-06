hangups_cli
===========

hangups_cli aims to provide a simple command line interface to
`hangups <https://github.com/tdryer/hangups>`_. Its goal is to
implement as many features as possible from the hangups api into a
command line tool.

It allows for messaging and texting through hangouts and google voice
respectively

Installation
------------

hangups_cli is not yet on pypi and can only be installed from source

.. code-block:: bash

   $ python setup.py install

Auto complete
^^^^^^^^^^^^^

hangups_cli supports tab autocompletion of conversation names for both
sending and recieving messages.

After having installed hangups_cli as described above the directions
outline `here
<https://github.com/kislyuk/argcomplete#activating-global-completion>`_

Auto complete options will only appear after running the program an
intial time

.. code-block:: bash

   $ hangups_cli

Emacs Mode
----------

There is an emacs mode that uses hangups_cli. After having installed
hangups_cli (Autocomplete not needed) go to and install which is not
yet on melpa `hangups.el <http://github.com/jtamagnan/hangups.el>`_

I try and keep both up to date. Right now hangups.el can load the
conversation list, read messages from a conversation and send messages
to a conversation.

Disclaimer
----------

This software is still very much a work in progress; I have plans: to
implement more features, clean up the code. Please bare with me and
don't forget to report any issues.
