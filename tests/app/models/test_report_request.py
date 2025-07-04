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


@mock_aws
def test_is_report_exists_should_return_true_when_report_exists(notify_admin):
    bucket_name = ReportRequest.get_bucket_name()
    s3 = boto3.client("s3", region_name="eu-west-1")
    s3.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": "eu-west-1"})
    s3.put_object(Bucket=bucket_name, Key="notifications_report/abcd.csv", Body=b"csv_content")

    assert ReportRequest.is_report_exists("abcd")


@mock_aws
def test_is_report_exists_should_return_false_when_report_does_not_exist(notify_admin):
    bucket_name = ReportRequest.get_bucket_name()
    s3 = boto3.client("s3", region_name="eu-west-1")
    s3.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": "eu-west-1"})

    assert ReportRequest.is_report_exists("abcd") is False
