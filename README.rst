Cloud-init
==========

*Cloud-init initializes systems for cloud environments.*

Join us
-------

- http://launchpad.net/cloud-init

Testing and requirements
------------------------

Requirements
~~~~~~~~~~~~

TBD

Tox.ini
~~~~~~~

Our ``tox.ini`` file describes several test environments that allow to test
cloud-init with different python versions and sets of requirements installed.
Please refer to the `tox`_ documentation to understand how to make these test
environments work for you.

Developer documentation
-----------------------

We also have sphinx documentation in ``docs/source``.

*To build it, run:*

::

    $ python setup.py build_sphinx

.. _tox: http://tox.testrun.org/
