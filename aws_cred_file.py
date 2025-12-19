#!/usr/bin/python3

import os
import subprocess
import sys
from os.path import dirname

AWS_ID = os.environ.get("AWS_ID")
IAM_ROLE_ARN = f"arn:aws:iam::{AWS_ID}:role/turnkeyhub"
CRED_TEMPLATE = """# EXPIRY: {expiry}
# Short lived AWS IAM role credentials for S3 bucket access

export PASSPHRASE=$(cat /var/lib/tklbam/secret)

export AWS_ROLE_ARN={iamrole}
export AWS_ACCESS_KEY_ID={accesskey}
export AWS_SECRET_ACCESS_KEY={secretkey}
export AWS_SESSION_TOKEN={sessiontoken}
"""


def write_creds(cred_file_path: str, iamrole: str = IAM_ROLE_ARN) -> None:
    try:
        os.makedirs(dirname(cred_file_path), exist_ok=True)
    except FileNotFoundError:
        # if path is file in PWD dirname will raise this
        pass
    stsagent_proc = subprocess.run(
        ["/usr/bin/tklbam-internal", "stsagent"],
        capture_output=True,
        text=True,
    )
    print(stsagent_proc)
    accesskey, secretkey, sessiontoken, expiry = stsagent_proc.stdout.split()
    with open(cred_file_path, "w") as fob:
        fob.write(
            CRED_TEMPLATE.format(
                expiry=expiry,
                iamrole=iamrole,
                accesskey=accesskey,
                secretkey=secretkey,
                sessiontoken=sessiontoken,
            )
        )

if __name__ == "__main__":
    if AWS_ID is None:
        print("AWS_ID (AWS account ID) must be set in env", file=sys.stderr)
        sys.exit(1)
    cred_file_path = "/var/lib/tklbam/aws_sts_creds"
    if len(sys.argv) > 1:
        cred_file_path = sys.argv[1]
        if len(sys.argv) > 2:
            print("Additional arguements ignored", file=sys.stderr)
    print(f"writing creds to '{cred_file_path}'")
    write_creds(cred_file_path)
