"""
Google Workspace Add-on for KD-Code System
Enables KD-Code generation and scanning within Google Workspace applications
"""

import json
import base64
import requests
from typing import Dict, Any, Optional, List
import logging
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os


class GoogleWorkspaceAddon:
    """
    Google Workspace Add-on for KD-Code functionality
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.gmail_service = None
        self.drive_service = None
        self.docs_service = None
        self.sheets_service = None
        self.slides_service = None
        self.credentials = None
        
        # Google API scopes
        self.scopes = [
            'https://www.googleapis.com/auth/gmail.modify',
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/documents',
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/presentations'
        ]
    
    def authenticate_with_google(self, client_id: str, client_secret: str, 
                                redirect_uri: str, auth_code: str) -> bool:
        """
        Authenticate with Google using OAuth2
        
        Args:
            client_id: Google application client ID
            client_secret: Google application client secret
            redirect_uri: Redirect URI for OAuth2
            auth_code: Authorization code from Google
        
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            token_url = "https://oauth2.googleapis.com/token"
            
            token_data = {
                'client_id': client_id,
                'client_secret': client_secret,
                'code': auth_code,
                'grant_type': 'authorization_code',
                'redirect_uri': redirect_uri
            }
            
            response = requests.post(token_url, data=token_data)
            
            if response.status_code == 200:
                token_info = response.json()
                
                # Create credentials object
                self.credentials = Credentials(
                    token=token_info['access_token'],
                    refresh_token=token_info.get('refresh_token'),
                    token_uri=token_url,
                    client_id=client_id,
                    client_secret=client_secret,
                    scopes=self.scopes
                )
                
                # Build service objects
                self._build_services()
                
                self.logger.info("Successfully authenticated with Google Workspace")
                return True
            else:
                self.logger.error(f"Google authentication failed: {response.text}")
                return False
        except Exception as e:
            self.logger.error(f"Error authenticating with Google: {e}")
            return False
    
    def _build_services(self):
        """Build Google API service objects"""
        try:
            self.gmail_service = build('gmail', 'v1', credentials=self.credentials)
            self.drive_service = build('drive', 'v3', credentials=self.credentials)
            self.docs_service = build('docs', 'v1', credentials=self.credentials)
            self.sheets_service = build('sheets', 'v4', credentials=self.credentials)
            self.slides_service = build('slides', 'v1', credentials=self.credentials)
            
            self.logger.info("Google API services built successfully")
        except Exception as e:
            self.logger.error(f"Error building Google API services: {e}")
    
    def generate_kd_code_in_google_doc(self, document_id: str, text_to_encode: str, 
                                     position: Dict[str, int] = None) -> bool:
        """
        Generate and insert a KD-Code into a Google Doc
        
        Args:
            document_id: ID of the Google Doc
            text_to_encode: Text to encode in the KD-Code
            position: Position to insert the KD-Code (optional)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate KD-Code
            from kd_core.encoder import generate_kd_code
            kd_code_b64 = generate_kd_code(text_to_encode)
            
            if not kd_code_b64:
                self.logger.error("Failed to generate KD-Code")
                return False
            
            # Create image from base64
            image_data = base64.b64decode(kd_code_b64)
            
            # Upload image to Drive first
            file_metadata = {
                'name': f'kdcode_{document_id}.png',
                'parents': ['root']  # Or specify a folder
            }
            
            media = self._create_media_from_bytes(image_data, 'image/png')
            
            drive_file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,webViewLink'
            ).execute()
            
            image_file_id = drive_file.get('id')
            image_url = drive_file.get('webViewLink')
            
            # Insert image into the document
            if position:
                # Insert at specific position
                requests_list = [{
                    'insertInlineImage': {
                        'location': {
                            'index': position.get('index', 1)
                        },
                        'uri': image_url,
                        'objectSize': {
                            'height': {
                                'magnitude': position.get('height', 100),
                                'unit': 'PT'
                            },
                            'width': {
                                'magnitude': position.get('width', 100),
                                'unit': 'PT'
                            }
                        }
                    }
                }]
            else:
                # Insert at the end of the document
                # First get the document to find its length
                doc = self.docs_service.documents().get(documentId=document_id).execute()
                body = doc.get('body')
                content = body.get('content')
                
                # Find the end of the document
                end_index = 0
                for element in content:
                    if 'endIndex' in element:
                        end_index = max(end_index, element['endIndex'])
                
                requests_list = [{
                    'insertInlineImage': {
                        'location': {
                            'index': end_index - 1
                        },
                        'uri': image_url,
                        'objectSize': {
                            'height': {
                                'magnitude': 100,
                                'unit': 'PT'
                            },
                            'width': {
                                'magnitude': 100,
                                'unit': 'PT'
                            }
                        }
                    }
                }]
            
            # Execute the requests
            result = self.docs_service.documents().batchUpdate(
                documentId=document_id,
                body={'requests': requests_list}
            ).execute()
            
            self.logger.info(f"KD-Code inserted into Google Doc: {document_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error inserting KD-Code into Google Doc: {e}")
            return False
    
    def generate_kd_code_in_google_sheet(self, spreadsheet_id: str, text_to_encode: str, 
                                       cell_range: str = 'A1') -> bool:
        """
        Generate and insert a KD-Code into a Google Sheet
        
        Args:
            spreadsheet_id: ID of the Google Sheet
            text_to_encode: Text to encode in the KD-Code
            cell_range: Cell range to insert the KD-Code image (e.g., 'A1')
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate KD-Code
            from kd_core.encoder import generate_kd_code
            kd_code_b64 = generate_kd_code(text_to_encode)
            
            if not kd_code_b64:
                self.logger.error("Failed to generate KD-Code")
                return False
            
            # Create image from base64
            image_data = base64.b64decode(kd_code_b64)
            
            # Upload image to Drive first
            file_metadata = {
                'name': f'kdcode_{spreadsheet_id}.png',
                'parents': ['root']
            }
            
            media = self._create_media_from_bytes(image_data, 'image/png')
            
            drive_file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,webViewLink'
            ).execute()
            
            image_file_id = drive_file.get('id')
            image_url = drive_file.get('webViewLink')
            
            # Insert image into the spreadsheet
            # First, we need to get the sheet ID
            spreadsheet = self.sheets_service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            
            # Get the first sheet ID
            sheet_id = spreadsheet['sheets'][0]['properties']['sheetId']
            
            # Insert image request
            requests_list = [{
                'addImage': {
                    'spec': {
                        'contentUri': image_url
                    },
                    'cell': {
                        'sheetId': sheet_id,
                        'rowIndex': 0,  # A1 is row 0, col 0
                        'columnIndex': 0
                    }
                }
            }]
            
            # Execute the requests
            result = self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={'requests': requests_list}
            ).execute()
            
            self.logger.info(f"KD-Code inserted into Google Sheet: {spreadsheet_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error inserting KD-Code into Google Sheet: {e}")
            return False
    
    def generate_kd_code_in_google_slide(self, presentation_id: str, text_to_encode: str, 
                                       slide_index: int = 0) -> bool:
        """
        Generate and insert a KD-Code into a Google Slide
        
        Args:
            presentation_id: ID of the Google Presentation
            text_to_encode: Text to encode in the KD-Code
            slide_index: Index of the slide to insert into
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate KD-Code
            from kd_core.encoder import generate_kd_code
            kd_code_b64 = generate_kd_code(text_to_encode)
            
            if not kd_code_b64:
                self.logger.error("Failed to generate KD-Code")
                return False
            
            # Create image from base64
            image_data = base64.b64decode(kd_code_b64)
            
            # Upload image to Drive first
            file_metadata = {
                'name': f'kdcode_{presentation_id}.png',
                'parents': ['root']
            }
            
            media = self._create_media_from_bytes(image_data, 'image/png')
            
            drive_file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,webViewLink'
            ).execute()
            
            image_file_id = drive_file.get('id')
            image_url = drive_file.get('webViewLink')
            
            # Get presentation to find slide ID
            presentation = self.slides_service.presentations().get(
                presentationId=presentation_id
            ).execute()
            
            slide_id = presentation['slides'][slide_index]['objectId']
            
            # Insert image request
            requests_list = [{
                'createImage': {
                    'objectId': f'kdcode_img_{slide_index}',
                    'elementProperties': {
                        'pageObjectId': slide_id,
                        'size': {
                            'height': {'magnitude': 100, 'unit': 'PT'},
                            'width': {'magnitude': 100, 'unit': 'PT'}
                        },
                        'transform': {
                            'scaleX': 1.0,
                            'scaleY': 1.0,
                            'translateX': 100,  # Position in slide
                            'translateY': 100,
                            'unit': 'PT'
                        }
                    },
                    'url': image_url
                }
            }]
            
            # Execute the requests
            result = self.slides_service.presentations().batchUpdate(
                presentationId=presentation_id,
                body={'requests': requests_list}
            ).execute()
            
            self.logger.info(f"KD-Code inserted into Google Slide: {presentation_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error inserting KD-Code into Google Slide: {e}")
            return False
    
    def generate_kd_code_as_attachment(self, email_content: str, subject: str = "KD-Code Attachment") -> Optional[str]:
        """
        Generate a KD-Code and attach it to an email draft
        
        Args:
            email_content: Content to encode in the KD-Code
            subject: Subject for the email
        
        Returns:
            Draft ID if successful, None otherwise
        """
        try:
            # Generate KD-Code
            from kd_core.encoder import generate_kd_code
            kd_code_b64 = generate_kd_code(email_content)
            
            if not kd_code_b64:
                self.logger.error("Failed to generate KD-Code")
                return None
            
            # Create image from base64
            image_data = base64.b64decode(kd_code_b64)
            
            # Create email with attachment
            import base64
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText
            from email.mime.image import MIMEImage
            
            message = MIMEMultipart()
            message['to'] = ''  # Will be filled by user
            message['subject'] = subject
            
            # Add text content
            message.attach(MIMEText(f"KD-Code for: {email_content}", 'plain'))
            
            # Add KD-Code as attachment
            img = MIMEImage(image_data, name='kdcode.png')
            message.attach(img)
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            # Create draft
            draft = self.gmail_service.users().drafts().create(
                userId='me',
                body={
                    'message': {
                        'raw': raw_message
                    }
                }
            ).execute()
            
            self.logger.info(f"Email draft with KD-Code created: {draft['id']}")
            return draft['id']
        except Exception as e:
            self.logger.error(f"Error creating email with KD-Code attachment: {e}")
            return None
    
    def get_user_google_docs(self) -> List[Dict[str, str]]:
        """
        Get user's Google Docs that can be enhanced with KD-Codes
        
        Returns:
            List of document information
        """
        try:
            # Search for Google Docs
            query = "mimeType='application/vnd.google-apps.document'"
            results = self.drive_service.files().list(
                q=query,
                pageSize=50,
                fields="nextPageToken, files(id, name, mimeType, modifiedTime)"
            ).execute()
            
            documents = []
            for file in results.get('files', []):
                documents.append({
                    'id': file.get('id'),
                    'name': file.get('name'),
                    'mimeType': file.get('mimeType'),
                    'modifiedTime': file.get('modifiedTime')
                })
            
            return documents
        except Exception as e:
            self.logger.error(f"Error getting Google Docs: {e}")
            return []
    
    def get_user_google_sheets(self) -> List[Dict[str, str]]:
        """
        Get user's Google Sheets that can be enhanced with KD-Codes
        
        Returns:
            List of spreadsheet information
        """
        try:
            # Search for Google Sheets
            query = "mimeType='application/vnd.google-apps.spreadsheet'"
            results = self.drive_service.files().list(
                q=query,
                pageSize=50,
                fields="nextPageToken, files(id, name, mimeType, modifiedTime)"
            ).execute()
            
            spreadsheets = []
            for file in results.get('files', []):
                spreadsheets.append({
                    'id': file.get('id'),
                    'name': file.get('name'),
                    'mimeType': file.get('mimeType'),
                    'modifiedTime': file.get('modifiedTime')
                })
            
            return spreadsheets
        except Exception as e:
            self.logger.error(f"Error getting Google Sheets: {e}")
            return []
    
    def get_user_google_slides(self) -> List[Dict[str, str]]:
        """
        Get user's Google Slides that can be enhanced with KD-Codes
        
        Returns:
            List of presentation information
        """
        try:
            # Search for Google Slides
            query = "mimeType='application/vnd.google-apps.presentation'"
            results = self.drive_service.files().list(
                q=query,
                pageSize=50,
                fields="nextPageToken, files(id, name, mimeType, modifiedTime)"
            ).execute()
            
            presentations = []
            for file in results.get('files', []):
                presentations.append({
                    'id': file.get('id'),
                    'name': file.get('name'),
                    'mimeType': file.get('mimeType'),
                    'modifiedTime': file.get('modifiedTime')
                })
            
            return presentations
        except Exception as e:
            self.logger.error(f"Error getting Google Slides: {e}")
            return []
    
    def _create_media_from_bytes(self, data: bytes, mime_type: str):
        """Create a MediaIoBaseUpload object from bytes data"""
        from googleapiclient.http import MediaIoBaseUpload
        import io
        
        io_data = io.BytesIO(data)
        return MediaIoBaseUpload(io_data, mimetype=mime_type, resumable=True)


# Global Google Workspace integration instance
google_workspace_addon = GoogleWorkspaceAddon()


def initialize_google_workspace_addon():
    """Initialize the Google Workspace addon"""
    global google_workspace_addon
    google_workspace_addon = GoogleWorkspaceAddon()


def authenticate_google_workspace(client_id: str, client_secret: str, 
                                redirect_uri: str, auth_code: str) -> bool:
    """
    Authenticate with Google Workspace
    
    Args:
        client_id: Google application client ID
        client_secret: Google application client secret
        redirect_uri: Redirect URI for OAuth2
        auth_code: Authorization code from Google
    
    Returns:
        True if authentication successful, False otherwise
    """
    return google_workspace_addon.authenticate_with_google(
        client_id, client_secret, redirect_uri, auth_code
    )


def insert_kd_code_in_google_doc(document_id: str, text: str, position: Dict[str, int] = None) -> bool:
    """
    Insert a KD-Code into a Google Doc
    
    Args:
        document_id: ID of the Google Doc
        text: Text to encode in the KD-Code
        position: Position to insert the KD-Code (optional)
    
    Returns:
        True if successful, False otherwise
    """
    return google_workspace_addon.generate_kd_code_in_google_doc(document_id, text, position)


def insert_kd_code_in_google_sheet(spreadsheet_id: str, text: str, cell_range: str = 'A1') -> bool:
    """
    Insert a KD-Code into a Google Sheet
    
    Args:
        spreadsheet_id: ID of the Google Sheet
        text: Text to encode in the KD-Code
        cell_range: Cell range to insert the KD-Code image
    
    Returns:
        True if successful, False otherwise
    """
    return google_workspace_addon.generate_kd_code_in_google_sheet(spreadsheet_id, text, cell_range)


def insert_kd_code_in_google_slide(presentation_id: str, text: str, slide_index: int = 0) -> bool:
    """
    Insert a KD-Code into a Google Slide
    
    Args:
        presentation_id: ID of the Google Presentation
        text: Text to encode in the KD-Code
        slide_index: Index of the slide to insert into
    
    Returns:
        True if successful, False otherwise
    """
    return google_workspace_addon.generate_kd_code_in_google_slide(presentation_id, text, slide_index)


def create_email_with_kd_code_attachment(content: str, subject: str = "KD-Code Attachment") -> Optional[str]:
    """
    Create an email draft with a KD-Code attachment
    
    Args:
        content: Content to encode in the KD-Code
        subject: Subject for the email
    
    Returns:
        Draft ID if successful, None otherwise
    """
    return google_workspace_addon.generate_kd_code_as_attachment(content, subject)


def get_user_google_documents(doc_type: str = 'all') -> List[Dict[str, str]]:
    """
    Get user's Google documents of specified type
    
    Args:
        doc_type: Type of documents ('docs', 'sheets', 'slides', 'all')
    
    Returns:
        List of document information
    """
    if doc_type == 'docs' or doc_type == 'all':
        return google_workspace_addon.get_user_google_docs()
    elif doc_type == 'sheets':
        return google_workspace_addon.get_user_google_sheets()
    elif doc_type == 'slides':
        return google_workspace_addon.get_user_google_slides()
    else:
        return []


# Example usage
if __name__ == "__main__":
    print("Google Workspace Add-on for KD-Code System")
    print("This module provides integration with Google Workspace applications")
    
    # Example of how to use the integration:
    # 1. Authenticate with Google
    # success = authenticate_google_workspace(
    #     client_id="your_client_id",
    #     client_secret="your_client_secret", 
    #     redirect_uri="your_redirect_uri",
    #     auth_code="auth_code_from_google"
    # )
    # 
    # if success:
    #     # 2. Insert KD-Code into a Google Doc
    #     doc_success = insert_kd_code_in_google_doc(
    #         "document_id_here", 
    #         "Hello from Google Workspace!"
    #     )
    #     print(f"Inserted KD-Code in doc: {doc_success}")
    # 
    #     # 3. Get user's Google documents
    #     docs = get_user_google_documents('docs')
    #     print(f"Found {len(docs)} Google Docs")
    
    print("Module ready for Google Workspace integration")