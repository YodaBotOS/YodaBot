import os
import subprocess

import config


def get_gcp_token(*, from_gcloud=False):
    """
    Get a GCP access token.
    """

    if not from_gcloud:
        return config.GCP_TOKEN

    # GCE (Google Compute Engine) has a default service account, so we don't need this.
    # We just need to let gcloud handle it.
    #
    # if 'GOOGLE_APPLICATION_CREDENTIALS' not in os.environ:
    #     raise Exception("GOOGLE_APPLICATION_CREDENTIALS environment variable not set.")
    #
    # if not os.path.exists(os.environ['GOOGLE_APPLICATION_CREDENTIALS']):
    #     raise Exception("GOOGLE_APPLICATION_CREDENTIALS environment variable set to non-existent file.")

    process = subprocess.Popen(["gcloud", "auth", "application-default", "print-access-token"], stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)

    stdout, stderr = process.communicate()

    if stderr:
        raise Exception(stderr.decode())

    return stdout.decode().rstrip()
