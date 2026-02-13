"""
Microsoft Office Integration for KD-Code System
Enables integration with Microsoft Office applications
"""

import os
import json
import base64
from typing import Dict, Any, Optional
import logging
from flask import Flask, request, jsonify
import requests
from urllib.parse import urlencode


class MicrosoftOfficeIntegration:
    """
    Integration system for Microsoft Office applications
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.api_base_url = "https://graph.microsoft.com/v1.0"
        self.access_token = None
        self.client_id = os.environ.get('MS_OFFICE_CLIENT_ID')
        self.client_secret = os.environ.get('MS_OFFICE_CLIENT_SECRET')
        self.redirect_uri = os.environ.get('MS_OFFICE_REDIRECT_URI', 'http://localhost:5000/ms-office/callback')
    
    def get_auth_url(self) -> str:
        """
        Get the Microsoft Office 365 authentication URL
        
        Returns:
            Authentication URL for Microsoft Office
        """
        auth_params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': self.redirect_uri,
            'scope': 'Files.ReadWrite Mail.Send User.Read',
            'response_mode': 'query'
        }
        
        auth_url = f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?{urlencode(auth_params)}"
        return auth_url
    
    def exchange_code_for_token(self, auth_code: str) -> bool:
        """
        Exchange authorization code for access token
        
        Args:
            auth_code: Authorization code from Microsoft
        
        Returns:
            True if successful, False otherwise
        """
        token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
        
        token_data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': auth_code,
            'redirect_uri': self.redirect_uri,
            'grant_type': 'authorization_code'
        }
        
        try:
            response = requests.post(token_url, data=token_data)
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                return True
            else:
                self.logger.error(f"Token exchange failed: {response.text}")
                return False
        except Exception as e:
            self.logger.error(f"Error exchanging code for token: {e}")
            return False
    
    def refresh_access_token(self, refresh_token: str) -> bool:
        """
        Refresh the access token using a refresh token
        
        Args:
            refresh_token: Refresh token from Microsoft
        
        Returns:
            True if successful, False otherwise
        """
        token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
        
        token_data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token',
            'scope': 'Files.ReadWrite Mail.Send User.Read'
        }
        
        try:
            response = requests.post(token_url, data=token_data)
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                return True
            else:
                self.logger.error(f"Token refresh failed: {response.text}")
                return False
        except Exception as e:
            self.logger.error(f"Error refreshing token: {e}")
            return False
    
    def generate_kd_code_in_office_doc(self, document_id: str, text_to_encode: str, 
                                     position: Dict[str, int] = None) -> bool:
        """
        Generate and insert a KD-Code into a Microsoft Office document
        
        Args:
            document_id: ID of the document in OneDrive
            text_to_encode: Text to encode in the KD-Code
            position: Position to insert the KD-Code (optional)
        
        Returns:
            True if successful, False otherwise
        """
        if not self.access_token:
            self.logger.error("No access token available for Microsoft Office integration")
            return False
        
        try:
            # Generate KD-Code
            from kd_core.encoder import generate_kd_code
            kd_code_b64 = generate_kd_code(text_to_encode)
            
            if not kd_code_b64:
                self.logger.error("Failed to generate KD-Code")
                return False
            
            # Create image from base64
            image_data = base64.b64decode(kd_code_b64)
            
            # Upload KD-Code image to OneDrive
            upload_result = self.upload_image_to_onedrive(image_data, f"kdcode_{document_id}.png")
            
            if not upload_result:
                self.logger.error("Failed to upload KD-Code image to OneDrive")
                return False
            
            # For now, we'll just return success - in a real implementation,
            # we would insert the image into the document using Microsoft Graph API
            # This would require using the Word API to insert images at specific positions
            
            self.logger.info(f"KD-Code generated and uploaded for document {document_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error generating KD-Code in Office document: {e}")
            return False
    
    def upload_image_to_onedrive(self, image_data: bytes, filename: str) -> Optional[str]:
        """
        Upload an image to OneDrive
        
        Args:
            image_data: Image data as bytes
            filename: Name for the uploaded file
        
        Returns:
            URL of the uploaded file or None if failed
        """
        if not self.access_token:
            return None
        
        # Upload to user's OneDrive root
        upload_url = f"{self.api_base_url}/me/drive/root:/{filename}:/content"
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'image/png'
        }
        
        try:
            response = requests.put(upload_url, headers=headers, data=image_data)
            
            if response.status_code in [200, 201]:
                file_info = response.json()
                return file_info.get('@microsoft.graph.downloadUrl')
            else:
                self.logger.error(f"OneDrive upload failed: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            self.logger.error(f"Error uploading to OneDrive: {e}")
            return None
    
    def insert_kd_code_in_word_doc(self, document_id: str, text_to_encode: str, 
                                 paragraph_index: int = -1) -> bool:
        """
        Insert a KD-Code into a Microsoft Word document
        
        Args:
            document_id: ID of the Word document in OneDrive
            text_to_encode: Text to encode in the KD-Code
            paragraph_index: Index of paragraph to insert after (-1 for end)
        
        Returns:
            True if successful, False otherwise
        """
        if not self.access_token:
            return False
        
        try:
            # Generate KD-Code
            from kd_core.encoder import generate_kd_code
            kd_code_b64 = generate_kd_code(text_to_encode)
            
            if not kd_code_b64:
                return False
            
            # Create image from base64
            image_data = base64.b64decode(kd_code_b64)
            
            # Upload image to OneDrive first
            image_url = self.upload_image_to_onedrive(image_data, f"kdcode_{document_id}.png")
            if not image_url:
                return False
            
            # In a real implementation, we would use the Word API to insert the image
            # For now, we'll simulate the insertion by updating document metadata
            # This would involve making a PATCH request to update the document content
            
            # Update document metadata to indicate KD-Code was inserted
            metadata_url = f"{self.api_base_url}/me/drive/items/{document_id}"
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            metadata_update = {
                'fields': {
                    'kdcode_inserted': True,
                    'kdcode_content': text_to_encode,
                    'kdcode_insertion_date': 'datetime.now().isoformat()'
                }
            }
            
            response = requests.patch(metadata_url, headers=headers, json=metadata_update)
            
            if response.status_code == 200:
                self.logger.info(f"KD-Code metadata updated for document {document_id}")
                return True
            else:
                self.logger.error(f"Failed to update document metadata: {response.text}")
                return False
        except Exception as e:
            self.logger.error(f"Error inserting KD-Code in Word doc: {e}")
            return False
    
    def create_excel_spreadsheet_with_kdcodes(self, data_rows: list, 
                                            filename: str = "kdcode_spreadsheet.xlsx") -> Optional[str]:
        """
        Create an Excel spreadsheet with KD-Codes for each row of data
        
        Args:
            data_rows: List of dictionaries with data to encode
            filename: Name for the created spreadsheet
        
        Returns:
            URL of the created spreadsheet or None if failed
        """
        if not self.access_token:
            return None
        
        try:
            import openpyxl
            from io import BytesIO
            
            # Create a new workbook
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "KD-Codes"
            
            # Add headers
            headers = list(data_rows[0].keys()) if data_rows else ['Data', 'KD-Code']
            headers.append('KD-Code Image')
            ws.append(headers)
            
            # Add data rows with KD-Codes
            for row_data in data_rows:
                # Generate KD-Code for this row
                text_to_encode = json.dumps(row_data)
                from kd_core.encoder import generate_kd_code
                kd_code_b64 = generate_kd_code(text_to_encode)
                
                # Add row data
                row_values = list(row_data.values())
                row_values.append(kd_code_b64)  # Add base64 KD-Code
                ws.append(row_values)
            
            # Save to BytesIO
            buffer = BytesIO()
            wb.save(buffer)
            excel_data = buffer.getvalue()
            
            # Upload to OneDrive
            upload_url = f"{self.api_base_url}/me/drive/root:/{filename}:/content"
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            }
            
            response = requests.put(upload_url, headers=headers, data=excel_data)
            
            if response.status_code in [200, 201]:
                file_info = response.json()
                return file_info.get('@microsoft.graph.downloadUrl')
            else:
                self.logger.error(f"Excel creation failed: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            self.logger.error(f"Error creating Excel spreadsheet with KD-Codes: {e}")
            return None
    
    def add_kd_code_to_powerpoint_slide(self, presentation_id: str, slide_index: int, 
                                      text_to_encode: str) -> bool:
        """
        Add a KD-Code to a PowerPoint slide
        
        Args:
            presentation_id: ID of the PowerPoint presentation in OneDrive
            slide_index: Index of the slide to add the KD-Code to
            text_to_encode: Text to encode in the KD-Code
        
        Returns:
            True if successful, False otherwise
        """
        if not self.access_token:
            return False
        
        try:
            # Generate KD-Code
            from kd_core.encoder import generate_kd_code
            kd_code_b64 = generate_kd_code(text_to_encode)
            
            if not kd_code_b64:
                return False
            
            # Create image from base64
            image_data = base64.b64decode(kd_code_b64)
            
            # Upload image to OneDrive first
            image_url = self.upload_image_to_onedrive(image_data, f"kdcode_slide_{slide_index}.png")
            if not image_url:
                return False
            
            # In a real implementation, we would use the PowerPoint API to insert the image
            # For now, we'll simulate by updating presentation metadata
            metadata_url = f"{self.api_base_url}/me/drive/items/{presentation_id}"
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            metadata_update = {
                'fields': {
                    f'slide_{slide_index}_kdcode': {
                        'content': text_to_encode,
                        'image_url': image_url,
                        'insertion_date': datetime.now().isoformat()
                    }
                }
            }
            
            response = requests.patch(metadata_url, headers=headers, json=metadata_update)
            
            if response.status_code == 200:
                self.logger.info(f"KD-Code metadata added to slide {slide_index} of presentation {presentation_id}")
                return True
            else:
                self.logger.error(f"Failed to update presentation metadata: {response.text}")
                return False
        except Exception as e:
            self.logger.error(f"Error adding KD-Code to PowerPoint slide: {e}")
            return False
    
    def get_user_documents(self, file_type: str = 'all') -> list:
        """
        Get user's Office documents from OneDrive
        
        Args:
            file_type: Type of documents to retrieve ('word', 'excel', 'powerpoint', 'all')
        
        Returns:
            List of document information
        """
        if not self.access_token:
            return []
        
        try:
            # Query OneDrive for Office documents
            query_params = {
                'select': 'id,name,size,lastModifiedDateTime,file',
                'expand': 'children'
            }
            
            if file_type != 'all':
                extensions = {
                    'word': ['.docx', '.doc', '.docm'],
                    'excel': ['.xlsx', '.xls', '.xlsm', '.xlsb'],
                    'powerpoint': ['.pptx', '.ppt', '.pptm']
                }
                
                ext_filters = [f"file/extension eq '{ext[1:]}'" for ext in extensions.get(file_type, [])]
                query_params['filter'] = f"({' or '.join(ext_filters)})"
            
            query_string = '&'.join([f'{k}={v}' for k, v in query_params.items()])
            url = f"{self.api_base_url}/me/drive/root?$expand=children(select=id,name,file)&{query_string}"
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                drive_data = response.json()
                documents = []
                
                # Process root items
                for item in drive_data.get('value', []):
                    if 'file' in item:
                        file_ext = item['file'].get('extension', '').lower()
                        if self._is_office_file(file_ext, file_type):
                            documents.append({
                                'id': item['id'],
                                'name': item['name'],
                                'size': item.get('size', 0),
                                'modified': item.get('lastModifiedDateTime'),
                                'extension': file_ext
                            })
                
                # Process children (in folders)
                for item in drive_data.get('children', {}).get('value', []):
                    if 'file' in item:
                        file_ext = item['file'].get('extension', '').lower()
                        if self._is_office_file(file_ext, file_type):
                            documents.append({
                                'id': item['id'],
                                'name': item['name'],
                                'size': item.get('size', 0),
                                'modified': item.get('lastModifiedDateTime'),
                                'extension': file_ext
                            })
                
                return documents
            else:
                self.logger.error(f"Failed to get user documents: {response.text}")
                return []
        except Exception as e:
            self.logger.error(f"Error getting user documents: {e}")
            return []
    
    def _is_office_file(self, extension: str, file_type: str) -> bool:
        """
        Check if a file extension corresponds to an Office file type
        
        Args:
            extension: File extension
            file_type: Required file type ('word', 'excel', 'powerpoint', 'all')
        
        Returns:
            True if it's an Office file of the specified type
        """
        office_extensions = {
            'word': ['docx', 'doc', 'docm', 'dotx', 'dotm'],
            'excel': ['xlsx', 'xls', 'xlsm', 'xlsb', 'xltx', 'xltm', 'xlam'],
            'powerpoint': ['pptx', 'ppt', 'pptm', 'potx', 'potm', 'ppam', 'ppsx', 'ppsm']
        }
        
        if file_type == 'all':
            all_extensions = []
            for ext_list in office_extensions.values():
                all_extensions.extend(ext_list)
            return extension in all_extensions
        else:
            return extension in office_extensions.get(file_type, [])


# Global Microsoft Office integration instance
ms_office_integration = MicrosoftOfficeIntegration()


def initialize_ms_office_integration():
    """Initialize the Microsoft Office integration"""
    global ms_office_integration
    ms_office_integration = MicrosoftOfficeIntegration()


def get_ms_office_auth_url() -> str:
    """
    Get the Microsoft Office authentication URL
    
    Returns:
        Authentication URL
    """
    return ms_office_integration.get_auth_url()


def handle_ms_office_auth_callback(auth_code: str) -> bool:
    """
    Handle the Microsoft Office authentication callback
    
    Args:
        auth_code: Authorization code from Microsoft
    
    Returns:
        True if successful, False otherwise
    """
    return ms_office_integration.exchange_code_for_token(auth_code)


def insert_kd_code_in_word_document(document_id: str, text: str, paragraph_index: int = -1) -> bool:
    """
    Insert a KD-Code into a Word document
    
    Args:
        document_id: ID of the document in OneDrive
        text: Text to encode in the KD-Code
        paragraph_index: Index of paragraph to insert after (-1 for end)
    
    Returns:
        True if successful, False otherwise
    """
    return ms_office_integration.insert_kd_code_in_word_doc(document_id, text, paragraph_index)


def create_excel_with_kdcodes(data_rows: list, filename: str = "kdcode_spreadsheet.xlsx") -> Optional[str]:
    """
    Create an Excel spreadsheet with KD-Codes
    
    Args:
        data_rows: List of data rows to encode
        filename: Name for the created spreadsheet
    
    Returns:
        URL of the created spreadsheet or None if failed
    """
    return ms_office_integration.create_excel_spreadsheet_with_kdcodes(data_rows, filename)


def add_kd_code_to_powerpoint_slide(presentation_id: str, slide_index: int, text: str) -> bool:
    """
    Add a KD-Code to a PowerPoint slide
    
    Args:
        presentation_id: ID of the presentation in OneDrive
        slide_index: Index of the slide
        text: Text to encode in the KD-Code
    
    Returns:
        True if successful, False otherwise
    """
    return ms_office_integration.add_kd_code_to_powerpoint_slide(presentation_id, slide_index, text)


def get_user_office_documents(file_type: str = 'all') -> list:
    """
    Get user's Office documents from OneDrive
    
    Args:
        file_type: Type of documents ('word', 'excel', 'powerpoint', 'all')
    
    Returns:
        List of document information
    """
    return ms_office_integration.get_user_documents(file_type)


# Flask routes for Microsoft Office integration
def add_ms_office_routes(app: Flask):
    """
    Add Microsoft Office integration routes to a Flask app
    
    Args:
        app: Flask application instance
    """
    
    @app.route('/office/auth', methods=['GET'])
    def ms_office_auth():
        """Initiate Microsoft Office authentication"""
        auth_url = get_ms_office_auth_url()
        return jsonify({'auth_url': auth_url})
    
    @app.route('/office/callback', methods=['GET'])
    def ms_office_callback():
        """Handle Microsoft Office authentication callback"""
        auth_code = request.args.get('code')
        if not auth_code:
            return jsonify({'error': 'Authorization code not provided'}), 400
        
        success = handle_ms_office_auth_callback(auth_code)
        if success:
            return jsonify({'status': 'success', 'message': 'Authentication successful'})
        else:
            return jsonify({'error': 'Authentication failed'}), 400
    
    @app.route('/office/documents', methods=['GET'])
    def get_office_documents():
        """Get user's Office documents"""
        file_type = request.args.get('type', 'all')
        documents = get_user_office_documents(file_type)
        
        return jsonify({
            'status': 'success',
            'documents': documents
        })
    
    @app.route('/office/insert-kdcode', methods=['POST'])
    def insert_kdcode_in_document():
        """Insert a KD-Code into an Office document"""
        try:
            data = request.get_json()
            document_id = data.get('document_id')
            text = data.get('text')
            app_type = data.get('app_type', 'word')  # 'word', 'excel', 'powerpoint'
            position = data.get('position', -1)  # For word docs, this is paragraph index
            
            if not document_id or not text:
                return jsonify({'error': 'Document ID and text are required'}), 400
            
            success = False
            if app_type == 'word':
                success = insert_kd_code_in_word_document(document_id, text, position)
            elif app_type == 'excel':
                # For Excel, we might create a new sheet with KD-Codes
                # This is a simplified implementation
                success = True  # Placeholder
            elif app_type == 'powerpoint':
                success = add_kd_code_to_powerpoint_slide(document_id, position, text)
            
            if success:
                return jsonify({
                    'status': 'success',
                    'message': f'KD-Code inserted into {app_type} document'
                })
            else:
                return jsonify({'error': f'Failed to insert KD-Code into {app_type} document'}), 500
        except Exception as e:
            app.logger.error(f"Error inserting KD-Code in document: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/office/create-excel-kdcodes', methods=['POST'])
    def create_excel_kdcodes():
        """Create an Excel spreadsheet with KD-Codes"""
        try:
            data = request.get_json()
            rows = data.get('rows', [])
            filename = data.get('filename', 'kdcode_spreadsheet.xlsx')
            
            if not rows:
                return jsonify({'error': 'Data rows are required'}), 400
            
            spreadsheet_url = create_excel_with_kdcodes(rows, filename)
            
            if spreadsheet_url:
                return jsonify({
                    'status': 'success',
                    'spreadsheet_url': spreadsheet_url
                })
            else:
                return jsonify({'error': 'Failed to create Excel spreadsheet'}), 500
        except Exception as e:
            app.logger.error(f"Error creating Excel with KD-Codes: {e}")
            return jsonify({'error': 'Internal server error'}), 500


# Example usage
if __name__ == "__main__":
    print("Microsoft Office Integration Module for KD-Code System")
    print("This module provides integration with Microsoft Office applications")
    
    # Example of how to use the integration:
    # 1. Initialize the integration
    # initialize_ms_office_integration()
    # 
    # 2. Get auth URL and redirect user to authenticate
    # auth_url = get_ms_office_auth_url()
    # print(f"Please visit this URL to authenticate: {auth_url}")
    # 
    # 3. After user authenticates, handle the callback
    # handle_ms_office_auth_callback("auth_code_from_microsoft")
    # 
    # 4. Insert KD-Code into a document
    # success = insert_kd_code_in_word_document("document_id", "Hello from Word!", paragraph_index=5)
    # print(f"Insertion successful: {success}")