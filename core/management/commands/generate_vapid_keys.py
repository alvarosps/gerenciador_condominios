"""Generate a VAPID key pair for Web Push, printed as env-ready variables.

The keys are emitted in the base64url string form that ``pywebpush``
(``Vapid.from_string``) accepts directly from environment variables — the
``.pem`` files produced by ``vapid --gen`` do NOT load as an env string.
"""

import base64

from cryptography.hazmat.primitives import serialization
from django.core.management.base import BaseCommand, CommandError
from py_vapid import Vapid01


class Command(BaseCommand):
    help = "Generate a VAPID key pair (base64url) for Web Push environment variables."

    def handle(self, *args: object, **options: object) -> None:
        vapid = Vapid01()
        vapid.generate_keys()
        public = vapid.public_key
        private = vapid.private_key
        if public is None or private is None:
            msg = "Falha ao gerar o par de chaves VAPID."
            raise CommandError(msg)

        public_key = (
            base64.urlsafe_b64encode(
                public.public_bytes(
                    serialization.Encoding.X962,
                    serialization.PublicFormat.UncompressedPoint,
                )
            )
            .decode()
            .rstrip("=")
        )
        private_key = (
            base64.urlsafe_b64encode(private.private_numbers().private_value.to_bytes(32, "big"))
            .decode()
            .rstrip("=")
        )

        self.stdout.write(f"VAPID_PUBLIC_KEY={public_key}")
        self.stdout.write(f"VAPID_PRIVATE_KEY={private_key}")
        self.stdout.write("VAPID_SUBJECT=mailto:seu-email@dominio.com")
