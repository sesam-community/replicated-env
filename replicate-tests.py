import filecmp
import json
import unittest

from replicate import rewrite_config


class MyTestCase(unittest.TestCase):
    def test_config(self):
        with open('test-config.json', 'r') as i, open('.actual.json', 'w') as a:
            config = json.load(i)
            rewritten = rewrite_config(config, source_api='http://example.com', source_jwt='source_jwt',
                                       system_name='upstream')
            json.dump(rewritten, a, indent=2, sort_keys=True)
        self.assertTrue(filecmp.cmp('.actual.json', 'expected.json'))


if __name__ == '__main__':
    unittest.main()
