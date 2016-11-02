Cloud-init
==========

**Note**: This is a "version 2" branch of cloud-init, that has laid idle
for some time.  To contribute to active cloud-init series, see
  https://git.launchpad.net/cloud-init/tree/HACKING.rst


*Cloud-init initializes systems for cloud environments.*

Join us
-------

- http://launchpad.net/cloud-init


Bugs
----
Bug reports should be opened at
  https://bugs.launchpad.net/cloud-init/+filebug

On Ubuntu Systems, you can file bugs with:

::

  $ ubuntu-bug cloud-init

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
