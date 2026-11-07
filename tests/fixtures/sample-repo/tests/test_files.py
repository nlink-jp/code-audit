import os
import tempfile
import unittest

from app import files


class ReadUserFileTests(unittest.TestCase):
    def test_reads_named_file(self):
        with tempfile.TemporaryDirectory() as base:
            with open(os.path.join(base, "hello.txt"), "w", encoding="utf-8") as fh:
                fh.write("hi")
            self.assertEqual(files.read_user_file(base, "hello.txt"), "hi")
            self.assertEqual(files.list_user_files(base), ["hello.txt"])


if __name__ == "__main__":
    unittest.main()
