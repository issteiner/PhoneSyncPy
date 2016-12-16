import unittest
import os
import PhoneSync
import unittest.mock

class MyTestCase(unittest.TestCase):
    def test_if_class_can_be_ize(self):
        fileData = PhoneSync.FileDataStore('/tmp/teszt')
        self.assertIsInstance(fileData, PhoneSync.FileDataStore, msg="Could not instantiate Class")

    def test_get_dir_path_repr(self):
        pass

if __name__ == '__main__':
    unittest.main()
