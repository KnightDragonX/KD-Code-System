"""
Salesforce Integration Module for KD-Code System
Enables integration with Salesforce for CRM and business operations
"""

import requests
import json
from typing import Dict, Any, Optional, List
import logging
from urllib.parse import urljoin


class SalesforceIntegration:
    """
    Integration system for connecting KD-Code system with Salesforce
    """
    
    def __init__(self, instance_url: str = None, access_token: str = None):
        """
        Initialize the Salesforce integration
        
        Args:
            instance_url: Salesforce instance URL (e.g., https://yourorg.salesforce.com)
            access_token: Salesforce access token for API access
        """
        self.instance_url = instance_url
        self.access_token = access_token
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)
        
        if self.access_token:
            self.session.headers.update({
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            })
    
    def connect(self, username: str, password: str, security_token: str, 
                client_id: str, client_secret: str) -> bool:
        """
        Connect to Salesforce using username-password OAuth flow
        
        Args:
            username: Salesforce username
            password: Salesforce password
            security_token: Salesforce security token
            client_id: Connected app consumer key
            client_secret: Connected app consumer secret
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Construct login URL
            auth_url = "https://login.salesforce.com/services/oauth2/token"
            
            # Prepare authentication data
            auth_data = {
                'grant_type': 'password',
                'client_id': client_id,
                'client_secret': client_secret,
                'username': username,
                'password': password + security_token  # Password + security token
            }
            
            # Make authentication request
            response = requests.post(auth_url, data=auth_data)
            
            if response.status_code == 200:
                auth_result = response.json()
                self.access_token = auth_result['access_token']
                self.instance_url = auth_result['instance_url']
                
                # Update session headers
                self.session.headers.update({
                    'Authorization': f'Bearer {self.access_token}',
                    'Content-Type': 'application/json'
                })
                
                self.logger.info("Successfully connected to Salesforce")
                return True
            else:
                self.logger.error(f"Salesforce authentication failed: {response.text}")
                return False
        except Exception as e:
            self.logger.error(f"Error connecting to Salesforce: {e}")
            return False
    
    def create_kd_code_record(self, kd_code_data: Dict[str, Any]) -> Optional[str]:
        """
        Create a KD-Code record in Salesforce
        
        Args:
            kd_code_data: Dictionary containing KD-Code information
        
        Returns:
            Salesforce record ID if successful, None otherwise
        """
        if not self.access_token or not self.instance_url:
            self.logger.error("Not connected to Salesforce")
            return None
        
        try:
            # Define the Salesforce object to create (custom object assumed)
            sf_object = 'KD_Code__c'  # Custom object in Salesforce
            
            # Map KD-Code data to Salesforce fields
            salesforce_data = {
                'Name': kd_code_data.get('code_id', 'Unnamed KD-Code'),
                'Content__c': kd_code_data.get('content', ''),
                'Encoded_Image__c': kd_code_data.get('image_data', '')[:131072],  # Limit for Salesforce text area
                'Status__c': kd_code_data.get('status', 'Active'),
                'Created_By_User__c': kd_code_data.get('creator_id', ''),
                'Scan_Count__c': kd_code_data.get('scan_count', 0),
                'Segments_Per_Ring__c': kd_code_data.get('segments_per_ring', 16),
                'Anchor_Radius__c': kd_code_data.get('anchor_radius', 10),
                'Ring_Width__c': kd_code_data.get('ring_width', 15),
                'Scale_Factor__c': kd_code_data.get('scale_factor', 5)
            }
            
            # Add optional fields if present
            if 'created_at' in kd_code_data:
                salesforce_data['Created_Date__c'] = kd_code_data['created_at']
            
            if 'expires_at' in kd_code_data:
                salesforce_data['Expiration_Date__c'] = kd_code_data['expires_at']
            
            if 'tags' in kd_code_data:
                salesforce_data['Tags__c'] = json.dumps(kd_code_data['tags'])
            
            # Construct API URL
            api_url = urljoin(self.instance_url, f'/services/data/v58.0/sobjects/{sf_object}/')
            
            # Create the record
            response = self.session.post(api_url, json=salesforce_data)
            
            if response.status_code == 201:  # Created
                result = response.json()
                record_id = result.get('id')
                self.logger.info(f"KD-Code record created in Salesforce with ID: {record_id}")
                return record_id
            else:
                self.logger.error(f"Failed to create KD-Code record: {response.text}")
                return None
        except Exception as e:
            self.logger.error(f"Error creating KD-Code record in Salesforce: {e}")
            return None
    
    def update_kd_code_record(self, record_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a KD-Code record in Salesforce
        
        Args:
            record_id: Salesforce record ID
            updates: Dictionary of field updates
        
        Returns:
            True if successful, False otherwise
        """
        if not self.access_token or not self.instance_url:
            self.logger.error("Not connected to Salesforce")
            return False
        
        try:
            # Define the Salesforce object
            sf_object = 'KD_Code__c'
            
            # Construct API URL
            api_url = urljoin(self.instance_url, f'/services/data/v58.0/sobjects/{sf_object}/{record_id}')
            
            # Update the record
            response = self.session.patch(api_url, json=updates)
            
            if response.status_code == 204:  # Success, no content
                self.logger.info(f"KD-Code record updated in Salesforce: {record_id}")
                return True
            else:
                self.logger.error(f"Failed to update KD-Code record: {response.text}")
                return False
        except Exception as e:
            self.logger.error(f"Error updating KD-Code record in Salesforce: {e}")
            return False
    
    def get_kd_code_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a KD-Code record from Salesforce
        
        Args:
            record_id: Salesforce record ID
        
        Returns:
            KD-Code record data or None if not found
        """
        if not self.access_token or not self.instance_url:
            self.logger.error("Not connected to Salesforce")
            return None
        
        try:
            # Define the Salesforce object
            sf_object = 'KD_Code__c'
            
            # Construct API URL
            api_url = urljoin(self.instance_url, f'/services/data/v58.0/sobjects/{sf_object}/{record_id}')
            
            # Retrieve the record
            response = self.session.get(api_url)
            
            if response.status_code == 200:
                record_data = response.json()
                
                # Map Salesforce fields back to KD-Code format
                kd_code_data = {
                    'salesforce_id': record_data.get('Id'),
                    'code_id': record_data.get('Name'),
                    'content': record_data.get('Content__c', ''),
                    'image_data': record_data.get('Encoded_Image__c', ''),
                    'status': record_data.get('Status__c', 'Active'),
                    'creator_id': record_data.get('Created_By_User__c', ''),
                    'scan_count': record_data.get('Scan_Count__c', 0),
                    'segments_per_ring': record_data.get('Segments_Per_Ring__c', 16),
                    'anchor_radius': record_data.get('Anchor_Radius__c', 10),
                    'ring_width': record_data.get('Ring_Width__c', 15),
                    'scale_factor': record_data.get('Scale_Factor__c', 5),
                    'created_at': record_data.get('Created_Date__c'),
                    'expires_at': record_data.get('Expiration_Date__c'),
                    'tags': json.loads(record_data.get('Tags__c', '[]')) if record_data.get('Tags__c') else []
                }
                
                return kd_code_data
            else:
                self.logger.error(f"Failed to retrieve KD-Code record: {response.text}")
                return None
        except Exception as e:
            self.logger.error(f"Error retrieving KD-Code record from Salesforce: {e}")
            return None
    
    def search_kd_codes(self, query: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for KD-Code records in Salesforce
        
        Args:
            query: SOQL query to filter results (optional)
            limit: Maximum number of results to return
        
        Returns:
            List of KD-Code records
        """
        if not self.access_token or not self.instance_url:
            self.logger.error("Not connected to Salesforce")
            return []
        
        try:
            # Build SOQL query
            if query:
                soql = query
            else:
                soql = f"SELECT Id, Name, Content__c, Status__c, Created_By_User__c, Scan_Count__c FROM KD_Code__c LIMIT {limit}"
            
            # Construct API URL
            api_url = urljoin(self.instance_url, f'/services/data/v58.0/query/')
            params = {'q': soql}
            
            # Execute query
            response = self.session.get(api_url, params=params)
            
            if response.status_code == 200:
                result = response.json()
                records = []
                
                for record in result.get('records', []):
                    kd_code_data = {
                        'salesforce_id': record.get('Id'),
                        'code_id': record.get('Name'),
                        'content': record.get('Content__c', ''),
                        'status': record.get('Status__c', 'Active'),
                        'creator_id': record.get('Created_By_User__c', ''),
                        'scan_count': record.get('Scan_Count__c', 0)
                    }
                    records.append(kd_code_data)
                
                return records
            else:
                self.logger.error(f"Failed to search KD-Code records: {response.text}")
                return []
        except Exception as e:
            self.logger.error(f"Error searching KD-Code records in Salesforce: {e}")
            return []
    
    def sync_kd_code_to_salesforce(self, kd_code_info: Dict[str, Any]) -> Optional[str]:
        """
        Sync a KD-Code to Salesforce, creating or updating as needed
        
        Args:
            kd_code_info: KD-Code information to sync
        
        Returns:
            Salesforce record ID or None if failed
        """
        # First, check if a record already exists with this code_id
        existing_records = self.search_kd_codes(
            query=f"SELECT Id FROM KD_Code__c WHERE Name = '{kd_code_info.get('code_id', '')}'",
            limit=1
        )
        
        if existing_records:
            # Update existing record
            record_id = existing_records[0]['salesforce_id']
            updates = {
                'Content__c': kd_code_info.get('content', ''),
                'Status__c': kd_code_info.get('status', 'Active'),
                'Scan_Count__c': kd_code_info.get('scan_count', 0)
            }
            
            success = self.update_kd_code_record(record_id, updates)
            return record_id if success else None
        else:
            # Create new record
            return self.create_kd_code_record(kd_code_info)
    
    def get_salesforce_objects(self) -> List[Dict[str, str]]:
        """
        Get available Salesforce objects that can be used for KD-Code integration
        
        Returns:
            List of available objects
        """
        if not self.access_token or not self.instance_url:
            self.logger.error("Not connected to Salesforce")
            return []
        
        try:
            # Get available objects
            api_url = urljoin(self.instance_url, '/services/data/v58.0/sobjects/')
            response = self.session.get(api_url)
            
            if response.status_code == 200:
                result = response.json()
                objects = []
                
                for obj in result.get('sobjects', []):
                    if obj.get('createable', False) and obj.get('updateable', False):
                        objects.append({
                            'name': obj['name'],
                            'label': obj['label'],
                            'custom': obj.get('custom', False)
                        })
                
                return objects
            else:
                self.logger.error(f"Failed to retrieve Salesforce objects: {response.text}")
                return []
        except Exception as e:
            self.logger.error(f"Error retrieving Salesforce objects: {e}")
            return []


