#!python
# -*- coding: utf-8 -*-
import io
import logging
# Configure logging level here
LOG_LEVEL = logging.INFO
# Configure logging to include line number
logging.basicConfig(level=LOG_LEVEL,
                    format='%(asctime)s - %(levelname)s - %(message)s (line %(lineno)d)',
                    datefmt='%Y-%m-%d %H:%M:%S')
import requests
from binascii import unhexlify, b2a_base64
from requests.auth import HTTPBasicAuth
from hashlib import sha256
import hmac
import configparser
import pandas as pd
import json
import os
# set working directory so can import scram and credentials (file in folder)
os.chdir(os.path.dirname(os.path.abspath(__file__)))
import scram
import logging


# Configure logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# Create logger
logger = logging.getLogger('MyLogger')

# http://www.alienfactory.co.uk/articles/skyspark-scram-over-sasl
class HaystackLogin(object):
    def __init__(self, url, user, password):
        self.url = url
        self.user = user
        self.password = password
        self.headers = {}

    # https://bmos.carnegosystems.net/ui
    # hello username=Z2xlbm5waWVyY2U
    def hello(self):
        headers = {'Authorization': 'HELLO username=%s' % (scram.base64_no_padding(self.user))}
        logger.debug(headers)
        logging.debug(self.user)
        logging.debug(headers)
        logging.debug(self.url)
        x = requests.get(self.url + '/ui', headers=headers)
        if x.status_code != 401:
            raise Exception("Hello failed")

        www_str = x.headers['www-authenticate']
        if not www_str.lower().startswith('scram'):
            raise Exception("We only support scram")

        logger.debug(www_str)
        self.handshake_token = www_str.split('handshakeToken=')[1].strip()

    def first_message(self):
        self._nonce = "5GK3jXL3hz0vuhrJI-h2ag=="  # scram.get_nonce_24()
        logging.debug('nonce %s', self._nonce)
        gs2_header = 'n,,'  # Is this to spec ? This is what I implemented on our server
        self.client_bare = 'n=' + self.user + ',r=' + self._nonce
        msg = gs2_header + self.client_bare
        data = scram.base64_no_padding(msg)

        headers = {'Authorization': 'SCRAM handshakeToken=%s, data=%s' % (self.handshake_token, data)}
        logger.debug(headers)
        logging.debug("first_message %s", self.url)
        x = requests.get(self.url + '/ui', headers=headers)
        www_str = x.headers['www-authenticate']
        if not www_str.lower().startswith('scram'):
            raise Exception("first_message fail")
        logger.debug(www_str)
        split_tmp = www_str.split(',')
        if len(split_tmp) < 3:
            raise Exception("first_message fail")
        tmp = split_tmp[2].strip()
        encoded_data = tmp.split('data=')[1]
        decoded = scram.urlsafe_b64decode(encoded_data).decode("utf-8")
        self._server_first_msg = decoded.strip()
        self._server_nonce = scram.marker_split(decoded, 'r=', ',s=')
        self._server_salt_base64 = scram.marker_split(decoded, ',s=', ',i=')
        self._server_salt = scram.b64decode(self._server_salt_base64)
        self._server_salt_hex = scram.hexlify(self._server_salt)
        self._server_interations = decoded.split(',i=')[1].strip()

        logging.debug('self._server_first_msg %s', self._server_first_msg)
        logging.debug('self._server_nonce %s', self._server_nonce)
        logging.debug('self._server_salt_base64 %s', self._server_salt_base64)
        logging.debug('self._server_salt %s', self._server_salt)
        logging.debug('self._server_salt_hex %s', self._server_salt_hex)
        logging.debug('self._server_interations %s', self._server_interations)

    def _create_client_proof(salted_password, auth_msg):
        logging.debug('auth_msg %s', auth_msg)
        logging.debug('salted_password: %s', salted_password)
        client_key = hmac.new(unhexlify(salted_password), "Client Key".encode("utf-8"), sha256).hexdigest()
        logging.debug('client_key: %s', client_key)
        logging.debug("client key un hexed: %s", unhexlify(client_key))
        stored_key = scram._hash_sha256(unhexlify(client_key), sha256)
        logging.debug('stored_key: %s', stored_key)
        logging.debug("unhexlify(stored_key) %s", unhexlify(stored_key))
        logging.debug("auth_msg.encode() %s", auth_msg.encode())
        client_signature = hmac.new(unhexlify(stored_key), auth_msg.encode(), sha256).hexdigest()
        logging.debug('client_signature: %s', client_signature)
        client_proof = scram._xor(client_key, client_signature)
        logging.debug('client_proof: %s', client_proof)
        return b2a_base64(unhexlify(client_proof)).decode("utf-8")

    def second_message(self):
        logging.debug("scram.salted_password_2 %s %s %s", self._server_salt_hex, self._server_interations, self.password)
        self.salted_password = scram.salted_password_2(
            self._server_salt_hex,
            self._server_interations,
            "sha256",
            self.password,
        )

        logging.debug('salted_password: %s', self.salted_password)

        self.salted_password_hex = scram.hexlify(self.salted_password)

        logger.debug('salted_password_hex: %s', self.salted_password_hex)

        cbind_input = "n,,"
        channel_binding = 'c=' + scram.base64_no_padding(cbind_input)

        nonce = 'r=' + self._server_nonce
        c2_no_proof = channel_binding + ',' + nonce

        logger.debug("c2_no_proof: %s", c2_no_proof)

        logging.debug("self.client_bare: %s", self.client_bare)
        logging.debug("self._server_first_msg: %s", self._server_first_msg)
        logging.debug("c2_no_proof: %s", c2_no_proof)

        auth_msg = self.client_bare + ',' + self._server_first_msg + ',' + c2_no_proof

        logger.debug('auth_msg: %s', auth_msg)

        logging.debug("_create_client_proof args %s %s", self.salted_password, auth_msg)
        client_proof = HaystackLogin._create_client_proof(self.salted_password, auth_msg)

        logging.debug('client_proof base64 encoded: %s', client_proof)

        client_final = c2_no_proof + ',p=' + client_proof

        logger.debug("client_final: %s", client_final)

        data = scram.base64_no_padding(client_final)

        logger.debug('data: %s', data)

        headers = {'Authorization': 'SCRAM handshakeToken=%s, data=%s' % (self.handshake_token, data)}
        logger.info(headers)
        x = requests.get(self.url + '/ui', headers=headers)

        if x.status_code != 200:
            raise Exception("failed to authenticate")

        headers = {}
        headers['authorization'] = 'bearer ' + x.headers['authentication-info'].split(',')[0]

        return headers

    def login(self):
        self.hello()
        logger.debug('handshake_token: %s', self.handshake_token)
        self.first_message()
        return self.second_message()

