# Create unittest test suite
import unittest


class TestDummy(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_dummy(self):
        self.assertTrue(True)
