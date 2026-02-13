"""
Blockchain Verification Module for KD-Code Authenticity
Implements blockchain-based verification for KD-Code authenticity
"""

import hashlib
import json
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import requests
import base64
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Cipher import PKCS1_OAEP
import secrets


@dataclass
class Block:
    """Represents a block in the KD-Code blockchain"""
    index: int
    timestamp: float
    data: str  # Hash of KD-Code and metadata
    previous_hash: str
    nonce: int = 0
    hash: str = ""
    
    def calculate_hash(self) -> str:
        """Calculate the hash of the block"""
        block_string = f"{self.index}{self.timestamp}{self.data}{self.previous_hash}{self.nonce}"
        return hashlib.sha256(block_string.encode()).hexdigest()


class KDCodeBlockchain:
    """Blockchain implementation for KD-Code authenticity verification"""
    
    def __init__(self, difficulty: int = 4):
        """
        Initialize the blockchain
        
        Args:
            difficulty: Mining difficulty (number of leading zeros required)
        """
        self.chain: List[Block] = []
        self.difficulty = difficulty
        self.pending_verification = []  # Pending KD-Codes awaiting verification
        self.mining_reward = 1  # Reward for mining a block
        
        # Create genesis block
        self.create_genesis_block()
    
    def create_genesis_block(self):
        """Create the first block in the chain"""
        genesis_block = Block(
            index=0,
            timestamp=time.time(),
            data="Genesis Block - KD-Code Blockchain",
            previous_hash="0" * 64  # 64 zeros
        )
        genesis_block.hash = genesis_block.calculate_hash()
        self.chain.append(genesis_block)
    
    def get_latest_block(self) -> Block:
        """Get the most recent block in the chain"""
        return self.chain[-1]
    
    def add_verification_request(self, kd_code_hash: str, metadata: Dict) -> bool:
        """
        Add a KD-Code for verification to the pending list
        
        Args:
            kd_code_hash: Hash of the KD-Code to verify
            metadata: Additional metadata about the KD-Code
        
        Returns:
            True if successfully added, False otherwise
        """
        verification_data = {
            'kd_code_hash': kd_code_hash,
            'metadata': metadata,
            'timestamp': time.time(),
            'verifier': 'system'  # Could be replaced with actual verifier identity
        }
        
        self.pending_verification.append(verification_data)
        return True
    
    def mine_pending_verifications(self, miner_address: str) -> Optional[Block]:
        """
        Mine pending verification requests into a new block
        
        Args:
            miner_address: Address of the miner performing the work
        
        Returns:
            Mined block or None if no pending verifications
        """
        if len(self.pending_verification) == 0:
            return None
        
        # Create data for the block (serialize pending verifications)
        block_data = json.dumps({
            'verifications': self.pending_verification,
            'miner': miner_address,
            'reward': self.mining_reward
        }, sort_keys=True)
        
        # Create new block
        new_block = Block(
            index=len(self.chain),
            timestamp=time.time(),
            data=block_data,
            previous_hash=self.get_latest_block().hash
        )
        
        # Perform proof of work
        new_block = self.proof_of_work(new_block)
        
        # Add block to chain
        self.chain.append(new_block)
        
        # Clear pending verifications
        self.pending_verification = []
        
        return new_block
    
    def proof_of_work(self, block: Block) -> Block:
        """
        Perform proof of work to mine a block
        
        Args:
            block: Block to mine
        
        Returns:
            Mined block with correct nonce
        """
        target = '0' * self.difficulty
        
        while block.hash[:self.difficulty] != target:
            block.nonce += 1
            block.hash = block.calculate_hash()
        
        return block
    
    def is_chain_valid(self) -> bool:
        """
        Validate the entire blockchain
        
        Returns:
            True if chain is valid, False otherwise
        """
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i-1]
            
            # Check if current block hash is valid
            if current_block.hash != current_block.calculate_hash():
                return False
            
            # Check if previous hash matches
            if current_block.previous_hash != previous_block.hash:
                return False
        
        return True
    
    def verify_kd_code(self, kd_code_hash: str) -> Dict[str, any]:
        """
        Verify if a KD-Code exists in the blockchain
        
        Args:
            kd_code_hash: Hash of the KD-Code to verify
        
        Returns:
            Verification result with details
        """
        # Search through all blocks for the KD-Code hash
        for block in self.chain:
            try:
                block_data = json.loads(block.data)
                if 'verifications' in block_data:
                    for verification in block_data['verifications']:
                        if verification.get('kd_code_hash') == kd_code_hash:
                            return {
                                'valid': True,
                                'block_index': block.index,
                                'timestamp': verification.get('timestamp'),
                                'metadata': verification.get('metadata', {}),
                                'verified_at': block.timestamp
                            }
            except json.JSONDecodeError:
                # Skip blocks with invalid JSON data
                continue
        
        return {
            'valid': False,
            'error': 'KD-Code not found in blockchain'
        }
    
    def get_verification_history(self, kd_code_hash: str) -> List[Dict]:
        """
        Get the verification history for a KD-Code
        
        Args:
            kd_code_hash: Hash of the KD-Code to lookup
        
        Returns:
            List of verification records
        """
        history = []
        
        for block in self.chain:
            try:
                block_data = json.loads(block.data)
                if 'verifications' in block_data:
                    for verification in block_data['verifications']:
                        if verification.get('kd_code_hash') == kd_code_hash:
                            history.append({
                                'block_index': block.index,
                                'timestamp': verification.get('timestamp'),
                                'metadata': verification.get('metadata', {}),
                                'miner': block_data.get('miner'),
                                'block_timestamp': block.timestamp
                            })
            except json.JSONDecodeError:
                continue
        
        return history


