# Sensor-PKI Trust Anchors Directory

This directory contains manufacturer public key certificates for sensor-level signature verification.

## Structure

```
sensor_pki_anchors/
├── Sony/
│   ├── sony_root_ca.pem
│   ├── sony_imx989_2023.pem
│   └── sony_imx989_2024.pem
├── Canon/
│   ├── canon_root_ca.pem
│   └── canon_digic_x_2023.pem
├── Nikon/
│   └── nikon_root_ca.pem
└── Samsung/
    └── samsung_isocell_2023.pem
```

## Certificate Hierarchy

Each manufacturer maintains:
1. **Root CA**: Manufacturer's root certificate authority
2. **Sensor-specific certificates**: Per-camera-model or per-sensor certificates
3. **Firmware signing keys**: Keys embedded in camera firmware

## Adding Manufacturer Certificates

1. Obtain certificates from manufacturer PKI
2. Verify authenticity via manufacturer's public key infrastructure
3. Convert to PEM format:
   ```bash
   openssl x509 -inform DER -in cert.der -out manufacturer_cert.pem
   ```
4. Place in manufacturer-specific subdirectory

## Sensor Signature Format

Cameras embed COSE (CBOR Object Signing and Encryption) signatures in:
- EXIF MakerNote field
- XMP metadata
- Custom metadata chunks

Example COSE structure:
```
COSE Sign1 Message:
- Protected Headers: {manufacturer, model, sensor_id, timestamp}
- Payload: SHA-256 hash of image content
- Signature: ECDSA or RSA signature
```

## Supported Manufacturers

Current sensor-PKI implementations:
- Sony (IMX series)
- Canon (DIGIC processors)
- Nikon (EXPEED processors)
- Samsung (ISOCELL sensors)

_Note: Sensor-PKI is an emerging standard. Manufacturer support is growing._

## Verification Process

1. Extract COSE signature from image metadata
2. Parse protected headers to identify manufacturer/model
3. Load corresponding certificate
4. Verify signature against image content hash
5. Validate certificate chain to root CA

## Certificate Management

- **Validity**: Certificates typically valid for 2-5 years
- **Rotation**: Manufacturers issue new certificates periodically
- **Revocation**: Check CRLs or OCSP for revoked certificates

## Security Considerations

- Private keys never leave camera's secure enclave
- Signature created at sensor readout time
- Hardware-backed key storage (TPM, Secure Element)
- Anti-tampering protections

## Resources

- CAI Sensor-PKI Working Group: https://contentauthenticity.org/
- C2PA Hard-binding Specification
- Camera & Imaging Products Association (CIPA) standards

## Testing

Generate test certificates for development:
```bash
# Generate root CA
openssl req -x509 -new -nodes -key root.key -sha256 -days 3650 -out root_ca.pem

# Generate sensor certificate
openssl req -new -key sensor.key -out sensor.csr
openssl x509 -req -in sensor.csr -CA root_ca.pem -CAkey root.key -out sensor_cert.pem
```
