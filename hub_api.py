import json
import logging
import time

import requests
from django.core.cache import cache

logger = logging.getLogger(__name__)

BASE_URL = "https://api.hubapi.com"

CONTACTS_URL = BASE_URL + "/contacts/v1/contact"
COMPANIES_URL = BASE_URL + "/companies/v2/companies"


class HubSpot:

    api_key = None

    cache_key = 'hub_api_calls'

    user_property_manager = None

    def __init__(self, *, api_key, user_property_manager):
        self.api_key = api_key
        self.user_property_manager = user_property_manager

    @property
    def client(self):
        client = requests.Session()
        client.headers.update({'content-type': 'application/json'})
        client.params.update({'hapikey': self.api_key})
        return client

    def request(self, method, url, params={}, **kwargs):
        """
        Make a request without violating HubSpot's rate limit of 10 requests per second.

        We err on the safe side and sleep when there are 8 within the last 10 seconds.
        """
        now = time.time()
        recent_calls = cache.get(self.cache_key)
        if recent_calls:
            recent_calls = [t for t in recent_calls if now - t <= 10]
            if len(recent_calls) >= 8:
                time_to_sleep = min([abs(10.1 - (now - recent_calls[0])), 10])
                logger.info('[HUBSPOT] sleeping for {} seconds '.format(time_to_sleep) +
                            'to avoid exceeding rate limits')
                time.sleep(time_to_sleep)
        if not recent_calls:
            recent_calls = []
        recent_calls.append(time.time())
        cache.set(self.cache_key, recent_calls)
        return self.client.request(method, url, params=params, **kwargs)

    # sync user methods
    def sync_user(self, user):
        data = self.user_property_manager.generate_sync_data(user)
        resp = self.create_or_update_contact(user.email, data)
        return resp

    # contact methods
    def create_or_update_user(self, user, user_data):
        if not user.crm_unique_id:
            url = "{}/createOrUpdate/email/{}".format(CONTACTS_URL, user.email)
            response = self.request('post', url, json=user_data)
            if response is not None:
                user.crm_unique_id = response.json()['vid']
                user.save()
                return response.json()
        else:
            response = self.request(
                'post',
                BASE_URL + '/contacts/v1/contact/vid/%s/profile' % user.crm_unique_id,
                data=json.dump(user_data)
            )
            return response

    # contact methods
    def create_or_update_contact(self, email, user_data):
        url = "{}/createOrUpdate/email/{}".format(CONTACTS_URL, email)
        response = self.request('post', url, json=user_data)
        if response is not None:
            return response.json()

    # contact properties
    def sync_contact_property_groups(self):

        # get groups first
        response = self.request('get', BASE_URL + '/properties/v1/contacts/groups')
        existing_group_names = [g['name'] for g in response.json()]

        for group in self.user_property_manager.groups:
            if group['name'] not in existing_group_names:
                logger.info('[HUBSPOT][SYNC] Creating new contact property group %s',
                            group['name'])
                self.request('post', BASE_URL + '/properties/v1/contacts/groups',
                             data=json.dumps(group))
            else:
                logger.info('[HUBSPOT][SYNC] Updating existing contact property group %s',
                            group['name'])
                self.request('put',
                             BASE_URL +
                             '/properties/v1/contacts/groups/named/%s' % group.pop('name'),
                             data=json.dumps(group))

    def sync_contact_properties(self):

        response = self.request('get', BASE_URL + '/properties/v1/contacts/properties')
        existing_prop_names = [p['name'] for p in response.json()]

        # Create / update propertiest from CONTACT_PROPERTIES
        for prop in self.user_property_manager.custom_user_properties:

            prop_dict = prop.get_dict()

            if prop_dict['name'] not in existing_prop_names:
                logger.info('[HUBSPOT][SYNC] Creating contact property %s', prop_dict['name'])
                self.request(
                    'post',
                    BASE_URL + '/properties/v1/contacts/properties', data=json.dumps(prop_dict))
            else:
                logger.info(
                    '[HUBSPOT][SYNC] Updating existing contact property %s', prop_dict['name'])
                self.request(
                    'put',
                    BASE_URL + '/properties/v1/contacts/properties/named/{}'.format(
                        prop_dict.pop('name')),
                    data=json.dumps(prop_dict))

        # Delete old properties from our group
        cf_group_names = [g['name'] for g in self.user_property_manager.groups]
        cf_prop_names = [p.name for p in self.user_property_manager.custom_user_properties]
        prop_names_to_delete = [p['name'] for p in response.json() if
                                p['groupName'] in cf_group_names and
                                p['name'] not in cf_prop_names]

        for prop_name in prop_names_to_delete:
            logger.info('[HUBSPOT][SYNC] Deleting unused contact property %s', prop_name)
            resp = self.request('delete',
                                BASE_URL + '/properties/v1/contacts/properties/named/' +
                                prop_name)
            assert resp.status_code == 204
