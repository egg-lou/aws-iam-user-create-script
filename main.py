import csv
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
import os
import json

load_dotenv()

aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
region_name = os.getenv('AWS_REGION')

iam_client = boto3.client('iam', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key, region_name=region_name)
ses_client = boto3.client('ses', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key, region_name=region_name)

csv_file = 'dcc_core.csv'
credentials = 'dcc_creds.csv'

user_group = os.getenv('IAM_USER_GROUP')

created_users = []

console_access_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "iam:ChangePassword",
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": "iam:GetUser",
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": "iam:ListMFADevices",
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": "iam:ListVirtualMFADevices",
            "Resource": "*"
        }
    ]
}

error_occurred = False

with open(csv_file, 'r') as file:
    csv_reader = csv.reader(file)
    next(csv_reader)

    for row in csv_reader:
        full_name, email = row

        username = full_name.replace(' ', '.')

        custom_password = os.getenv('CUSTOM_PASSWORD')

        try:
            response = iam_client.create_user(UserName=username)
            print(f'IAM User {full_name} created successfully')

            iam_client.create_login_profile(
                UserName=username,
                Password=custom_password,
                PasswordResetRequired=True
            )

            print(f'Password set for IAM user {username}')

            iam_client.put_user_policy(
                UserName=username,
                PolicyName='ConsoleAccessPolicy',
                PolicyDocument=json.dumps(console_access_policy)
            )

            print(f"Console access policy attached to IAM user '{username}'.")

            iam_client.add_user_to_group(GroupName=user_group, UserName=username)
            print(f"IAM user '{username}' added to group '{user_group}'.")

            sign_in_url = os.getenv('AWS_SIGN_IN_URL')

            subject = 'Welcome to Amazon Web Services'
            body = f"Hello {full_name}, \n\nYou now have access to the AWS Management Console\n\nYour Username is: {username}\nYour custom password is: {custom_password}\n\nSign-in URL: {sign_in_url}\n\nPlease sign-in as soon as possible and change your password\n\nThank you very much Cloud Buddy"
            sender_email = os.getenv('EMAIL')
            recipient_email = email

            try:
                response = ses_client.send_email(
                    Source=sender_email,
                    Destination={'ToAddresses': [recipient_email]},
                    Message={
                        'Subject': {'Data': subject},
                        'Body': {'Text': {'Data': body}}
                    }
                )

                print(f'Email Sent to {recipient_email} successfully!.')

                created_users.append({'Name': username, 'Email': email, 'Password': custom_password, 'Group': user_group, 'SignInURL': sign_in_url})

            except ClientError as e:
                print(f"Error sending email to {recipient_email}: {e}")
                error_occurred = True

        except ClientError as e:
            print(f"Error creating IAM user '{username}': {e}")
            error_occurred = True

if not error_occurred:
    print("User creation and email sending completed successfully.")
else:
    print("There were errors during user creation or email sending.")
