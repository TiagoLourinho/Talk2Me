import sys
import logging
import boto3
from botocore.exceptions import ClientError
import subprocess
import os

from aws_config import *

# Set enviroment variables defined in aws_config.py and used by boto3
os.environ["AWS_ACCESS_KEY_ID"] = AWS_ACCESS_KEY_ID
os.environ["AWS_SECRET_ACCESS_KEY"] = AWS_SECRET_ACCESS_KEY
os.environ["AWS_DEFAULT_REGION"] = AWS_DEFAULT_REGION

# Instance parameters
IMAGE_AMI = "ami-07c2ae35d31367b3e"
INSTANCE_TYPE = "t2.micro"
KEY_PAIR = "Talk2Me_key"
SECURITY_GROUPS = ["sg-0bb356c8607f06a99"]

# Global variables
logger = logging.getLogger(__name__)
ec2 = boto3.resource("ec2")


def create(image, instance_type, key_pair, security_groups=None):
    """
    Creates a new EC2 instance. The instance starts immediately after
    it is created.

    The instance is created in the default VPC of the current account.

    :param image: A Boto3 Image object that represents an Amazon Machine Image (AMI)
                  that defines attributes of the instance that is created. The AMI
                  defines things like the kind of operating system and the type of
                  storage used by the instance.
    :param instance_type: The type of instance to create, such as 't2.micro'.
                          The instance type defines things like the number of CPUs and
                          the amount of memory.
    :param key_pair: A Boto3 KeyPair or KeyPairInfo object that represents the key
                     pair that is used to secure connections to the instance.
    :param security_groups: A list of Boto3 SecurityGroup objects that represents the
                            security groups that are used to grant access to the
                            instance. When no security groups are specified, the
                            default security group of the VPC is used.
    :return: A Boto3 Instance object that represents the newly created instance.
    """
    try:
        instance_params = {
            "ImageId": image,
            "InstanceType": instance_type,
            "KeyName": key_pair,
        }
        if security_groups is not None:
            instance_params["SecurityGroupIds"] = [sg for sg in security_groups]
        instance = ec2.create_instances(**instance_params, MinCount=1, MaxCount=1)[0]
        instance.wait_until_running()
    except ClientError as err:
        logging.error(
            "Couldn't create instance with image %s, instance type %s, and key %s. "
            "Here's why: %s: %s",
            image,
            instance_type,
            key_pair,
            err.response["Error"]["Code"],
            err.response["Error"]["Message"],
        )
        raise
    else:
        return instance


def display(instance):
    """
    Displays information about an instance.
    """
    try:
        instance.load()
        ind = "\t"
        print(f"{ind}ID: {instance.id}")
        print(f"{ind}Image ID: {instance.image_id}")
        print(f"{ind}Instance type: {instance.instance_type}")
        print(f"{ind}Key name: {instance.key_name}")
        print(f"{ind}Public IP: {instance.public_ip_address}")
        print(f"{ind}State: {instance.state['Name']}")
    except ClientError as err:
        logger.error(
            "Couldn't display your instance. Here's why: %s: %s",
            err.response["Error"]["Code"],
            err.response["Error"]["Message"],
        )
        raise


def print_usage():
    print("Usage:")
    print("- aws_ec2.py start")
    print("- aws_ec2.py stop <instance id>")


def execute_command(command):
    subprocess.run(command.split())


if __name__ == "__main__":
    try:
        if sys.argv[1] == "start":
            print("Lauching instance...")
            instance = create(
                IMAGE_AMI,
                INSTANCE_TYPE,
                KEY_PAIR,
                SECURITY_GROUPS,
            )
            display(instance)

            print("Copying server code to virtual machine...")
            execute_command(
                f'scp -i {os.path.join(os.getcwd(), KEY_PAIR + ".pem")} -r source/ ubuntu@{instance.public_ip_address}:'
            )

            print(f"Starting the server at {instance.public_ip_address}...")

            boto3.client("ssm").send_command(
                DocumentName="AWS-RunShellScript",
                Parameters={"commands": ["python3 source/t2ms.py"]},
                InstanceIds=[instance.id],
            )

        elif sys.argv[1] == "stop":
            print("Terminating instance...")
            ec2.Instance(sys.argv[2]).terminate()
        else:
            print_usage()
    except IndexError:
        print_usage()
