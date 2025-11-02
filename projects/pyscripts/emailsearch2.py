from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import datetime
import base64

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/documents']

def search_gmail_and_create_doc(keyword1, keyword2, start_date):
    """Searches Gmail based on keywords and date, then creates a Google Doc."""
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        # Gmail API
        service_gmail = build('gmail', 'v1', credentials=creds)
        # Docs API
        service_docs = build('docs', 'v1', credentials=creds)

        # Construct the search query.
        query = f'after:{start_date} {keyword1} {keyword2}'
        results = service_gmail.users().messages().list(userId='me', q=query).execute()
        messages = results.get('messages', [])

        if not messages:
            print('No messages found.')
            return

        # Create a new Google Doc.
        document = {'title': f'Gmail Search Results - {datetime.date.today()}'}
        document = service_docs.documents().create(body=document).execute()
        document_id = document.get('documentId')

        requests = []
        for message in messages:
            msg = service_gmail.users().messages().get(userId='me', id=message['id'], format='full').execute()
            payload = msg['payload']
            headers = payload['headers']
            for header in headers:
                if header['name'] == 'Subject':
                    subject = header['value']
                if header['name'] == 'From':
                    sender = header['value']
                if header['name'] == 'Date':
                    date = header['value']

            # Extract the message body.
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        data = part['body']['data']
                        message_body = base64.urlsafe_b64decode(data).decode()
                        break
                    elif part['mimeType'] == 'text/html':
                        data = part['body']['data']
                        message_body = 'HTML email. HTML data not included for simplicity.'
                        break
            else:
                if payload['mimeType'] == 'text/plain':
                    data = payload['body']['data']
                    message_body = base64.urlsafe_b64decode(data).decode()
                elif payload['mimeType'] == 'text/html':
                    data = payload['body']['data']
                    message_body = 'HTML email. HTML data not included for simplicity.'

            requests.append({
                'insertText': {
                    'location': {
                        'index': 1,
                    },
                    'text': f'Subject: {subject}\nFrom: {sender}\nDate: {date}\n\n{message_body}\n\n--------------------\n\n',
                }
            })
        if requests:
          result = service_docs.documents().batchUpdate(documentId=document_id, body={'requests': requests}).execute()
          print(f'Document created: https://docs.google.com/document/d/{document_id}')

    except HttpError as error:
        print(f'An error occurred: {error}')

import os.path

if __name__ == '__main__':
    keyword1 = input("Enter keyword 1: ")
    keyword2 = input("Enter keyword 2: ")
    start_date = input("Enter start date (YYYY/MM/DD): ")
    search_gmail_and_create_doc(keyword1, keyword2, start_date)
