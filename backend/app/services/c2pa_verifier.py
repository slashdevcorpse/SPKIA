"""
C2PA verification service
Validates C2PA manifests and trust chains
"""
import logging
from typing import Optional, Dict, Any
from pathlib import Path
import json

from app.models.database import C2PAResult
from app.config import settings

logger = logging.getLogger(__name__)


class C2PAVerifier:
    """C2PA manifest verification service"""
    
    def __init__(self):
        """Initialize C2PA verifier with trust anchors"""
        self.trust_anchors_path = Path(settings.c2pa_trust_anchors_path)
        self.strict_validation = settings.c2pa_validation_strict
        self._load_trust_anchors()
        
    def _load_trust_anchors(self):
        """Load trusted certificate authorities"""
        try:
            if not self.trust_anchors_path.exists():
                logger.warning(f"C2PA trust anchors path not found: {self.trust_anchors_path}")
                self.trust_anchors = []
                return
                
            self.trust_anchors = []
            for cert_file in self.trust_anchors_path.glob("*.pem"):
                with open(cert_file, 'r') as f:
                    self.trust_anchors.append(f.read())
                    
            logger.info(f"Loaded {len(self.trust_anchors)} C2PA trust anchors")
        except Exception as e:
            logger.error(f"Failed to load C2PA trust anchors: {e}")
            self.trust_anchors = []
    
    async def verify(self, file_path: Path) -> C2PAResult:
        """
        Verify C2PA manifest in media file
        
        Args:
            file_path: Path to media file
            
        Returns:
            C2PAResult with verification details
        """
        try:
            # Check if file has C2PA data
            has_c2pa = await self._check_c2pa_presence(file_path)
            if not has_c2pa:
                return C2PAResult(
                    valid=False,
                    error="No C2PA manifest found"
                )
            
            # Extract and parse C2PA manifest
            manifest = await self._extract_manifest(file_path)
            if not manifest:
                return C2PAResult(
                    valid=False,
                    error="Failed to extract C2PA manifest"
                )
            
            # Validate trust chain
            trust_chain_valid = await self._validate_trust_chain(manifest)
            
            # Extract issuer information
            issuer = manifest.get("claim_generator", {}).get("name")
            
            # Extract edit history
            edit_history = self._extract_edit_history(manifest)
            
            # Validate signatures
            signatures_valid = await self._validate_signatures(manifest, file_path)
            
            # Overall validity
            valid = trust_chain_valid and signatures_valid
            
            if not valid and self.strict_validation:
                error_msg = "C2PA validation failed"
                if not trust_chain_valid:
                    error_msg += " (trust chain invalid)"
                if not signatures_valid:
                    error_msg += " (signature verification failed)"
                    
                return C2PAResult(
                    valid=False,
                    issuer=issuer,
                    trust_chain_valid=trust_chain_valid,
                    manifest_store=manifest,
                    edit_history=edit_history,
                    error=error_msg
                )
            
            return C2PAResult(
                valid=valid,
                issuer=issuer,
                trust_chain_valid=trust_chain_valid,
                manifest_store=manifest,
                edit_history=edit_history
            )
            
        except Exception as e:
            logger.error(f"C2PA verification error: {e}", exc_info=True)
            return C2PAResult(
                valid=False,
                error=f"C2PA verification exception: {str(e)}"
            )
    
    async def _check_c2pa_presence(self, file_path: Path) -> bool:
        """Check if file contains C2PA data"""
        try:
            # Look for C2PA markers in file
            # JPEG: Check for "c2pa" marker segment
            # PNG: Check for "caBX" chunk
            # This is a simplified check - real implementation would use c2pa-python
            
            with open(file_path, 'rb') as f:
                header = f.read(1024)
                return b'c2pa' in header or b'caBX' in header
                
        except Exception as e:
            logger.error(f"Error checking C2PA presence: {e}")
            return False
    
    async def _extract_manifest(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Extract C2PA manifest from file
        
        Real implementation would use c2pa-python library:
        from c2pa import read_file
        manifest_store = read_file(str(file_path))
        """
        try:
            # Placeholder - actual implementation requires c2pa-python
            # which is not yet available in pip
            
            # Simulated manifest structure for demonstration
            manifest = {
                "claim_generator": {
                    "name": "Example Camera App",
                    "version": "1.0.0"
                },
                "assertions": [],
                "signature": {},
                "credentials": []
            }
            
            return manifest
            
        except Exception as e:
            logger.error(f"Error extracting C2PA manifest: {e}")
            return None
    
    async def _validate_trust_chain(self, manifest: Dict[str, Any]) -> bool:
        """Validate certificate trust chain"""
        try:
            # Extract credentials from manifest
            credentials = manifest.get("credentials", [])
            
            if not credentials:
                logger.warning("No credentials found in manifest")
                return False
            
            # Validate each credential against trust anchors
            # Real implementation would perform full X.509 validation
            
            # Placeholder validation
            return len(credentials) > 0
            
        except Exception as e:
            logger.error(f"Trust chain validation error: {e}")
            return False
    
    async def _validate_signatures(
        self,
        manifest: Dict[str, Any],
        file_path: Path
    ) -> bool:
        """Validate cryptographic signatures"""
        try:
            # Verify COSE signatures over claim and assertions
            # Real implementation uses COSE verification
            
            signature = manifest.get("signature", {})
            if not signature:
                return False
            
            # Placeholder - actual implementation would:
            # 1. Extract public key from credentials
            # 2. Compute hash of claim + file content
            # 3. Verify signature
            
            return True
            
        except Exception as e:
            logger.error(f"Signature validation error: {e}")
            return False
    
    def _extract_edit_history(self, manifest: Dict[str, Any]) -> list:
        """Extract edit history from manifest"""
        try:
            assertions = manifest.get("assertions", [])
            edit_history = []
            
            for assertion in assertions:
                if assertion.get("label") == "c2pa.actions":
                    actions = assertion.get("data", {}).get("actions", [])
                    for action in actions:
                        edit_history.append(
                            f"{action.get('action')}: {action.get('software_agent', 'Unknown')}"
                        )
            
            return edit_history
            
        except Exception as e:
            logger.error(f"Error extracting edit history: {e}")
            return []


# Global verifier instance
c2pa_verifier = C2PAVerifier()
