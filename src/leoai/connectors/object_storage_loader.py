from __future__ import annotations

import oci

from ..config import Settings


def _build_object_storage_client(settings: Settings) -> oci.object_storage.ObjectStorageClient:
    if settings.auth_mode == "instance_principal":
        signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
        return oci.object_storage.ObjectStorageClient(
            config={"region": settings.region},
            signer=signer,
            timeout=(10, 120),
        )

    config = oci.config.from_file(profile_name=settings.oci_profile)
    return oci.object_storage.ObjectStorageClient(config=config, timeout=(10, 120))


def load_object_text(
    settings: Settings,
    namespace_name: str,
    bucket_name: str,
    object_name: str,
    encoding: str = "utf-8",
) -> str:
    client = _build_object_storage_client(settings)
    response = client.get_object(
        namespace_name=namespace_name,
        bucket_name=bucket_name,
        object_name=object_name,
    )
    data = response.data.content
    return data.decode(encoding, errors="replace")

