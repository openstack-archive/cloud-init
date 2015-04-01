=====================
Hacking on cloud-init
=====================

To get changes into cloud-init, the process to follow is:

* Fork from github, create a branch and make your changes

  - ``git clone https://github.com/stackforge/cloud-init``
  - ``cd cloud-init``
  - ``echo hack``

* Check test and code formatting / lint and address any issues:

  - ``tox``

* Commit / ammend your changes (before review, make good commit messages with
  one line summary followed by empty line followed by expanded comments).

  - ``git commit``

* Push to branch to http://review.openstack.org:

  - ``git-review``

Then be patient and wait (or ping someone on cloud-init team).

* `Core reviewers/maintainers`_

Remember the more you are involved in the project the more beneficial it is
for everyone involved (including yourself).

**Contacting us:**

Feel free to ping the folks listed above and/or join ``#cloud-init`` on
`freenode`_ (`IRC`_) if you have any questions.

.. _Core reviewers/maintainers: https://review.openstack.org/#/admin/groups/665,members
.. _IRC: irc://chat.freenode.net/cloud-init
.. _freenode: http://freenode.net/
