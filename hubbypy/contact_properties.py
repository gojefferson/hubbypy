import copy
import functools
import logging
import time
from datetime import datetime, date

logger = logging.getLogger(__name__)


PROPERTY_GROUPS = [
    {
        'name': 'your_org',
        'displayName': 'My Sample Organization Property Group'
    }
]


sentinel = object()


def rgetattr(obj, attr, default=sentinel):
    if default is sentinel:
        _getattr = getattr
    else:
        def _getattr(obj, name):
            return getattr(obj, name, default)
    return functools.reduce(_getattr, [obj] + attr.split('.'))


class EnumerationOption:
    """
      Each option will have the following data
      - "description": null,
          String or null; a description of the option.
      - "label": "Blue",
          String; A human readable label for the option. The label is displayed in the HubSpot UI.
      - "displayOrder": -1,
          Integer; Options are displayed in numerical order based on this value,
          options with -1 appear after options with positive values
      - "hidden": false,
          Boolean; hidden values will not be displayed in HubSpot
      - "value": "blue"
          String; The internal value of the option.  The value must be used to set
          the value of the property.
    }

    """

    def __init__(self, *, value, label, display_order=-1, description=None, hidden=False):
        self.value = value
        self.label = label
        self.display_order = display_order
        self.description = description
        self.hidden = hidden

    def get_dict(self):

        _dict = {}

        _dict['value'] = self.value
        _dict['label'] = self.label
        _dict['displayOrder'] = self.display_order
        _dict['description'] = self.description
        _dict['hidden'] = self.hidden

        return _dict


class BaseUserProperty:
    """
    The base class for three different types of properties you may want to post to HubSpot to use
    for the purpose of segmenting contacts for sending emails, creating tasks, and
    triggering workflows (timed sequences of emails). For example, you might want
    to create a list in HubSpot of account owners on a certain stripe plan.
    For that use-case we will want to save the `is_owner` and Stripe `plan_id` properties
    to HubSpot.

    The three subclasses, `AccessorProperty`, `FunctionProperty`, and `ConstantProperty`
    do this work.

    Their differences are explained in their docstrings. They share the following common
    features:

    Each new instance *must* have the following attributes:
    - `name`: a string name that must be unique. By convention, custom properties that we define,
      shoulb are prefixed with `your_org_`. NB: if you use a name that corresponds to an existing
      HubSpot property, you should set `built_in` to `True` (see below)
    - `native_type`: the basic type of the property in database and python terms. The class is
      responsible for mapping the value to the correct type in HubSpot both when defining the
      property and when getting a value to for a particular user. The class also uses the
      `native_type` to pick an appropriate HubSpot for displaying the data in HubSpot
      The following options are possible:
      - `bool`
      - `date`
      - `datetime`
      - `number`
      - `varchar`
      - `textarea`
    - `label`: a human readable label for the field in HubSpot. This is what users of HubSpot
      will see when they are looking at contact records.

    The following attributes are optional:
    - `group_name`: the name of the property group to which this property belongs. At this time,
      all custom properties belong to one group named `your_org`.
    - `built_in`: set this to true if the property is not a custom property, but is one of the
      built in HubSpot properties, such as `email`, `firstname`, and `lifecyclestage`. A full
      list of these properties can be found
      [here](https://knowledge.hubspot.com/articles/kcs_article/contacts/list-of-hubspot-s-default-contact-properties)
    - `description`: a description of the property that HubSpot users will see in the CRM

    """
    name = None
    label = None
    description = None
    group_name = None
    hs_type = None
    fieldType = None
    built_in = False

    def _get_hs_type(self, native_type, options=None):
        """
        string, number, date, datetime, or enumeration
        """
        type_mappings = {
            'date': 'date',
            'datetime': 'datetime',
            'varchar': 'string',
            'textarea': 'string',
            'number': 'number',
            'enumeration': 'enumeration'
        }
        if native_type == 'enumeration':
            assert type(options) == list
            self.options = options
        return type_mappings[native_type]

    def _get_field_type(self, native_type):
        field_type_mappings = {
            'bool': 'booleancheckbox',
            'date': 'date',
            'datetime': 'date',
            'varchar': 'text',
            'textarea': 'textarea',
            'number': 'number',
            'enumeration': ''
        }
        return field_type_mappings.get(native_type, None)

    def _handle_bool(self):
        self.hs_type = 'enumeration'
        trueOption = EnumerationOption(
            value='true',
            label='Yes',
            display_order=1
        )

        falseOption = EnumerationOption(
            value='false',
            label='No',
            display_order=2
        )

        self.options = [trueOption, falseOption]

    def __init__(self, *, name, native_type, label=None, description=None,
                 group_name=None, options=None, built_in=False):
        self.name = name
        self.label = label
        self.description = description
        self.native_type = native_type
        self.group_name = group_name
        self.built_in = built_in
        if native_type == 'enumeration':
            assert type(options) == list
            self.options = options
        elif native_type == 'bool':
            self._handle_bool()
        else:
            self.options = options
            self.hs_type = self._get_hs_type(native_type, options)
        self.field_type = self._get_field_type(native_type)

    def get_dict(self):
        """
        Return a dictionary with keys conforming to the HubSpot API. This enables
        us to create or update the property in HubSpot.

        """
        _dict = {}
        _dict['name'] = self.name
        _dict['label'] = self.label
        _dict['type'] = self.hs_type
        _dict['groupName'] = self.group_name
        if self.description:
            _dict['description'] = self.description
        if self.field_type:
            _dict['fieldType'] = self.field_type
        if self.options:
            _dict['options'] = [o.get_dict() for o in self.options]
        return _dict

    def get_formatted_value(self, user):
        """
        Get the value of the property in the from required by HubSpot for a particular user
        """
        value = self._get_value(user)

        if value is not None:
            if self.native_type == 'bool':
                return 'true' if value else 'false'
            if self.native_type == 'datetime':
                return self._datetime_to_unix(value)
            if self.native_type == 'date' and type(value) is date:
                return self._date_to_unix(value)
            if self.native_type == 'date' and type(value) is datetime:
                return self._date_to_unix(value.date())
            return value

    def _get_value(self, user):
        raise NotImplementedError('Subclasses of BaseUserProperty should provide should '
                                  'implement the _get_value method')

    def _datetime_to_unix(self, timestamp):
        return int(time.mktime(timestamp.timetuple()) * 1e3 + timestamp.microsecond / 1e3)

    def _date_to_unix(self, thisdate):
        return int(time.mktime(thisdate.timetuple()) * 1000)