class KDCodeAuthenticator:
    """Handles blockchain-based authentication for KD-Codes"""
    
    def __init__(self):
        self.blockchain = KDCodeBlockchain(difficulty=3)  # Lower difficulty for testing
        self.private_key = None
        self.public_key = None
        self._generate_keys()
    
    def _generate_keys(self):
        """Generate RSA key pair for signing"""
        key = RSA.generate(2048)
        self.private_key = key
        self.public_key = key.publickey()
    
    def sign_kd_code_data(self, kd_code_data: str) -> str:
        """
        Sign KD-Code data with private key
        
        Args:
            kd_code_data: Data to sign
        
        Returns:
            Base64 encoded signature
        """
        if not self.private_key:
            raise ValueError("Private key not available")
        
        # Hash the data
        hashed = SHA256.new(kd_code_data.encode('utf-8'))
        
        # Sign the hash
        signature = pkcs1_15.new(self.private_key).sign(hashed)
        
        # Return base64 encoded signature
        return base64.b64encode(signature).decode('utf-8')
    
    def verify_signature(self, kd_code_data: str, signature: str) -> bool:
        """
        Verify a signature for KD-Code data
        
        Args:
            kd_code_data: Original data that was signed
            signature: Base64 encoded signature
        
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            # Decode the signature
            decoded_sig = base64.b64decode(signature.encode('utf-8'))
            
            # Hash the data
            hashed = SHA256.new(kd_code_data.encode('utf-8'))
            
            # Verify the signature
            pkcs1_15.new(self.public_key).verify(hashed, decoded_sig)
            return True
        except (ValueError, TypeError):
            return False
    
    def register_kd_code(self, text: str, additional_metadata: Dict = None) -> Dict[str, any]:
        """
        Register a KD-Code in the blockchain for authenticity verification
        
        Args:
            text: Original text that was encoded in the KD-Code
            additional_metadata: Additional metadata to store with the verification
        
        Returns:
            Registration result with transaction details
        """
        if additional_metadata is None:
            additional_metadata = {}
        
        # Create a hash of the text
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        
        # Create metadata
        metadata = {
            'original_text_hash': text_hash,
            'creation_timestamp': time.time(),
            'additional_metadata': additional_metadata
        }
        
        # Add to verification queue
        success = self.blockchain.add_verification_request(text_hash, metadata)
        
        if success:
            return {
                'status': 'pending',
                'kd_code_hash': text_hash,
                'message': 'KD-Code registered for blockchain verification. Awaiting mining.'
            }
        else:
            return {
                'status': 'error',
                'kd_code_hash': text_hash,
                'error': 'Failed to register KD-Code for verification'
            }
    
    def authenticate_kd_code(self, kd_code_hash: str) -> Dict[str, any]:
        """
        Authenticate a KD-Code against the blockchain
        
        Args:
            kd_code_hash: Hash of the KD-Code to authenticate
        
        Returns:
            Authentication result
        """
        return self.blockchain.verify_kd_code(kd_code_hash)
    
    def get_authenticity_proof(self, kd_code_hash: str) -> Dict[str, any]:
        """
        Get detailed authenticity proof for a KD-Code
        
        Args:
            kd_code_hash: Hash of the KD-Code to check
        
        Returns:
            Detailed authenticity proof
        """
        verification_result = self.authenticate_kd_code(kd_code_hash)
        
        if verification_result['valid']:
            # Get full history
            history = self.blockchain.get_verification_history(kd_code_hash)
            
            return {
                'authenticated': True,
                'kd_code_hash': kd_code_hash,
                'verification_details': verification_result,
                'history': history,
                'blockchain_valid': self.blockchain.is_chain_valid()
            }
        else:
            return {
                'authenticated': False,
                'kd_code_hash': kd_code_hash,
                'error': verification_result.get('error', 'Unknown error'),
                'blockchain_valid': self.blockchain.is_chain_valid()
            }
    
    def mine_verification_block(self, miner_address: str = "system_miner") -> Dict[str, any]:
        """
        Mine a block containing pending verifications
        
        Args:
            miner_address: Address of the miner (for reward purposes)
        
        Returns:
            Mining result
        """
        mined_block = self.blockchain.mine_pending_verifications(miner_address)
        
        if mined_block:
            return {
                'status': 'success',
                'block_index': mined_block.index,
                'block_hash': mined_block.hash,
                'verifications_processed': len(mined_block.data),
                'message': f'Mined block #{mined_block.index} with {len(mined_block.data)} verifications'
            }
        else:
            return {
                'status': 'no_work',
                'message': 'No pending verifications to mine'
            }


# Global authenticator instance
authenticator = KDCodeAuthenticator()


def initialize_blockchain_auth():
    """Initialize the blockchain authentication system"""
    global authenticator
    authenticator = KDCodeAuthenticator()


def register_kd_code_for_auth(text: str, metadata: Dict = None) -> Dict[str, any]:
    """
    Register a KD-Code for blockchain authentication
    
    Args:
        text: Original text that was encoded
        metadata: Additional metadata
    
    Returns:
        Registration result
    """
    return authenticator.register_kd_code(text, metadata)


def authenticate_kd_code(kd_code_hash: str) -> Dict[str, any]:
    """
    Authenticate a KD-Code against the blockchain
    
    Args:
        kd_code_hash: Hash of the KD-Code to authenticate
    
    Returns:
        Authentication result
    """
    return authenticator.authenticate_kd_code(kd_code_hash)


def get_authenticity_proof(kd_code_hash: str) -> Dict[str, any]:
    """
    Get detailed authenticity proof for a KD-Code
    
    Args:
        kd_code_hash: Hash of the KD-Code to check
    
    Returns:
        Detailed authenticity proof
    """
    return authenticator.get_authenticity_proof(kd_code_hash)


def mine_auth_block(miner_address: str = "system") -> Dict[str, any]:
    """
    Mine a block of pending verifications
    
    Args:
        miner_address: Address of the miner
    
    Returns:
        Mining result
    """
    return authenticator.mine_verification_block(miner_address)


def is_blockchain_valid() -> bool:
    """
    Check if the blockchain is valid
    
    Returns:
        True if blockchain is valid, False otherwise
    """
    return authenticator.blockchain.is_chain_valid()


# Example usage
if __name__ == "__main__":
    # Initialize the blockchain authentication system
    initialize_blockchain_auth()
    
    # Register a KD-Code for authentication
    result = register_kd_code_for_auth("Hello, Blockchain-Verified KD-Code!", {
        'creator': 'system',
        'purpose': 'testing',
        'timestamp': time.time()
    })
    
    print(f"Registration result: {result}")
    
    # Mine the verification block
    mine_result = mine_auth_block()
    print(f"Mining result: {mine_result}")
    
    # Verify the KD-Code
    if 'kd_code_hash' in result:
        auth_result = authenticate_kd_code(result['kd_code_hash'])
        print(f"Authentication result: {auth_result}")
        
        # Get detailed proof
        proof = get_authenticity_proof(result['kd_code_hash'])
        print(f"Authenticity proof: {proof}")
    
    # Check blockchain validity
    is_valid = is_blockchain_valid()
    print(f"Blockchain validity: {is_valid}")