# Global Salesforce integration instance
salesforce_integration = SalesforceIntegration()


def initialize_salesforce_integration(instance_url: str = None, access_token: str = None):
    """
    Initialize the Salesforce integration
    
    Args:
        instance_url: Salesforce instance URL
        access_token: Salesforce access token
    """
    global salesforce_integration
    salesforce_integration = SalesforceIntegration(instance_url, access_token)


def connect_to_salesforce(username: str, password: str, security_token: str, 
                        client_id: str, client_secret: str) -> bool:
    """
    Connect to Salesforce using credentials
    
    Args:
        username: Salesforce username
        password: Salesforce password
        security_token: Salesforce security token
        client_id: Connected app consumer key
        client_secret: Connected app consumer secret
    
    Returns:
        True if connection successful, False otherwise
    """
    return salesforce_integration.connect(username, password, security_token, client_id, client_secret)


def sync_kd_code_to_sf(kd_code_data: Dict[str, Any]) -> Optional[str]:
    """
    Sync a KD-Code to Salesforce
    
    Args:
        kd_code_data: KD-Code information to sync
    
    Returns:
        Salesforce record ID or None if failed
    """
    return salesforce_integration.sync_kd_code_to_salesforce(kd_code_data)


def create_salesforce_kd_code_record(kd_code_data: Dict[str, Any]) -> Optional[str]:
    """
    Create a KD-Code record in Salesforce
    
    Args:
        kd_code_data: KD-Code information to store
    
    Returns:
        Salesforce record ID or None if failed
    """
    return salesforce_integration.create_kd_code_record(kd_code_data)


