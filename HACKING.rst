=====================
Hacking on cloud-init
=====================

To get changes into cloud-init, the process to follow is:

* Fork from github, create a branch and make your changes

  - ``git clone https://github.com/openstack/cloud-init``
  - ``cd cloud-init``
  - ``echo hack``

* Check test and code formatting / lint and address any issues:

  - ``tox``

* Commit / ammend your changes (before review, make good commit messages with
  one line summary followed by empty line followed by expanded comments).

  - ``git commit``

* Push to http://review.openstack.org:

  - ``git-review``

* Before your changes can be accepted, you must sign the `Canonical
  Contributors License Agreement`_.  Use 'Scott Moser' as the 'Project
  contact'.  To check to see if you've done this before, look for your
  name in the `Canonical Contributor Agreement Team`_ on Launchpad.

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
.. _Canonical Contributors License Agreement: http://www.ubuntu.com/legal/contributors
.. _Canonical Contributor Agreement Team: https://launchpad.net/~contributor-agreement-canonical/+members#active