def about(url, auth_header):
    response = requests.post(url=url + '/about', headers=auth_header)
    data = response.content
    logging.debug('Response: %s', response)
    logging.debug('Data: %s', data)

def get_ref_map(url, auth_header):
    zinc = 'ver:"3.0" action:"ref_namespace_map"\n'
    logging.debug('Zinc: %s', zinc)
    return requests.post(url=url + '/action', headers=auth_header, data=zinc)

def historical_read(url, auth_header, aggregate, granularity, refs, daterange):
    zinc_fmt = 'ver:"3.0" aggregate:"%s" granularity:"%s" interpolate:"true"\nid,range\n%s,"%s"\n'
    zinc = zinc_fmt % (aggregate, granularity, refs, daterange)
    logging.debug('Zinc: %s', zinc)
    return requests.post(url=url + '/hisRead', headers=auth_header, data=zinc)

def refresh_token(url, auth_header):
    response = requests.post(url=url + '/refresh_token', headers=auth_header)
    data = response.content
    logging.debug('Response: %s', response)
    logging.debug('Data: %s', data)
    return response

def get_user_info(url, auth_header):
    response = requests.get(url=url + '/api/info', headers=auth_header)
    data = response.content
    logging.debug('Response: %s', response)
    logging.debug('Data: %s', data)
    return response


def prompt_for_input(prompt_text, default=None):
    user_input = input(prompt_text)  # For Python 3
    return user_input.strip() or default

def save_config(url, username, password):
    config = configparser.ConfigParser()
    config.add_section('Login')
    config.set('Login', 'URL', url)
    config.set('Login', 'Username', username)
    config.set('Login', 'Password', password)

    with open('config.ini', 'w') as configfile:
        config.write(configfile)

def load_config():

    config = configparser.ConfigParser()
    config.read('config.ini')

    url = config.get('Login', 'URL', fallback="https://users.carnego.net")
    username = config.get('Login', 'Username', fallback="")
    password = config.get('Login', 'Password', fallback="")

    return url, username, password