def update_salesforce_kd_code_record(record_id: str, updates: Dict[str, Any]) -> bool:
    """
    Update a KD-Code record in Salesforce
    
    Args:
        record_id: Salesforce record ID
        updates: Dictionary of field updates
    
    Returns:
        True if successful, False otherwise
    """
    return salesforce_integration.update_kd_code_record(record_id, updates)


def get_salesforce_kd_code_record(record_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a KD-Code record from Salesforce
    
    Args:
        record_id: Salesforce record ID
    
    Returns:
        KD-Code record data or None if not found
    """
    return salesforce_integration.get_kd_code_record(record_id)


def search_salesforce_kd_codes(query: str = None, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search for KD-Code records in Salesforce
    
    Args:
        query: SOQL query to filter results (optional)
        limit: Maximum number of results to return
    
    Returns:
        List of KD-Code records
    """
    return salesforce_integration.search_kd_codes(query, limit)


def get_available_salesforce_objects() -> List[Dict[str, str]]:
    """
    Get available Salesforce objects for integration
    
    Returns:
        List of available objects
    """
    return salesforce_integration.get_salesforce_objects()


# Example usage
if __name__ == "__main__":
    print("Salesforce Integration Module for KD-Code System")
    print("This module provides functions to integrate KD-Codes with Salesforce CRM")
    
    # Example of how to use the integration:
    # 1. Initialize the integration
    # initialize_salesforce_integration("https://yourorg.salesforce.com", "your_access_token")
    
    # 2. Or connect using credentials
    # success = connect_to_salesforce(
    #     username="your_username",
    #     password="your_password", 
    #     security_token="your_security_token",
    #     client_id="your_connected_app_client_id",
    #     client_secret="your_connected_app_client_secret"
    # )
    
    # 3. Sync a KD-Code to Salesforce
    # kd_code_info = {
    #     'code_id': 'kd_code_123',
    #     'content': 'Sample KD-Code content',
    #     'status': 'active',
    #     'creator_id': 'user_456',
    #     'scan_count': 5
    # }
    # sf_record_id = sync_kd_code_to_sf(kd_code_info)
    # print(f"Synced to Salesforce with record ID: {sf_record_id}")
    
    print("Module ready for Salesforce integration")