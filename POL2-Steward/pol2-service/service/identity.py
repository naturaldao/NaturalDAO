import hashlib
import hmac
import os


def compute_identity_signature(client_id, account_scope, session_id, project_id=None):
    secret = os.getenv('POL2_IDENTITY_SECRET')
    if not secret:
        return None
    message = '|'.join([client_id or '', account_scope or '', session_id or '', project_id or ''])
    return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()


def verify_identity_signature(headers, client_id, account_scope, session_id, project_id=None):
    secret = os.getenv('POL2_IDENTITY_SECRET')
    if not secret:
        return os.getenv('POL2_ENV') != 'production'
    supplied = headers.get('x-pol2-identity-signature', '')
    expected = compute_identity_signature(client_id, account_scope, session_id, project_id)
    return bool(supplied and expected and hmac.compare_digest(supplied, expected))
