# © 2025 Numantic Solutions LLC
# MIT License
#
#

import os

# Environment variables for API credential storage
from dotenv import dotenv_values
from dotenv import load_dotenv

class ApiAuthentication:
    '''
    Class to store API authentication credentials in an object.

    Attributes

        dotenv_path: Path to .env file used by dotenv
        cred_source: Credential source:
            'local': Credentials come from a local .env file

    '''

    def __init__(self,
                 client: str,
                 **kwargs):
        '''
        Initialize class

        '''

        # Class parameters
        self.dotenv_path = "{}/.numantic/keys/{}".format(os.environ["HOME"],
                                                        client)
        self.override = True
        self.cred_source = "dotenv"

        # Update any key word args
        self.__dict__.update(kwargs)

        # Set up error message
        self.error_message = None

        # Get the database configuration
        self.__get_api_creds__()

        # Set environment variables - unless it has some error message
        if self.error_message == None:
            self.set_environ_variables()

    def __get_api_creds__(self):
        '''
        Method to retrieve API credentials

        '''

        self.apis_configs = {}

        # check if dotenv_path - if not return None
        if not os.path.exists(self.dotenv_path):
            msg = "The dotenv_path ({}) path could not be found.".format(self.dotenv_path)
            self.error_message = msg
            return None

        # check if .env in the directory
        if ".env" not in os.listdir(self.dotenv_path):
            msg = "No .env file found in dotenv_path directory: {}.".format(self.dotenv_path)
            self.error_message = msg
            return None

        # Get the dotenv configuration file
        if self.cred_source == "dotenv":
            creds_file = ".env"
            self.apis_configs = dotenv_values(os.path.join(self.dotenv_path,
                                                           creds_file))

    def set_environ_variables(self):
        '''
        Load environmental variables from a .env file
        '''
        load_dotenv(dotenv_path=os.path.join(self.dotenv_path, ".env"), override=self.override)