import sys
import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
ec2 = boto3.resource('ec2')


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
            'ImageId': image, 'InstanceType': instance_type, 'KeyName': key_pair
        }
        if security_groups is not None:
            instance_params['SecurityGroupIds'] = [sg for sg in security_groups]
        instance = ec2.create_instances(**instance_params, MinCount=1, MaxCount=1)[0]
        instance.wait_until_running()
    except ClientError as err:
        logging.error(
            "Couldn't create instance with image %s, instance type %s, and key %s. "
            "Here's why: %s: %s", image, instance_type, key_pair,
            err.response['Error']['Code'], err.response['Error']['Message'])
        raise
    else:
        return instance


def display(instance):
    """
    Displays information about an instance.
    """
    try:
        instance.load()
        ind = '\t'
        print(f"{ind}ID: {instance.id}")
        print(f"{ind}Image ID: {instance.image_id}")
        print(f"{ind}Instance type: {instance.instance_type}")
        print(f"{ind}Key name: {instance.key_name}")
        print(f"{ind}Public IP: {instance.public_ip_address}")
        print(f"{ind}State: {instance.state['Name']}")
    except ClientError as err:
        logger.error(
            "Couldn't display your instance. Here's why: %s: %s",
            err.response['Error']['Code'], err.response['Error']['Message'])
        raise


if __name__ == '__main__':
    if sys.argv[1] == 'launch':
        display(create("ami-0283a57753b18025b", "t2.micro", "esc22keypair", ["sg-002f71db95c7f849d"]))
    elif sys.argv[1] == 'terminate':
        ec2.Instance(sys.argv[2]).terminate()
    else:
        print("Syntax (two modes):")
        print("\tinstance.py create")
        print("\tinstance.py terminate <instance id>")

