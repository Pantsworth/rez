============
Installation
============

Installation Script
===================

.. warning::
   The install script only supports Python 3.7+.

To install rez, download the source. Then from the root directory, run::

   ]$ python ./install.py

This installs rez to ``/opt/rez``. See ```install.py -h``` for how to install to a
different location.

Once the installation is complete, a message tells you how to run it::

   SUCCESS! To activate Rez, add the following path to $PATH:
   /opt/rez/bin/rez

   You may also want to source the completion script (for bash):
   source /opt/rez/completion/complete.sh


.. warning::
   Do **not** move the installation. Re-install to a new location if you want to change
   the install path. If you want to install rez for multiple operating systems,
   perform separate installs for each of those systems.


Installation via pip
====================

It is possible to install rez with pip, like so::

   ]$ pip install rez

.. note::
   While the ``install.py`` script only supports Python 3.7+,
   rez is still usable with Python 2.7 when installed via pip. In other words, the API
   is fully compatible with Python 2 and 3.

However, this comes with a caveat. Rez command line tools **are not guaranteed
to work correctly** once inside a rez environment (ie after using the :ref:`rez-env`
command). The reasons are given in the next section.

Pip installation is adequate however, if all you require is the rez API, or you
don't require its command line tools to be available within a resolved environment.

.. note::
   that running pip-installed rez command line tools will print a warning like so:

   .. code-block:: text

      Pip-based rez installation detected. Please be aware that rez command line tools
      are not guaranteed to function correctly in this case. See :ref:`why-not-pip-for-production`
      for further details.

.. _why-not-pip-for-production:

Why Not Pip For Production?
===========================

Rez is not a normal python package. Although it can successfully be installed
using standard mechanisms such as pip, this comes with a number of caveats.
Specifically:

* When within a rez environment (ie after using the :ref:`rez-env` command), the rez
  command line tools are not guaranteed to function correctly;
* When within a rez environment, other packages' tools (that were also installed
  with pip) remain visible, but are not guaranteed to work.

When you enter a rez environment, the rez packages in the resolve configure
that environment as they see fit. For example, it is not uncommon for a python
package to append to :envvar:`PYTHONPATH`. Environment variables such as :envvar:`PYTHONPATH`
affect the behaviour of tools, including rez itself, and this can cause it to
crash or behave abnormally.

When you use the ``install.py`` script to install rez, some extra steps are taken
to avoid this problem. Specifically:

* Rez is installed into a virtualenv so that it operates standalone;
* The rez tools are shebanged with ``python -E``, in order to protect them from
  environment variables that affect python's behaviour;
* The rez tools are stored in their own directory, so that other unrelated tools
  are not visible.

Due to the way standard wheel-based python installations work, it simply is not
possible to perform these extra steps without using a custom installation script.
Wheels do not give the opportunity to run post-installation code. Neither do
they provide functionality for specifying interpreter arguments to be added for
any given entry point.
