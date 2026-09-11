import json
import logging
import aiohttp
from typing import Dict, Any, Optional

try:
    from lighthouseweb3 import Lighthouse
    HAS_LIGHTHOUSE = True
except ImportError:
    HAS_LIGHTHOUSE = False

logger = logging.getLogger(__name__)

class LighthouseClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        if not self.api_key:
            logger.warning("Lighthouse API key is missing.")

    async def upload_json(self, data: dict, name: str) -> str:
        if not self.api_key:
            logger.warning("No API key, returning empty CID")
            return ""
        
        text = json.dumps(data)
        
        if HAS_LIGHTHOUSE:
            try:
                lh = Lighthouse(token=self.api_key)
                # Attempting to use the SDK if available
                response = lh.upload_text(text, name)
                if response and "Hash" in response:
                    return response["Hash"]
            except Exception as e:
                logger.warning(f"lighthouseweb3 package failed, falling back: {e}")

        # REST fallback / primary async approach
        try:
            url = "https://node.lighthouse.storage/api/v0/add"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            # lighthouse expects multipart/form-data
            form = aiohttp.FormData()
            form.add_field('file', text.encode('utf-8'), filename=f"{name}.json", content_type='application/json')
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, data=form) as response:
                    if response.status == 200:
                        res_json = await response.json()
                        return res_json.get("Hash", "")
                    else:
                        text_resp = await response.text()
                        logger.error(f"Lighthouse upload failed: {text_resp}")
                        return ""
        except Exception as e:
            logger.error(f"Error uploading to Lighthouse: {e}")
            return ""

    async def get_file_info(self, cid: str) -> dict:
        url = f"https://gateway.lighthouse.storage/ipfs/{cid}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        try:
                            data = await response.json()
                            return data
                        except Exception:
                            # Might not be json
                            text = await response.text()
                            return {"content": text[:100]}
                    else:
                        logger.error(f"Failed to fetch {cid}: {response.status}")
                        return {}
        except Exception as e:
            logger.error(f"Error fetching CID {cid}: {e}")
            return {}
