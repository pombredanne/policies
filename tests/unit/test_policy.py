# Copyright (C) 2013 by Kevin L. Mitchell <klmitch@mit.edu>
#
# This program is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see
# <http://www.gnu.org/licenses/>.

import mock
import pkg_resources

from policies import policy
from policies import rules

import tests


class TestPolicyContext(tests.TestCase):
    def test_init(self):
        ctxt = policy.PolicyContext('policy', 'attrs', 'variables')

        self.assertEqual(ctxt.policy, 'policy')
        self.assertEqual(ctxt.attrs, 'attrs')
        self.assertEqual(ctxt.variables, 'variables')
        self.assertEqual(ctxt.stack, [])
        self.assertEqual(ctxt.authz, None)

    def test_resolve_defined(self):
        pol = mock.Mock()
        ctxt = policy.PolicyContext(pol, 'attrs', {'a': 1})

        result = ctxt.resolve('a')

        self.assertEqual(result, 1)
        self.assertFalse(pol.resolve.called)

    def test_resolve_undefined(self):
        pol = mock.Mock(**{'resolve.return_value': 'value'})
        ctxt = policy.PolicyContext(pol, 'attrs', {'a': 1})

        result = ctxt.resolve('b')

        self.assertEqual(result, 'value')
        pol.resolve.assert_called_once_with('b')


def item_setter(obj, item, value):
    obj[item] = value


