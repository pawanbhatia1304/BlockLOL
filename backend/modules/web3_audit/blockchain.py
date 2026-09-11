import json
import logging
import os
import time
from typing import Dict, Any, Optional
from web3 import Web3

logger = logging.getLogger(__name__)

LOCAL_LOG_FILE = "backend/local_audit_log.json"

class BlockchainClient:
    def __init__(self, rpc_url: str, contract_address: str, private_key: str, abi: list):
        self.rpc_url = rpc_url
        self.contract_address = contract_address
        self.private_key = private_key
        self.abi = abi
        
        self.web3 = None
        if rpc_url:
            try:
                self.web3 = Web3(Web3.HTTPProvider(rpc_url))
                if self.web3.is_connected():
                    self.contract = self.web3.eth.contract(address=self.contract_address, abi=self.abi)
                    # Get account from private key
                    if self.private_key:
                        self.account = self.web3.eth.account.from_key(self.private_key)
                else:
                    logger.warning("Web3 is not connected")
                    self.web3 = None
            except Exception as e:
                logger.warning(f"Error connecting to blockchain: {e}")
                self.web3 = None

    def _store_local(self, job_id: str, ipfs_cid: str, data_hash: str):
        record = {
            "job_id": job_id,
            "ipfs_cid": ipfs_cid,
            "data_hash": data_hash,
            "timestamp": int(time.time()),
            "tx_hash": "local"
        }
        
        logs = []
        if os.path.exists(LOCAL_LOG_FILE):
            try:
                with open(LOCAL_LOG_FILE, "r") as f:
                    logs = json.load(f)
            except Exception:
                pass
        
        logs.append(record)
        
        try:
            os.makedirs(os.path.dirname(LOCAL_LOG_FILE), exist_ok=True)
            with open(LOCAL_LOG_FILE, "w") as f:
                json.dump(logs, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving to local audit log: {e}")

    async def log_audit_trail(self, job_id: str, ipfs_cid: str, data_hash: str) -> str:
        if not self.web3 or not self.private_key:
            logger.warning("Blockchain unavailable, storing record locally")
            self._store_local(job_id, ipfs_cid, data_hash)
            return "local_fallback"
            
        try:
            nonce = self.web3.eth.get_transaction_count(self.account.address)
            
            # Build transaction
            tx = self.contract.functions.logAuditTrail(
                job_id, ipfs_cid, data_hash
            ).build_transaction({
                'chainId': self.web3.eth.chain_id,
                'gas': 2000000,
                'gasPrice': self.web3.eth.gas_price,
                'nonce': nonce,
            })
            
            signed_tx = self.web3.eth.account.sign_transaction(tx, private_key=self.private_key)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            return self.web3.to_hex(tx_hash)
            
        except Exception as e:
            logger.error(f"Error sending transaction: {e}")
            self._store_local(job_id, ipfs_cid, data_hash)
            return "local_fallback"

    async def get_audit_trail(self, job_id: str) -> dict:
        if not self.web3:
            logger.warning("Blockchain unavailable")
            return {}
            
        try:
            result = self.contract.functions.getAuditTrail(job_id).call()
            return {
                "ipfs_cid": result[0],
                "data_hash": result[1],
                "timestamp": result[2]
            }
        except Exception as e:
            logger.error(f"Error reading from blockchain: {e}")
            return {}
