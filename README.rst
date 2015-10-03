hangups_cli
===========

hangups_cli aims to provide a simple command line interface to
`hangups <https://github.com/tdryer/hangups>`_. Its goal is to
implement as many features as possible from the hangups api into a
command line tool.

Installation
------------

hangups_cli is not yet on pypi and can only be installed from source

::
   $ pythons setup.py install

Auto complete
^^^^^^^^^^^^^

hangups_cli supports autocompletion of conversation names for both
sending and recieving messages.

After having installed hangups_cli as described above the directions
outline `here
<https://github.com/kislyuk/argcomplete#activating-global-completion>`_

Auto complete options will only appear after running the program an
intial time

::
   $ hangups_cli



Disclaimer
----------

This software is still very much a work in progress; I have plans: to
implement more features, clean up the code, create an emacs
mode. Please bare with me and don't forget to report any issues.
