from googleapiclient.discovery import build
from google.oauth2 import service_account

class GoogleAPI:
    def __init__(self, service_name, version, credentials_file):
        self.service_name = service_name
        self.version = version
        self.credentials_file = credentials_file
        self.service = self.authenticate()

    def authenticate(self):
        credentials = service_account.Credentials.from_service_account_file(
            self.credentials_file
        )
        return build(self.service_name, self.version, credentials=credentials)

    def get_service(self):
        return self.service

    # Add more methods to interact with specific Google APIs as needed
    # For example, methods to list files in Google Drive, send emails via Gmail, etc.