"""
Sensor-PKI verification service
Validates sensor-level cryptographic signatures from camera hardware
"""
import logging
from typing import Optional
from pathlib import Path
import hashlib

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa, ec
from cryptography.exceptions import InvalidSignature
import cbor2
from pycose.messages import Sign1Message
from pycose.keys import CoseKey

from app.models.database import SensorPKIResult
from app.config import settings

logger = logging.getLogger(__name__)


class SensorPKIVerifier:
    """Sensor-PKI signature verification service"""
    
    def __init__(self):
        """Initialize verifier with manufacturer trust anchors"""
        self.trust_anchors_path = Path(settings.sensor_pki_trust_anchors_path)
        self.enabled = settings.sensor_pki_enable
        self._load_manufacturer_certs()
    
    def _load_manufacturer_certs(self):
        """Load manufacturer public key certificates"""
        try:
            if not self.trust_anchors_path.exists():
                logger.warning(
                    f"Sensor-PKI trust anchors not found: {self.trust_anchors_path}"
                )
                self.manufacturer_certs = {}
                return
            
            self.manufacturer_certs = {}
            
            # Load certificates organized by manufacturer
            for manufacturer_dir in self.trust_anchors_path.iterdir():
                if manufacturer_dir.is_dir():
                    manufacturer_name = manufacturer_dir.name
                    certs = []
                    
                    for cert_file in manufacturer_dir.glob("*.pem"):
                        with open(cert_file, 'rb') as f:
                            cert = x509.load_pem_x509_certificate(
                                f.read(),
                                default_backend()
                            )
                            certs.append(cert)
                    
                    self.manufacturer_certs[manufacturer_name] = certs
            
            total_certs = sum(len(certs) for certs in self.manufacturer_certs.values())
            logger.info(
                f"Loaded {total_certs} sensor-PKI certificates from "
                f"{len(self.manufacturer_certs)} manufacturers"
            )
            
        except Exception as e:
            logger.error(f"Failed to load manufacturer certificates: {e}")
            self.manufacturer_certs = {}
    
    async def verify(self, file_path: Path) -> SensorPKIResult:
        """
        Verify sensor-level PKI signature
        
        Args:
            file_path: Path to media file
            
        Returns:
            SensorPKIResult with verification details
        """
        if not self.enabled:
            return SensorPKIResult(
                valid=False,
                error="Sensor-PKI verification disabled"
            )
        
        try:
            # Extract signature envelope from file metadata
            signature_envelope = await self._extract_signature_envelope(file_path)
            
            if not signature_envelope:
                return SensorPKIResult(
                    valid=False,
                    error="No sensor-PKI signature found"
                )
            
            # Parse COSE Sign1 message
            signature_data = await self._parse_signature_envelope(signature_envelope)
            
            if not signature_data:
                return SensorPKIResult(
                    valid=False,
                    error="Failed to parse signature envelope"
                )
            
            # Extract manufacturer and camera info
            manufacturer = signature_data.get("manufacturer")
            camera_model = signature_data.get("camera_model")
            sensor_id = signature_data.get("sensor_id")
            
            # Verify signature against file content
            verification_result = await self._verify_signature(
                file_path,
                signature_data,
                manufacturer
            )
            
            if not verification_result["valid"]:
                return SensorPKIResult(
                    valid=False,
                    manufacturer=manufacturer,
                    camera_model=camera_model,
                    sensor_id=sensor_id,
                    error=verification_result.get("error", "Signature verification failed")
                )
            
            # Extract signature algorithm info
            sig_algo = signature_data.get("algorithm", "Unknown")
            pub_key_fp = verification_result.get("public_key_fingerprint")
            
            return SensorPKIResult(
                valid=True,
                manufacturer=manufacturer,
                camera_model=camera_model,
                sensor_id=sensor_id,
                signature_algorithm=sig_algo,
                public_key_fingerprint=pub_key_fp
            )
            
        except Exception as e:
            logger.error(f"Sensor-PKI verification error: {e}", exc_info=True)
            return SensorPKIResult(
                valid=False,
                error=f"Verification exception: {str(e)}"
            )
    
    async def _extract_signature_envelope(self, file_path: Path) -> Optional[bytes]:
        """
        Extract sensor signature from file metadata
        
        Sensor signatures are typically embedded in:
        - EXIF MakerNote field (JPEG)
        - XMP metadata (various formats)
        - Custom metadata chunks (PNG, TIFF)
        - Video container metadata (MP4, MOV)
        """
        try:
            # Check if file is a video
            if file_path.suffix.lower() in ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv']:
                # For videos, sensor signatures would be in container metadata
                # This is a placeholder - real implementation would parse video containers
                logger.debug(f"Video file detected: {file_path.suffix}, sensor-PKI extraction not yet fully implemented for videos")
                return None
            
            # Check EXIF data for signature (images only)
            from PIL import Image
            from PIL.ExifTags import TAGS
            
            img = Image.open(file_path)
            exif_data = img._getexif()
            
            if not exif_data:
                return None
            
            # Look for sensor signature in MakerNote or custom tag
            # Tag 0x927C is MakerNote
            maker_note = exif_data.get(0x927C)
            
            if maker_note and isinstance(maker_note, bytes):
                # Check if it contains COSE signature marker
                if b'COSE' in maker_note[:100]:
                    # Extract COSE envelope
                    # Real implementation would properly parse MakerNote structure
                    return maker_note
            
            # Also check for XMP metadata containing signature
            if hasattr(img, 'info') and 'XML:com.adobe.xmp' in img.info:
                xmp = img.info['XML:com.adobe.xmp']
                if b'sensor-pki' in xmp:
                    # Extract signature from XMP
                    # Placeholder - real implementation would parse XMP
                    pass
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting signature envelope: {e}")
            return None
    
    async def _parse_signature_envelope(
        self,
        envelope: bytes
    ) -> Optional[dict]:
        """Parse COSE Sign1 message envelope"""
        try:
            # Decode CBOR-encoded COSE message
            # Real implementation:
            # msg = Sign1Message.decode(envelope)
            
            # Placeholder structure
            signature_data = {
                "manufacturer": "Sony",  # Extracted from protected headers
                "camera_model": "Alpha 7R V",
                "sensor_id": "IMX989-12345",
                "algorithm": "ES256",  # ECDSA with SHA-256
                "timestamp": "2025-10-02T10:30:00Z",
                "signature": b"...",  # Actual signature bytes
                "payload": b"...",  # Signed content hash
            }
            
            return signature_data
            
        except Exception as e:
            logger.error(f"Error parsing signature envelope: {e}")
            return None
    
    async def _verify_signature(
        self,
        file_path: Path,
        signature_data: dict,
        manufacturer: str
    ) -> dict:
        """Verify cryptographic signature"""
        try:
            # Get manufacturer certificates
            certs = self.manufacturer_certs.get(manufacturer, [])
            
            if not certs:
                return {
                    "valid": False,
                    "error": f"No certificates found for manufacturer: {manufacturer}"
                }
            
            # Compute file content hash
            file_hash = await self._compute_file_hash(file_path)
            
            # Extract signature and expected payload
            signature = signature_data.get("signature")
            expected_payload = signature_data.get("payload")
            
            # Verify signature with each certificate until one succeeds
            for cert in certs:
                try:
                    public_key = cert.public_key()
                    
                    # Verify based on algorithm type
                    if isinstance(public_key, rsa.RSAPublicKey):
                        public_key.verify(
                            signature,
                            file_hash,
                            padding.PSS(
                                mgf=padding.MGF1(hashes.SHA256()),
                                salt_length=padding.PSS.MAX_LENGTH
                            ),
                            hashes.SHA256()
                        )
                    elif isinstance(public_key, ec.EllipticCurvePublicKey):
                        public_key.verify(
                            signature,
                            file_hash,
                            ec.ECDSA(hashes.SHA256())
                        )
                    else:
                        continue
                    
                    # Signature verified successfully
                    pub_key_fp = hashlib.sha256(
                        public_key.public_bytes(
                            encoding=serialization.Encoding.DER,
                            format=serialization.PublicFormat.SubjectPublicKeyInfo
                        )
                    ).hexdigest()[:16]
                    
                    return {
                        "valid": True,
                        "public_key_fingerprint": pub_key_fp
                    }
                    
                except InvalidSignature:
                    continue
                except Exception as e:
                    logger.warning(f"Certificate verification error: {e}")
                    continue
            
            return {
                "valid": False,
                "error": "Signature verification failed with all certificates"
            }
            
        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            return {
                "valid": False,
                "error": str(e)
            }
    
    async def _compute_file_hash(self, file_path: Path) -> bytes:
        """Compute cryptographic hash of file content"""
        hasher = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        
        return hasher.digest()


# Global verifier instance
sensor_pki_verifier = SensorPKIVerifier()
