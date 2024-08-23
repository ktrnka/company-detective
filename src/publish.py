# convert to HTML
import markdown
import boto3
import os.path
import jinja2

from core import fix_markdown_list

from loguru import logger

templates = jinja2.Environment(
    loader=jinja2.FileSystemLoader("templates"),
)


def markdown_file_to_html(markdown_path: str):
    """Convert a markdown file to HTML and save it to the same directory with a different extension"""
    html_path = markdown_path.replace(".md", ".html")

    with open(markdown_path, "r") as f:
        md = f.read()
        html = markdown.markdown(fix_markdown_list(md))

        with open(html_path, "w") as f:
            f.write(templates.get_template("base.html").render(content=html))
            logger.info(f"HTML written to {f.name}")
            return html_path


S3_BUCKET = "company-detective"


def publish_to_s3(local_path: str) -> str:
    """Upload an file to S3 and return the public URL. Assumes that the S3 bucket has the right policy and is configured for static website hosting."""
    s3_client = boto3.client("s3")
    object_path = f"reports/{os.path.basename(local_path)}"

    # TODO: Catch exceptions
    # and ExtraArgs (dict) – Extra arguments that may be passed to the client operation. For allowed upload arguments see boto3.s3.transfer.S3Transfer.ALLOWED_UPLOAD_ARGS.
    # ALLOWED_UPLOAD_ARGS = ['ACL', 'CacheControl', 'ChecksumAlgorithm', 'ContentDisposition', 'ContentEncoding', 'ContentLanguage', 'ContentType', 'ExpectedBucketOwner', 'Expires', 'GrantFullControl', 'GrantRead', 'GrantReadACP', 'GrantWriteACP', 'Metadata', 'ObjectLockLegalHoldStatus', 'ObjectLockMode', 'ObjectLockRetainUntilDate', 'RequestPayer', 'ServerSideEncryption', 'StorageClass', 'SSECustomerAlgorithm', 'SSECustomerKey', 'SSECustomerKeyMD5', 'SSEKMSKeyId', 'SSEKMSEncryptionContext', 'Tagging', 'WebsiteRedirectLocation']

    s3_client.upload_file(
        local_path,
        S3_BUCKET,
        object_path,
        ExtraArgs={
            "ContentType": "text/html; charset=utf-8",
            "ContentDisposition": "inline",
        },
    )

    return f"http://{S3_BUCKET}.s3-website-us-west-2.amazonaws.com/{object_path}"
