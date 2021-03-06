import os, sys
import shutil

from twisted.trial import unittest
import twisted.python.procutils

from buildslave.commands import utils

class GetCommand(unittest.TestCase):

    def setUp(self):
        # monkey-patch 'which' to return something appropriate
        self.which_results = {}
        def which(arg):
            return self.which_results.get(arg, [])
        self.patch(twisted.python.procutils, 'which', which)
        # note that utils.py currently imports which by name, so we
        # patch it there, too
        self.patch(utils, 'which', which)

    def set_which_results(self, results):
        self.which_results = results

    def test_getCommand_empty(self):
        self.set_which_results({
            'xeyes' : [],
        })
        self.assertRaises(RuntimeError, lambda : utils.getCommand('xeyes'))

    def test_getCommand_single(self):
        self.set_which_results({
            'xeyes' : [ '/usr/bin/xeyes' ],
        })
        self.assertEqual(utils.getCommand('xeyes'), '/usr/bin/xeyes')

    def test_getCommand_multi(self):
        self.set_which_results({
            'xeyes' : [ '/usr/bin/xeyes', '/usr/X11/bin/xeyes' ],
        })
        self.assertEqual(utils.getCommand('xeyes'), '/usr/bin/xeyes')

    def test_getCommand_single_exe(self):
        self.set_which_results({
            'xeyes' : [ '/usr/bin/xeyes' ],
            # it should not select this option, since only one matched
            # to begin with
            'xeyes.exe' : [ r'c:\program files\xeyes.exe' ],
        })
        self.assertEqual(utils.getCommand('xeyes'), '/usr/bin/xeyes')

    def test_getCommand_multi_exe(self):
        self.set_which_results({
            'xeyes' : [ r'c:\program files\xeyes.com', r'c:\program files\xeyes.exe' ],
            'xeyes.exe' : [ r'c:\program files\xeyes.exe' ],
        })
        # this one will work out differently depending on platform..
        if sys.platform.startswith('win'):
            self.assertEqual(utils.getCommand('xeyes'), r'c:\program files\xeyes.exe')
        else:
            self.assertEqual(utils.getCommand('xeyes'), r'c:\program files\xeyes.com')

class RmdirRecursive(unittest.TestCase):

    # this is more complicated than you'd think because Twisted doesn't
    # rmdir its test directory very well, either..

    def setUp(self):
        self.target = 'testdir'
        try:
            if os.path.exists(self.target):
                shutil.rmtree(self.target)
        except:
            # this test will probably fail anyway
            e = sys.exc_info()[0]
            raise unittest.SkipTest("could not clean before test: %s" % (e,))

        # fill it with some files
        os.mkdir(os.path.join(self.target))
        open(    os.path.join(self.target, "a"), "w")
        os.mkdir(os.path.join(self.target, "d"))
        open(    os.path.join(self.target, "d", "a"), "w")
        os.mkdir(os.path.join(self.target, "d", "d"))
        open(    os.path.join(self.target, "d", "d", "a"), "w")

    def tearDown(self):
        try:
            if os.path.exists(self.target):
                shutil.rmtree(self.target)
        except:
            print "\n(target directory was not removed by test, and cleanup failed too)\n"
            raise

    def test_rmdirRecursive_easy(self):
        utils.rmdirRecursive(self.target)
        self.assertFalse(os.path.exists(self.target))

    def test_rmdirRecursive_symlink(self):
        # this was intended as a regression test for #792, but doesn't seem
        # to trigger it.  It can't hurt to check it, all the same.
        if sys.platform.startswith('win'):
            raise unittest.SkipTest("no symlinks on this platform")
        os.mkdir("noperms")
        open("noperms/x", "w")
        os.chmod("noperms/x", 0)
        try:
            os.symlink("../noperms", os.path.join(self.target, "link"))
            utils.rmdirRecursive(self.target)
            # that shouldn't delete the target of the symlink
            self.assertTrue(os.path.exists("noperms"))
        finally:
            # even Twisted can't clean this up very well, so try hard to
            # clean it up ourselves..
            os.chmod("noperms/x", 0777)
            os.unlink("noperms/x")
            os.rmdir("noperms")

        self.assertFalse(os.path.exists(self.target))
