import sys
import decimal
from tests import unittest, OrderedDict

import jmespath
import jmespath.functions


class TestSearchOptions(unittest.TestCase):
    def test_can_provide_dict_cls(self):
        result = jmespath.search(
            '{a: a, b: b, c: c}.*',
            {'c': 'c', 'b': 'b', 'a': 'a', 'd': 'd'},
            options=jmespath.Options(dict_cls=OrderedDict))
        self.assertEqual(result, ['a', 'b', 'c'])

    def test_can_provide_custom_functions(self):
        class CustomFunctions(jmespath.functions.Functions):
            @jmespath.functions.signature(
                {'types': ['number']},
                {'types': ['number']})
            def _func_custom_add(self, x, y):
                return x + y

            @jmespath.functions.signature(
                {'types': ['number']},
                {'types': ['number']})
            def _func_my_subtract(self, x, y):
                return x - y


        options = jmespath.Options(custom_functions=CustomFunctions())
        self.assertEqual(
            jmespath.search('custom_add(`1`, `2`)', {}, options=options),
            3
        )
        self.assertEqual(
            jmespath.search('my_subtract(`10`, `3`)', {}, options=options),
            7
        )
        # Should still be able to use the original functions without
        # any interference from the CustomFunctions class.
        self.assertEqual(
            jmespath.search('length(`[1, 2]`)', {}), 2
        )



class TestPythonSpecificCases(unittest.TestCase):
    def test_can_compare_strings(self):
        # This is python specific behavior that's not in the official spec
        # yet, but this was regression from 0.9.0 so it's been added back.
        self.assertTrue(jmespath.search('a < b', {'a': '2016', 'b': '2017'}))

    @unittest.skipIf(not hasattr(sys, 'maxint'), 'Test requires long() type')
    def test_can_handle_long_ints(self):
        result = sys.maxsize + 1
        self.assertEqual(jmespath.search('[?a >= `1`].a', [{'a': result}]),
                         [result])

    def test_can_handle_decimals_as_numeric_type(self):
        result = decimal.Decimal('3')
        self.assertEqual(jmespath.search('[?a >= `1`].a', [{'a': result}]),
                         [result])


# https://github.com/jmespath/jmespath.py/issues/182
class TestEmptyStringHandling(unittest.TestCase):
    def setUp(self):
        self.data = {
            "foo": {"": {"bar": {"baz": 123}}}
        }

    def assert_search(self, data, expression, expected_result):
        actual = jmespath.search(expression, data)
        self.assertEqual(expected_result, actual)
        return actual

    def test_quotes_field_sequence(self):
        self.assert_search(self.data, 'foo."".bar.baz', 123)

    def test_quotes_with_wildcard_field_last(self):
        self.assert_search(self.data, 'foo."".bar.*', [123])

    def test_quotes_with_wildcard_field_middle(self):
        self.assert_search(self.data, 'foo."".*.baz', [123])

    def test_quotes_with_wildcards_sequence(self):
        self.assert_search(self.data, 'foo."".*.*', [[123]])

    # ?
    def test_field_with_wildcard_first(self):
        self.assert_search(self.data, 'foo.*[].bar.baz', [123])

    def test_field_with_wildcard_first_flatten(self):
        self.assert_search(self.data, 'foo.*[].bar.baz', [123])

    def test_field_with_wildcard_first_pipe(self):
        self.assert_search(self.data, 'foo.*.bar | [].baz', [123])

    # ?
    def test_multiple_wildcards_with_middle_field(self):
        self.assert_search(self.data, 'foo.*[].bar.*', [[123]])

    def test_multiple_wildcards_with_middle_field_flatten(self):
        self.assert_search(self.data, 'foo.*[].bar.*', [[123]])

    def test_multiple_wildcards_with_last_field(self):
        self.assert_search(self.data, 'foo.*.*.baz', [[123]])

    def test_multiple_wildcards_sequence(self):
        self.assert_search(self.data, 'foo.*.*.*', [[[123]]])

    def test_multiple_wildcards_separated(self):
        # Same as 'foo.*.bar.*' but divided in 2 steps
        # 'foo.*.bar.*' = 'foo.*.bar' + '[*].*'
        result = self.assert_search(self.data, 'foo.*.bar', [{'baz': 123}])
        self.assert_search(result, '[*].*', [[123]])

    def test_wildcard_dot_syntax(self):
        self.assert_search(self.data, 'foo.*', [{'bar': {'baz': 123}}])

    def test_index_wildcards(self):
        self.assert_search(self.data, 'foo.[*]', [[{'bar': {'baz': 123}}]])

    def test_wildcard_with_field(self):
        self.assert_search(self.data, 'foo.*.bar', [{'baz': 123}])

    def test_complex_quotes(self):
        data = {
            "foo": [
                {"": {"bar": {"baz": 123}}},
                {"one": {"bar": {"": "123"}}},
                {"two": {"bar": {"": "123"}}},
                {"": {"bar": {"": "123"}}}
            ]
        }
        self.assert_search(data, 'foo[*].*.{"" : bar.*.to_number(@)}[].""[]', [123, 123, 123, 123])
        self.assert_search(data, 'foo[*].*.{"" : bar.*.to_number(@)}[].*[][]', [123, 123, 123, 123])
        self.assert_search(data, 'foo[*].*.bar[].*[].to_number(@)', [123, 123, 123, 123])
