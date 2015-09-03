Parallel metadata discovery and parallel config modules execution
=================================================================

This document tries to outline a couple of architectural
changes in order to support parallelization of the data source's
discovery and running config modules in parallel.
Since the same situation can be applied to both cloud-init
and cloudbase-init, whenever cloud-init V2 is mentioned,
it can be considered that the same changes applies to both
projects.


Motivation
----------


Currently, cloud-init and cloudbase-init are using the first
data source that can be loaded. This is a reasonable approach
if there aren't too many data sources and if the time to detect
that one data source can be used or not is low enough.
The current situation can be improved by parallelizing the discovery,
especially if the wanted data source is the last one that will be checked
and if each data source verification takes a couple of seconds. For instance,
this is not the case when discovering the HTTP OpenStack data source with cloudbase-init,
which can take up to two minutes.

The same principle can be applied to the execution of the
config modules (plugins in cloudbaseinit's parlance). If the data sources
can be discovered in parallel, the same can be said about config modules,
they can be executed in parallel. But these two paradigm changes implies
more than just running a process or a thread pool, since the following
questions need to be answered by our architecture:

   * what happens if a config modules depend on the execution of another
     before it can actually run?

   * the first data source that was loaded, even with the parallel discovery,
     will still be used, even though there are data sources that exports
     more information that can be used?

   * how the config modules will be executed, with regard to config module
     interdependency and dependencies between config modules and the
     data source they're expecting to use?


Architectural changes
---------------------

Capabilities
^^^^^^^^^^^^

An interesting thing about each kind of data source is the exported
metadata, which in turn composes the Python API through which the said
metadata can be used. Each data source is exporting one or more
similar APIs:

   * retrieving the instance id

   * getting the hostname

   * getting the public keys

   * etc

In a sense, these APIs are nothing more than the *capabilities* of that
data source, each data source being more capable than another one if it
exports more API methods.
For instance, the HTTP OpenStack data source supports password posting,
while other data sources don't have this capability.

The same principle is also applied to config modules, they're using
a particular set of a data source's API, which means they are using
some or most of the data source's capabilities. If the data source it operates
with doesn't have a capability or another, then the config module might not
actually run or not function properly. This leads to the fact that each
config modules needs a set of capabilities from the data source. In some cases,
only a part of this set is actually used, as it is the case the cloudbaseinit's
plugin that sets the user password. It needs a way to retrieve the password that
was set into the metadata (thus an admin password capability) and after it
changes the password of the user, it tries to post it to the data source
API, but the plugin itself does not fail if the used data source doesn't
provide the capability in question.

This leads us to two concepts:

   * specify the capabilities of the each data source.

     This can be done declaratively, by attaching an enum of capabilities
     to each data source.

   * specify for each config module what capabilities are needed
     and what capabilities are required.


As an attemptive API, declaring the capabilities for a data source
might look like this:

.. code-block:: python

   from cloudinit import capability

   class DataSource(BaseDataSource):

      capabilities = (
          capability.PUBLIC_KEYS,
          capability.USER_DATA,
          capability.INSTANCE_ID,
          ...
      )


As an alternative, we could infer the capabilities from the methods
that a data source class defines. The problem with this approach is that
then we'll have to look through the methods of a class and the methods
of its ancestors in order to determine its capabilities.

The capabilities for the config modules can be defined with the
same API, with the distinction that we'll need to declare two types of
capabilities, all the capabilities that a config module can use
and all the capabilities that it absolutely needs.


Strategies
^^^^^^^^^^

cloudinit V2 uses a new concept called *search strategy*
for discovering a potential data source. The search strategies
are classes whose purpose is to select one or more data sources
from a data source stream (any iterable).

We could detect before executing the config modules what
capabilities are needed. With this information, we could use
a new search strategy for selecting the most suitable data source
for our current run. A nice side effect of this is that if the
config modules that we need to execute don't need a data source
capability at all, then we don't need to load them.

The strategies aren't limited to filtering, they can be used to
load the data sources as well, which is already done
by ``cloudinit.sources.strategy.SerialSearchStrategy``. The parallel
discovery can be implemented into a new strategy,
called ``cloudinit.sources.strategy.ParallelSearchStrategy``.

The combination between parallel discovery and the capabilities
leads to an interesting concept, the ability to use multiple
data sources in a run. This is useful because we can already
start executing config modules before discovering all the data sources,
as long as the available data source has the capabilities
required to run the aforementioned config modules.
The rest of the config modules can be executed as soon as a data
source capable for them is available.

The technical problem is that ``cloudinit.sources.base.get_data_source``
is expected to return only one data source, not a collection of them.
We can alleviate this with the following:

  * define a strategy that does only parallel discovery, using
    processes or whatever technique we're going to choose.
    Instead of returning the first data source that's available
    (the first data source for which ``source.load`` returns True),
    we're going to return something similar to `concurrent.futures.as_completed`_,
    an iterator which yields available data sources, as soon as the underlying
    *future* finishes, where the *future* will be the unit belonging to the
    parallel mechanism (a thread, a process, a promise, a coroutine etc).

    As a proof of concept, the new strategy can look like this.
    It uses the ``concurrent.futures`` builtin modules, which has a backport
    for Python 2 called ``futures``.

    .. code-block:: python
       import concurrent.futures as futures

       class ParallelSearchStrategy(strategy.BaseSearchStrategy):

           def search_data_sources(self, data_sources):
                with futures.ProcessPoolExecutor() as executor:
                    futures = executor.map(self._is_available, data_sources)
                    for future in futures.as_completed(futures):
                        result = future.result()
                        if result:
                            # _is_available can return the data source if it's available
                            yield result

  * subclass the aforementioned strategy and wrap its result with a custom
    facade class. The class will simply hold the available data sources
    and each time a config module tries to access a capability, the facade
    object will delegate to the appropiate underlying data source.
    The API for this facade object is yet to be defined.

    As a proof of concept, the strategy can look like this:

    .. code-block:: python

       class FacadaParallelSearch(ParallelSearchStrategy):

           def search_data_sources(self, data_sources):
               sources = super(ProxyParallelSearch, self).search_data_sources(data_sources)
               yield FacadeDataSource(sources)


Config module dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^

As mentioned earlier, the config modules can have dependencies between them.
As an example, in cloudbaseinit there are two plugins for handling an user,
`createuser`, which creates an user and `setuserpassword`, which updates the
password of the created user. Since their behaviour is splitted, one can
be used without the other, for instance, `setuserpassword` can be used to
set the password of an user that was already created, so there won't
be a need to run `createuser` anymore. The problem with them is that
there is an intrinsic dependency between `createuser` and `setuserpassword`,
in the sense that `setuserpassword` can't run before `createuser`, if they
are operating on the same datum.

A parallel execution of the plugins / config modules implies a way to
solve such dependencies before running them. There are multiple ways
to do so:

   * add each plugin into priority groups, so that the config modules
     with the highest priority will run first (something that SystemV does).
     This means to have a map between a config module and its priority,
     map which will be inspected when trying to run the config module.

     As an example, it might look like this:

     .. code-block:: python

         PRIORITIES = {'create_user': 0,

                       'set_hostname': 1,

                       ...}

   * declare for each config module the plugins that need to be
     executed first. This means that the dependencies need to be
     solved dynamically at runtime.

     .. code-block:: python

         @depends_on('create_user', ...)
         class SetUserPasswordConfig(BaseConfig):


Each solution has its drawbacks. The first one implies a place with
all the config modules and their priority, while the second one implies
implicit knowledge into a config module regarding other config modules.
These "drawbacks" might not be as serious as it sounds, but it's better
to know beforehand what each solution will bring to the table before
implementing it.

Another point that we need to address with regard to config module
dependencies is represented by the fact that the config modules
have dependencies on the data source's capabilities as well,
which leads to our next point in this proposal spec.

Putting it all together
^^^^^^^^^^^^^^^^^^^^^^^

To recap what went so far:

   * bring the concept of *capabilities* to data sources and config modules

   * implement two (three) strategies, one for choosing data sources
     according to the needed capabilities, another one for parallel discovery
     of the data sources. A third strategy will be one that wraps the result
     from the parallel discovery strategy into a facade object, which contains
     the data sources that can be operated upon by the config modules, as soon
     as any data sources is available.

   * declare dependencies between config modules using a syntax we're going to
     choose.

The final point is represented by the mechanism which ties all of these together.
At this point, we have two design choices that can be made:

   * run everything in two steps. In the first step, discover the data sources
     in parallel. In the second step, after the first one finished, run in parallel
     the config modules which needs to be executed at this stage, after solving
     their dependencies.

   * run everything in one step. Start discovering data sources in parallel
     and as soon one of them is available, run the config modules that can operate
     with it. After another more capable data source is available, run the config
     modules that depends on it and so on.

     (As a note, this will be the approach that cloudbaseinit is going to
      experiment with)

The first one is simpler to implement, but it can lack in the speed department,
where as the second approach is more complex and could be tricky to implement,
but it can scale to a big number of possible data sources and config modules to execute.
The second approach also implies a central piece of code that manipulates both
data sources and config modules, knowing how to handle config modules per stage and
how to solve dependencies at runtime and so on. In a sense, this can be viewed
as the event loop of cloud-init V2.


.. _concurrent.futures.as_completed: https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures.as_completed
