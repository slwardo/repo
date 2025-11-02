from google.auth import impersonated_credentials, default
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import datetime
import base64
import os

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/documents']

def search_gmail_and_create_doc(keyword1, keyword2, start_date, target_service_account):
    """Searches Gmail based on keywords and date, then creates a Google Doc using service account impersonation."""
    try:
        # Get default credentials
        creds, _ = default()

        # Impersonate the target service account.
        impersonated_creds = impersonated_credentials.Credentials(
            creds,
            target_service_account,
            SCOPES, # scopes as a positional argument
        )

        # Gmail API
        service_gmail = build('gmail', 'v1', credentials=impersonated_creds)
        # Docs API
        service_docs = build('docs', 'v1', credentials=impersonated_creds)

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

if __name__ == '__main__':
    keyword1 = input("Enter keyword 1: ")
    keyword2 = input("Enter keyword 2: ")
    start_date = input("Enter start date (YYYY/MM/DD): ")
    target_service_account = input("Enter the target service account email: ")
    search_gmail_and_create_doc(keyword1, keyword2, start_date, target_service_account)
