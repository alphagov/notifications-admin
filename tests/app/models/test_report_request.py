import boto3
from moto import mock_aws

from app.models.report_request import ReportRequest


@mock_aws
def test_report_request_download(notify_admin):
    bucket_name = ReportRequest.get_bucket_name()
    s3 = boto3.client("s3", region_name="eu-west-1")
    s3.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": "eu-west-1"})
    s3.put_object(Bucket=bucket_name, Key="notifications_report/abcd.csv", Body=b"csv_content")

    csv_file = ReportRequest.download("abcd")

    assert csv_file.read().decode("utf-8") == "csv_content"