class TestPolicy(tests.TestCase):
    def test_init_basic(self):
        pol = policy.Policy()

        self.assertEqual(pol._group, None)
        self.assertEqual(pol._defaults, {})
        self.assertEqual(pol._docs, {})
        self.assertEqual(pol._rules, {})
        self.assertEqual(pol._resolve_cache, policy.Policy._builtins)
        self.assertNotEqual(id(pol._resolve_cache),
                            id(policy.Policy._builtins))

    def test_init_full(self):
        builtins = {'a': 1, 'b': 2, 'c': 3}

        pol = policy.Policy('group', builtins)

        self.assertEqual(pol._group, 'group')
        self.assertEqual(pol._defaults, {})
        self.assertEqual(pol._docs, {})
        self.assertEqual(pol._rules, {})
        self.assertEqual(pol._resolve_cache, builtins)
        self.assertNotEqual(id(pol._resolve_cache), id(builtins))

    def test_getitem_none(self):
        pol = policy.Policy()

        self.assertRaises(KeyError, pol.__getitem__, 'rule')

    def test_getitem_default(self):
        pol = policy.Policy()
        pol._defaults['rule'] = 'default'

        self.assertEqual(pol['rule'], 'default')

    def test_getitem_set(self):
        pol = policy.Policy()
        pol._defaults['rule'] = 'default'
        pol._rules['rule'] = 'configured'

        self.assertEqual(pol['rule'], 'configured')

    @mock.patch.object(rules, 'Rule', return_value='compiled')
    def test_setitem_string(self, mock_Rule):
        pol = policy.Policy()

        pol['rule'] = 'test'

        self.assertEqual(pol._rules, {'rule': 'compiled'})
        self.assertEqual(pol._defaults, {})
        mock_Rule.assert_called_once_with('rule', 'test')

    def test_setitem_badname(self):
        pol = policy.Policy()
        rule = rules.Rule('name')

        with mock.patch.object(rules, 'Rule',
                               return_value='compiled') as mock_Rule:
            self.assertRaises(policy.PolicyException, item_setter,
                              pol, 'rule', rule)

        self.assertEqual(pol._defaults, {})
        self.assertFalse(mock_Rule.called)

    def test_setitem(self):
        pol = policy.Policy()
        rule = rules.Rule('rule')

        with mock.patch.object(rules, 'Rule',
                               return_value='compiled') as mock_Rule:
            pol['rule'] = rule

        self.assertEqual(pol._rules, {'rule': rule})
        self.assertEqual(pol._defaults, {})
        self.assertFalse(mock_Rule.called)

    def test_delitem(self):
        pol = policy.Policy()
        pol._rules = {'a': 1, 'b': 2}
        pol._defaults = {'a': 3}

        del pol['a']

        self.assertEqual(pol._rules, {'b': 2})
        self.assertEqual(pol._defaults, {'a': 3})

    def test_iter(self):
        pol = policy.Policy()
        pol._rules = {'a': 1, 'c': 3}
        pol._defaults = {'b': 2, 'c': 3}

        result = sorted(iter(pol))

        self.assertEqual(result, ['a', 'b', 'c'])

    def test_len(self):
        pol = policy.Policy()
        pol._rules = {'a': 1, 'c': 3}
        pol._defaults = {'b': 2, 'c': 3}

        result = len(pol)

        self.assertEqual(result, 3)

    @mock.patch.object(rules, 'Rule', return_value='rule')
    @mock.patch.object(rules, 'RuleDoc', return_value='doc')
    def test_declare_basic(self, mock_RuleDoc, mock_Rule):
        pol = policy.Policy()

        pol.declare('name')

        self.assertEqual(pol._defaults, {'name': 'rule'})
        self.assertEqual(pol._docs, {'name': 'doc'})
        self.assertEqual(pol._rules, {})
        mock_Rule.assert_called_once_with('name', '', None)
        mock_RuleDoc.assert_called_once_with('name', None, None)

    @mock.patch.object(rules, 'Rule', return_value='rule')
    @mock.patch.object(rules, 'RuleDoc', return_value='doc')
    def test_declare_full(self, mock_RuleDoc, mock_Rule):
        pol = policy.Policy()

        pol.declare('name', 'text', 'doc', {'a': 1, 'b': 2},
                    {'a': 'doc a', 'b': 'doc b'})

        self.assertEqual(pol._defaults, {'name': 'rule'})
        self.assertEqual(pol._docs, {'name': 'doc'})
        self.assertEqual(pol._rules, {})
        mock_Rule.assert_called_once_with('name', 'text', {'a': 1, 'b': 2})
        mock_RuleDoc.assert_called_once_with('name', 'doc',
                                             {'a': 'doc a', 'b': 'doc b'})

    def test_set_rule(self):
        rule = rules.Rule('name')
        pol = policy.Policy()

        pol.set_rule(rule)

        self.assertEqual(pol._rules, {'name': rule})
        self.assertEqual(pol._defaults, {})

    def test_del_rule(self):
        rule = rules.Rule('name')
        pol = policy.Policy()
        pol._rules = {'name': 'rule1', 'other': 'rule2'}
        pol._defaults = {'name': 'default'}

        pol.del_rule(rule)

        self.assertEqual(pol._rules, {'other': 'rule2'})
        self.assertEqual(pol._defaults, {'name': 'default'})

    @mock.patch.object(rules, 'RuleDoc', return_value='doc')
    def test_get_doc_exists(self, mock_RuleDoc):
        pol = policy.Policy()
        pol._docs['name'] = 'other'

        result = pol.get_doc('name')

        self.assertEqual(result, 'other')
        self.assertEqual(pol._docs, {'name': 'other'})
        self.assertFalse(mock_RuleDoc.called)

    @mock.patch.object(rules, 'RuleDoc', return_value='doc')
    def test_get_doc_empty(self, mock_RuleDoc):
        pol = policy.Policy()

        result = pol.get_doc('name')

        self.assertEqual(result, 'doc')
        self.assertEqual(pol._docs, {'name': 'doc'})
        mock_RuleDoc.assert_called_once_with('name')

    @mock.patch.object(pkg_resources, 'iter_entry_points', return_value=[
        mock.Mock(**{'load.side_effect': ImportError()}),
        mock.Mock(**{'load.side_effect': AttributeError()}),
        mock.Mock(**{'load.side_effect': pkg_resources.UnknownExtra()}),
        mock.Mock(**{'load.return_value': 'value1'}),
        mock.Mock(**{'load.return_value': 'value2'}),
    ])
    def test_resolve_builtin(self, mock_iter_entry_points):
        pol = policy.Policy()

        result = pol.resolve('abs')

        self.assertEqual(result, abs)
        self.assertFalse(mock_iter_entry_points.called)

    @mock.patch.object(pkg_resources, 'iter_entry_points', return_value=[
        mock.Mock(**{'load.side_effect': ImportError()}),
        mock.Mock(**{'load.side_effect': AttributeError()}),
        mock.Mock(**{'load.side_effect': pkg_resources.UnknownExtra()}),
        mock.Mock(**{'load.return_value': 'value1'}),
        mock.Mock(**{'load.return_value': 'value2'}),
    ])
    def test_resolve_nogroup(self, mock_iter_entry_points):
        pol = policy.Policy()

        result = pol.resolve('other')

        self.assertEqual(result, None)
        self.assertEqual(pol._resolve_cache['other'], None)
        self.assertFalse(mock_iter_entry_points.called)

    @mock.patch.object(pkg_resources, 'iter_entry_points', return_value=[
        mock.Mock(**{'load.side_effect': ImportError()}),
        mock.Mock(**{'load.side_effect': AttributeError()}),
        mock.Mock(**{'load.side_effect': pkg_resources.UnknownExtra()}),
        mock.Mock(**{'load.return_value': 'value1'}),
        mock.Mock(**{'load.return_value': 'value2'}),
    ])
    def test_resolve_withgroup(self, mock_iter_entry_points):
        pol = policy.Policy('group')

        result = pol.resolve('other')

        self.assertEqual(result, 'value1')
        self.assertEqual(pol._resolve_cache['other'], 'value1')
        mock_iter_entry_points.assert_called_once_with('group', 'other')

    @mock.patch.object(pkg_resources, 'iter_entry_points', return_value=[])
    def test_resolve_withgroup_noresolve(self, mock_iter_entry_points):
        pol = policy.Policy('group')

        result = pol.resolve('other')

        self.assertEqual(result, None)
        self.assertEqual(pol._resolve_cache['other'], None)
        mock_iter_entry_points.assert_called_once_with('group', 'other')

    @mock.patch('logging.getLogger')
    @mock.patch('policies.authorization.Authorization', return_value='authz')
    @mock.patch.object(policy, 'PolicyContext',
                       return_value=mock.Mock(authz='ctxt_authz'))
    def test_evaluate_norule(self, mock_PolicyContext, mock_Authorization,
                             mock_getLogger):
        pol = policy.Policy()

        result = pol.evaluate('name')

        self.assertEqual(result, 'authz')
        mock_Authorization.assert_called_once_with(False)
        self.assertFalse(mock_PolicyContext.called)
        self.assertFalse(mock_getLogger.called)

    @mock.patch('logging.getLogger')
    @mock.patch('policies.authorization.Authorization', return_value='authz')
    @mock.patch.object(policy, 'PolicyContext',
                       return_value=mock.Mock(authz='ctxt_authz'))
    def test_evaluate_default(self, mock_PolicyContext, mock_Authorization,
                              mock_getLogger):
        default = mock.Mock(attrs={'a': 1})
        pol = policy.Policy()
        pol._defaults['name'] = default

        result = pol.evaluate('name')

        self.assertEqual(result, 'ctxt_authz')
        self.assertFalse(mock_Authorization.called)
        mock_PolicyContext.assert_called_once_with(pol, {'a': 1}, {})
        default.instructions.assert_called_once_with(
            mock_PolicyContext.return_value)
        self.assertFalse(mock_getLogger.called)

    @mock.patch('logging.getLogger')
    @mock.patch('policies.authorization.Authorization', return_value='authz')
    @mock.patch.object(policy, 'PolicyContext',
                       return_value=mock.Mock(authz='ctxt_authz'))
    def test_evaluate_rule(self, mock_PolicyContext, mock_Authorization,
                           mock_getLogger):
        rule = mock.Mock(attrs={'a': 1})
        pol = policy.Policy()
        pol._rules['name'] = rule

        result = pol.evaluate('name')

        self.assertEqual(result, 'ctxt_authz')
        self.assertFalse(mock_Authorization.called)
        mock_PolicyContext.assert_called_once_with(pol, {'a': 1}, {})
        rule.instructions.assert_called_once_with(
            mock_PolicyContext.return_value)
        self.assertFalse(mock_getLogger.called)

    @mock.patch('logging.getLogger')
    @mock.patch('policies.authorization.Authorization', return_value='authz')
    @mock.patch.object(policy, 'PolicyContext',
                       return_value=mock.Mock(authz='ctxt_authz'))
    def test_evaluate_both(self, mock_PolicyContext, mock_Authorization,
                           mock_getLogger):
        rule = mock.Mock(attrs={'a': 1, 'b': 2})
        default = mock.Mock(attrs={'b': 3, 'c': 4})
        pol = policy.Policy()
        pol._rules['name'] = rule
        pol._defaults['name'] = default

        result = pol.evaluate('name')

        self.assertEqual(result, 'ctxt_authz')
        self.assertFalse(mock_Authorization.called)
        mock_PolicyContext.assert_called_once_with(
            pol, {'a': 1, 'b': 2, 'c': 4}, {})
        rule.instructions.assert_called_once_with(
            mock_PolicyContext.return_value)
        self.assertFalse(default.instructions.called)
        self.assertFalse(mock_getLogger.called)

    @mock.patch('logging.getLogger')
    @mock.patch('policies.authorization.Authorization', return_value='authz')
    @mock.patch.object(policy, 'PolicyContext',
                       return_value=mock.Mock(authz='ctxt_authz'))
    def test_evaluate_variables(self, mock_PolicyContext, mock_Authorization,
                                mock_getLogger):
        rule = mock.Mock(attrs={'a': 1})
        pol = policy.Policy()
        pol._rules['name'] = rule

        result = pol.evaluate('name', {'x': 23, 'y': 24, 'z': 25})

        self.assertEqual(result, 'ctxt_authz')
        self.assertFalse(mock_Authorization.called)
        mock_PolicyContext.assert_called_once_with(
            pol, {'a': 1}, {'x': 23, 'y': 24, 'z': 25})
        rule.instructions.assert_called_once_with(
            mock_PolicyContext.return_value)
        self.assertFalse(mock_getLogger.called)

    @mock.patch('logging.getLogger')
    @mock.patch('policies.authorization.Authorization', return_value='authz')
    @mock.patch.object(policy, 'PolicyContext',
                       return_value=mock.Mock(authz='ctxt_authz'))
    def test_evaluate_exception(self, mock_PolicyContext, mock_Authorization,
                                mock_getLogger):
        rule = mock.Mock(**{
            'attrs': {'a': 1},
            'instructions.side_effect': tests.TestException("test"),
        })
        pol = policy.Policy()
        pol._rules['name'] = rule

        result = pol.evaluate('name')

        self.assertEqual(result, 'authz')
        mock_Authorization.assert_called_once_with(False, {'a': 1})
        mock_PolicyContext.assert_called_once_with(pol, {'a': 1}, {})
        rule.instructions.assert_called_once_with(
            mock_PolicyContext.return_value)
        mock_getLogger.assert_called_once_with('policies')
        mock_getLogger.return_value.warn.assert_called_once_with(
            "Exception raised while evaluating rule 'name': test")