class AccessorProperty(BaseUserProperty):
    """
    A property whose value is determined by looking up a value on a user record via dot notation.
    Thanks to the `rgetattr` function, we can lookup values that are nested, such as
    `user.company.name`. In addition to the properties needed
    """

    def __init__(self, *, accessor, **kwargs):
        self.accessor = accessor
        super().__init__(**kwargs)

    def _get_value(self, user):
        try:
            return rgetattr(user, self.accessor)
        except Exception as err:
            logger.debug(
                '[HUBSPOT] Could not get {} property on user with email{}, error: {}'.format(
                    self.accessor,
                    user.email,
                    err))


class FunctionProperty(BaseUserProperty):
    """
    A property whose value depends on calling a function at the time we ask for the value.
    Usefull for saving the last synced time. If your function takes a user as an argument,
    then set `send_user` to `True`.
    """

    def __init__(self, *, func, send_user=False, **kwargs):
        self.func = func
        self.send_user = send_user
        super().__init__(**kwargs)

    def _get_value(self, user):
        if self.send_user:
            return self.func(user)
        return self.func()


class ConstantProperty(BaseUserProperty):
    """
    A property whose value is always the same. `value` is the only required argument
    besides the required args from the base class
    """

    def __init__(self, *, value, **kwargs):
        self.value = value
        super().__init__(**kwargs)

    def _get_value(self, user):
        return self.value


class UserPropertyManager:

    _user_properties = []
    _groups = []

    def __init__(self, *, groups):
        self._user_properties = []
        self._groups = groups

    def add_prop(self, prop):

        if prop.name in [p.name for p in self._user_properties]:
            raise ValueError('Manager already contains a property with this name')
        else:
            self._user_properties.append(prop)

    @property
    def groups(self):
        return copy.deepcopy(self._groups)

    @property
    def custom_user_properties(self):
        """
        The properties that we have created, in contrast with the properties that HubSpot
        creates -- whick cannot be deleted
        """
        return [p for p in self._user_properties if not p.built_in]

    def generate_sync_data(self, user):

        properties = []

        for prop in self._user_properties:
            properties.append(
                {
                    'property': prop.name,
                    'value': prop.get_formatted_value(user)
                }
            )

        return {
            'properties': properties
        }
