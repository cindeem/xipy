"""Experimental code for cleaner support of IPython syntax with unittest.

In IPython up until 0.10, we've used very hacked up nose machinery for running
tests with IPython special syntax, and this has proved to be extremely slow.
This module provides decorators to try a different approach, stemming from a
conversation Brian and I (FP) had about this problem Sept/09.

The goal is to be able to easily write simple functions that can be seen by
unittest as tests, and ultimately for these to support doctests with full
IPython syntax.  Nose already offers this based on naming conventions and our
hackish plugins, but we are seeking to move away from nose dependencies if
possible.

This module follows a different approach, based on decorators.

- An @as_unittest decorator can be used to tag any normal parameter-less
  function as a unittest TestCase.  Then, both nose and normal unittest will
  recognize it as such.

- A decorator called @ipdoctest can mark any function as having a docstring
  that should be viewed as a doctest, but after syntax conversion.


Authors
-------

- Fernando Perez <Fernando.Perez@berkeley.edu>
"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2009  The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------


#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import doctest
import re
import unittest

from compiler.consts import CO_GENERATOR
from doctest import DocTestFinder, DocTestRunner

#-----------------------------------------------------------------------------
# nose monkeypatch, remove later
#-----------------------------------------------------------------------------
if 1:

    def getTestCaseNames(self, testCaseClass):
        """Override to select with selector, unless
        config.getTestCaseNamesCompat is True
        """
        if self.config.getTestCaseNamesCompat:
            return unittest.TestLoader.getTestCaseNames(self, testCaseClass)
        
        def wanted(attr, cls=testCaseClass, sel=self.selector):
            item = getattr(cls, attr, None)
            # MONKEYPATCH: replace this:
            #if not ismethod(item):
            # With:
            if not hasattr(item, '__call__'):
            # END MONKEYPATCH
                return False
            return sel.wantMethod(item)
        cases = filter(wanted, dir(testCaseClass))
        for base in testCaseClass.__bases__:
            for case in self.getTestCaseNames(base):
                if case not in cases:
                    cases.append(case)
        # add runTest if nothing else picked
        if not cases and hasattr(testCaseClass, 'runTest'):
            cases = ['runTest']
        if self.sortTestMethodsUsing:
            cases.sort(self.sortTestMethodsUsing)
        return cases

    import nose.loader
    nose.loader.TestLoader.getTestCaseNames = getTestCaseNames


#-----------------------------------------------------------------------------
# Classes and functions
#-----------------------------------------------------------------------------

# Simple example of the basic idea
def as_unittest(func):
    """Decorator to make a simple function into a normal test via unittest."""
    class Tester(unittest.TestCase):
        def test(self):
            func()

    Tester.__name__ = func.func_name

    return Tester


def isgenerator(func):
    try:
        return func.func_code.co_flags & CO_GENERATOR != 0
    except AttributeError:
        return False


class ParametricTestCase(unittest.TestCase):
    """Write parametric tests in normal unittest testcase form.

    Limitations: the last iteration misses printing out a newline when running
    in verbose mode.
    """
    def run_parametric(self, result, testMethod):
        # But if we have a test generator, we iterate it ourselves
        testgen = testMethod()
        while True:
            try:
                # Initialize test
                result.startTest(self)

                # SetUp
                try:
                    self.setUp()
                except KeyboardInterrupt:
                    raise
                except:
                    result.addError(self, self._exc_info())
                    return
                # Test execution
                ok = False
                try:
                    testgen.next()
                    ok = True
                except StopIteration:
                    # We stop the loop
                    break
                except self.failureException:
                    result.addFailure(self, self._exc_info())
                except KeyboardInterrupt:
                    raise
                except:
                    result.addError(self, self._exc_info())
                # TearDown
                try:
                    self.tearDown()
                except KeyboardInterrupt:
                    raise
                except:
                    result.addError(self, self._exc_info())
                    ok = False
                if ok: result.addSuccess(self)
                
            finally:
                result.stopTest(self)

    def run(self, result=None):
        if result is None:
            result = self.defaultTestResult()
        testMethod = getattr(self, self._testMethodName)
        # For normal tests, we just call the base class and return that
        if isgenerator(testMethod):
            return self.run_parametric(result, testMethod)
        else:
            return super(ParametricTestCase, self).run(result)


def parametric(func):
    """Decorator to make a simple function into a normal test via unittest."""
    class Tester(ParametricTestCase):
        test = staticmethod(func)

    Tester.__name__ = func.func_name

    return Tester


def count_failures(runner):
    """Count number of failures in a doctest runner.

    Code modeled after the summarize() method in doctest.
    """
    try:
        from doctest import TestResults
    except:
        from _doctest26 import TestResults

    return [TestResults(f, t) for f, t in runner._name2ft.values() if f > 0 ]


class IPython2PythonConverter(object):
    """Convert IPython 'syntax' to valid Python.

    Eventually this code may grow to be the full IPython syntax conversion
    implementation, but for now it only does prompt convertion."""
    
    def __init__(self):
        self.ps1 = re.compile(r'In\ \[\d+\]: ')
        self.ps2 = re.compile(r'\ \ \ \.\.\.+: ')
        self.out = re.compile(r'Out\[\d+\]: \s*?\n?')

    def __call__(self, ds):
        """Convert IPython prompts to python ones in a string."""
        pyps1 = '>>> '
        pyps2 = '... '
        pyout = ''

        dnew = ds
        dnew = self.ps1.sub('>>> ', dnew)
        dnew = self.ps2.sub('... ', dnew)
        dnew = self.out.sub('', dnew)
        return dnew


class Doc2UnitTester(object):
    """Class whose instances act as a decorator for docstring testing.

    In practice we're only likely to need one instance ever, made below (though
    no attempt is made at turning it into a singleton, there is no need for
    that).
    """
    def __init__(self, verbose=False):
        """New decorator.

        Parameters
        ----------

        verbose : boolean, optional (False)
          Passed to the doctest finder and runner to control verbosity.
        """
        self.verbose = verbose
        # We can reuse the same finder for all instances
        self.finder = DocTestFinder(verbose=verbose, recurse=False)

    def __call__(self, func):
        """Use as a decorator: doctest a function's docstring as a unittest.
        
        This version runs normal doctests, but the idea is to make it later run
        ipython syntax instead."""

        # Capture the enclosing instance with a different name, so the new
        # class below can see it without confusion regarding its own 'self'
        # that will point to the test instance at runtime
        d2u = self

        # Rewrite the function's docstring to have python syntax
        if func.__doc__ is not None:
            func.__doc__ = ip2py(func.__doc__)

        # Now, create a tester object that is a real unittest instance, so
        # normal unittest machinery (or Nose, or Trial) can find it.
        class Tester(unittest.TestCase):
            def test(self):
                # Make a new runner per function to be tested
                runner = DocTestRunner(verbose=d2u.verbose)
                map(runner.run, d2u.finder.find(func, func.func_name))
                failed = count_failures(runner)
                if failed:
                    # Since we only looked at a single function's docstring,
                    # failed should contain at most one item.  More than that
                    # is a case we can't handle and should error out on
                    if len(failed) > 1:
                        err = "Invalid number of test results:" % failed
                        raise ValueError(err)
                    # Report a normal failure.
                    self.fail('failed doctests: %s' % str(failed[0]))
                    
        # Rename it so test reports have the original signature.
        Tester.__name__ = func.func_name
        return Tester


def ipdocstring(func):
    """Change the function docstring via ip2py.
    """
    if func.__doc__ is not None:
        func.__doc__ = ip2py(func.__doc__)
    return func

        
# Make an instance of the classes for public use
ipdoctest = Doc2UnitTester()
ip2py = IPython2PythonConverter()
