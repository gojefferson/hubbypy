import pytest
import time
from unittest.mock import MagicMock, Mock, PropertyMock, patch

from hubbypy.hubbypy.hub_api import HubSpot
from hubbypy.hubbypy.contact_properties import (
    AccessorProperty,
    BaseUserProperty,
    ConstantProperty,
    FunctionProperty,
    UserPropertyManager
)

hs_user_property_manager = UserPropertyManager(
    groups=[
        {
            'name': 'your_org',
            'displayName': 'Your API Data'
        }
    ]
)


class SimpleCache:

    def __init__(self):
        self._cache = {}

    def set(self, key, value):
        self._cache[key] = value

    def get(self, key):
        return self._cache.get(key)


def test_bool_native_type_to_hs_type():
    active_user = BaseUserProperty(
        name='some_org_is_active',
        label='Active Account User',
        group_name='some_org',
        native_type='bool',
    )

    assert active_user.hs_type == 'enumeration'
    assert active_user.field_type == 'booleancheckbox'


def test_bool_native_type_to_hs_type_get_dict():
    active_user = BaseUserProperty(
        name='some_org_is_active',
        label='Active Account User',
        group_name='some_org',
        native_type='bool',
    )

    _dict = active_user.get_dict()

    assert 'Yes' in [o['label'] for o in _dict['options']]


def test_date_native_type_to_hs_type():
    active_user = BaseUserProperty(
        name='some_org_is_active',
        label='Active Account User',
        group_name='some_org',
        native_type='date',
    )

    assert active_user.hs_type == 'date'
    assert active_user.field_type == 'date'


def test_datetime_native_type_to_hs_type():
    active_user = BaseUserProperty(
        name='some_org_is_active',
        label='Active Account User',
        group_name='some_org',
        native_type='datetime',
    )

    assert active_user.hs_type == 'datetime'
    assert active_user.field_type == 'date'


def test_varchar_native_type_to_hs_type():
    active_user = BaseUserProperty(
        name='some_org_is_active',
        label='Active Account User',
        group_name='some_org',
        native_type='varchar',
    )

    assert active_user.hs_type == 'string'
    assert active_user.field_type == 'text'


def test_texarea_native_type_to_hs_type():
    active_user = BaseUserProperty(
        name='some_org_is_active',
        label='Active Account User',
        group_name='some_org',
        native_type='textarea',
    )

    assert active_user.hs_type == 'string'
    assert active_user.field_type == 'textarea'


def test_number_native_type_to_hs_type():
    active_user = BaseUserProperty(
        name='some_org_is_active',
        label='Active Account User',
        group_name='some_org',
        native_type='number',
    )

    assert active_user.hs_type == 'number'
    assert active_user.field_type == 'number'


def test_cannot_use_type_other_than_those_listed():

    with pytest.raises(KeyError):

        BaseUserProperty(
            name='some_org_is_active',
            label='Active Account User',
            group_name='some_org',
            native_type='numberolog',
        )


def test_adding_two_properties_with_same_name_raises_error():

    property_manager = UserPropertyManager(
        groups=[
            {
                'name': 'your_org',
                'displayName': 'Your API Data'
            }
        ]
    )

    property_manager.add_prop(
        BaseUserProperty(
            name='some_org_is_active',
            label='Active Account User',
            group_name='some_org',
            native_type='bool',
        )
    )

    with pytest.raises(ValueError) as err:

        property_manager.add_prop(
            BaseUserProperty(
                name='some_org_is_active',
                label='Active Account User',
                group_name='some_org',
                native_type='bool',
            )
        )

        assert 'Manager already contains' in str(err.value)


def test_get_value_user_accessor():

    user = Mock()
    user.is_active = 'yes'

    active_user = AccessorProperty(
        name='some_org_is_active',
        label='Active Account User',
        group_name='some_org',
        native_type='bool',
        accessor='is_active'
    )

    assert active_user._get_value(user) == 'yes'


def test_get_value_func_property():

    user = Mock()
    func = MagicMock(return_value='test call')

    active_user = FunctionProperty(
        name='some_org_is_active',
        label='Active Account User',
        group_name='some_org',
        native_type='bool',
        func=func,
        send_user=False
    )

    assert active_user._get_value(user) == 'test call'
    assert func.called


def test_get_formatted_value_user_accessor_boolean():

    user = Mock()
    user.is_active = True

    active_user = AccessorProperty(
        name='some_org_is_active',
        label='Active Account User',
        group_name='some_org',
        native_type='bool',
        accessor='is_active'
    )

    assert active_user.get_formatted_value(user) == 'true'


def test_nested_user_accessor():

    user = Mock()
    user.company = Mock()
    user.company.name = 'Test Account'

    company_name = AccessorProperty(
        name='some_org_company_name',
        label='User Account Name',
        group_name='some_org',
        native_type='varchar',
        accessor='company.name'
    )

    assert company_name.get_formatted_value(user) == 'Test Account'


def test_constant_property():

    user = Mock()

    company_name = ConstantProperty(
        name='some_org_company_name',
        label='User Account Name',
        group_name='some_org',
        native_type='varchar',
        value='Some Company'
    )

    assert company_name.get_formatted_value(user) == 'Some Company'


def test_request_queing():

    with patch('hubbypy.hubbypy.hub_api.HubSpot.client',
               new_callable=PropertyMock) as mock_client:

        client = Mock()
        client.request = MagicMock(return_value=True)
        mock_client.return_value = client

        cache = SimpleCache()

        test_hubspot = HubSpot(
            api_key='testing',
            user_property_manager=hs_user_property_manager,
            cache_backend=cache
        )

        test_hubspot.request('post', 'www.test.com')
        test_hubspot.request('post', 'www.test.com')
        test_hubspot.request('post', 'www.test.com')

        assert len(cache.get(test_hubspot.cache_key)) == 3
        assert test_hubspot.client.request.called


def test_request_queing_sleeping():

    with patch('hubbypy.hubbypy.hub_api.time.sleep', return_value=None) as sleeper:

        with patch('hubbypy.hubbypy.hub_api.HubSpot.client',
                   new_callable=PropertyMock) as mock_client:

            client = Mock()
            client.request = MagicMock(return_value=True)
            mock_client.return_value = client

            cache = SimpleCache()

            test_hubspot = HubSpot(
                api_key='testing',
                user_property_manager=hs_user_property_manager,
                cache_backend=cache
            )

            cache.set(test_hubspot.cache_key, None)

            for _ in range(12):
                test_hubspot.request('post', 'www.test.com')

            assert len(cache.get(test_hubspot.cache_key)) == 12
            assert sleeper.call_count == 4


def test_old_requests_cleared_from_cache():

    with patch('hubbypy.hubbypy.hub_api.time.sleep', return_value=None) as sleeper:

        with patch('hubbypy.hubbypy.hub_api.HubSpot.client',
                   new_callable=PropertyMock) as mock_client:

            client = Mock()
            client.request = MagicMock(return_value=True)
            mock_client.return_value = client

            cache = SimpleCache()

            test_hubspot = HubSpot(
                api_key='testing',
                user_property_manager=hs_user_property_manager,
                cache_backend=cache
            )

            now = time.time()

            old_time_stamps = [now - 11 for _ in range(11)]

            cache.set(test_hubspot.cache_key, old_time_stamps)

            test_hubspot.request('post', 'www.test.com')

            assert len(cache.get(test_hubspot.cache_key)) == 1
            assert sleeper.call_count == 0
