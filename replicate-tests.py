import filecmp
import json
import unittest

from replicate import rewrite_config


class MyTestCase(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.maxDiff = None

    def test_config(self):
        with open('test-config.json', 'r') as i, open('.actual.json', 'w') as a, open("expected.json") as e:
            config = json.load(i)
            rewritten = rewrite_config(config, source_api='http://example.com',
                                       system_name='upstream')
            expected_config = json.load(e)
            self.assertEqual(rewritten, expected_config)


if __name__ == '__main__':
    unittest.main()
