#!/usr/bin/env python3

'''

This script checks session timeouts for all orgs associated to a user token

'''

from mistrs import get_credentials, get_headers, get, print_table

############################################################

def get_settings(id, baseurl, headers):
    # Gets org timeout
    url = f'{baseurl}orgs/{id}/setting'
    data = get(url, headers)
    timeout = data.get('ui_idle_timeout', 0)
    return timeout


def get_data(baseurl, headers):
    #gets all available orgs for a token
    Orgs_Array = []
    url = f'{baseurl}self'
    data = get(url, headers)
    count = len(data['privileges'])
    print ("Getting data for {} Organisations".format(count))
    for i in data['privileges']:
        org = {
        "id" : i.get("org_id"),
        "name": i.get("name"),
        "role": i.get("role")
        }
        if i.get('scope') == 'org':
            timeout = get_settings(i.get("org_id"), baseurl, headers)
            org['timeout'] = timeout
            Orgs_Array.append(org)
    return Orgs_Array

############################################################

def main():
    credentials = get_credentials(org_token=False)
    headers = get_headers(credentials["api_token"])
    baseurl = credentials["api_url"]
    Array = get_data(baseurl, headers)
    Sorted_Array = sorted(Array, key=lambda x: x['timeout'], reverse=True)
    for i, option in enumerate(Sorted_Array, start=1):
        option['#'] = i
    print(print_table(Sorted_Array))

if __name__ == '__main__':
    main()