def giveRef(lookup, site, variable=None):
    # Ensure site is always a list if not None
    if site is not None and isinstance(site, str):
        site = [site]
    
    # Ensure variable is always a list if not None
    if variable is not None and isinstance(variable, str):
        variable = [variable]
    
    if site is None:
        # If site is None, do not filter by site
        if variable is None:
            return lookup.ref.tolist()
        else:
            return lookup.ref[lookup.name.isin(variable)].tolist()
    else:
        if variable is None:
            return lookup.ref[lookup.siteNamespace.isin(site)].tolist()
        else:
            return lookup.ref[
                lookup.siteNamespace.isin(site) & 
                lookup.name.isin(variable)
            ].tolist()

def login(auth_url, username, password):
    # Load the configuration
    #auth_url, username, password = load_config()
    if not auth_url:
        # Prompt for the URL if not present in the config
        url_prompt = "Enter the URL (default: {}): ".format(auth_url)
        auth_url = prompt_for_input(url_prompt, default=auth_url)
    # Prompt for the username and password if not present in the config
    if not username:
        username = prompt_for_input("Enter your username: ")
    if not password:
        password = prompt_for_input("Enter your password: ")
    logging.debug("username: %s password: %s", username, password)
    auth = HaystackLogin(auth_url, username, password)
    # This gives us a header that includes an auth token to send to the server for more data.
    # Note here I set the server which the data to bmos12. In the future this made need to be determined from what
    # is returned from user_info
    auth_header = auth.login()
    bmos_server = 'https://bmos12.carnego.net'

    # Get the user info 
    user_info = get_user_info(auth_url, auth_header)
    logging.debug("Text: %s", user_info.text)
    user_info = json.loads(user_info.text)

    attributes = {}
    try:
        attributes = user_info["attributes"]
    except KeyError:
        # Raise a KeyError with a custom error message
        raise KeyError("Key 'attributes' does not exist in the dictionary")

    auth_header['site_group_namespace'] = 'yosemite.nisep.refresh'
    return bmos_server,auth_header

def getLookup(auth_url, username, password,return_login=False):
    bmos_server,auth_header = login(auth_url, username, password)

    # return a zinc file (csv like) of points and all their attributes
    ref_map = get_ref_map(bmos_server, auth_header)
    # create lookup
    df = pd.read_csv(io.StringIO(ref_map.text), skiprows=1)
    df['siteNamespace'] = df['siteNamespace'].str.split('.').str[-1]
    df['equipNamespace'] = df['equipNamespace'].str.split('.').str[-1]
    if return_login==True:
        return df, bmos_server,auth_header
    else:
        return df

def getTimeseries(end_time,start_time,site,variable, auth_url, username, password,averaging="max",interval="minute"):
    df, bmos_server,auth_header = getLookup(auth_url, username, password, return_login=True)

    daterange = f"{start_time.strftime('%Y-%m-%dT%H:%M:%S')},{end_time.strftime('%Y-%m-%dT%H:%M:%S')}" # format into the right date range string
    formatted_list = "[" + ", ".join(giveRef(df,site, variable)) + "]"

    timeseries_response = historical_read(bmos_server, auth_header, averaging, interval, formatted_list, daterange)
    timeseries_df = pd.read_csv(io.StringIO(timeseries_response.text), skiprows=1)

    # Filter the lookup DataFrame to only include relevant refs found in timeseries_df column names
    filtered_lookup = df[df['ref'].str.strip('@').isin(
        [col.split('(')[-1].split(')')[0] for col in timeseries_df.columns if '(' in col]
    )]
    
    # Create a mapping dictionary from the filtered lookup DataFrame
    mapping = {ref.strip('@'): name for ref, name in zip(filtered_lookup['ref'], filtered_lookup['siteNamespace'])}
    
    # Replace numbers in column names using the filtered mapping
    timeseries_df.columns = [
        col.split('(')[0].strip() + f" ({mapping[num]})" if '(' in col and num in mapping else col
        for col in timeseries_df.columns for num in [col.split('(')[-1].split(')')[0] if '(' in col else '']
    ]
    # Make column names unique
    timeseries_df.columns = pd.Series(timeseries_df.columns).where(~pd.Series(timeseries_df.columns).duplicated(), 
                                             pd.Series(timeseries_df.columns) + '_' + pd.Series(timeseries_df.columns).duplicated().cumsum().astype(str))

        # Coerce all columns to numeric except the 'datetime' column
    for col in timeseries_df.columns:
        if col != 'datetime':  # Exclude datetime column from coercion
            timeseries_df[col] = pd.to_numeric(timeseries_df[col], errors='coerce')

    timeseries_df["datetime"] = pd.to_datetime(timeseries_df["datetime"])  # Ensure datetime column is in datetime format
    timeseries_df.set_index("datetime", inplace=True)
    
    return timeseries_df