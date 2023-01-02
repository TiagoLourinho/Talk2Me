# Talk2Me

Distributed system that sends and receives messages between users composed of a server and a client.

# Configuration

Change the parameters in `source/config.py` accordingly.
- `PORT`(int): The port in which to execute the communications
- `LOGGING` (bool): Whether to print the messages received/sent to the terminal (controlled by the environmental variable `TALK2ME_LOG`)
- `BASE_ENCRYPTION_KEY` (string): The encryption key used in the encryption/decryption of the messages
- `SUCCESS` (string): Macro for "Success"
- `FAILURE` (string): Macro for "Failure"
- `MAX_THREADS` (int): Maximum number of threads in the server before checking and cleaning inactive threads
- `SOCKET_TIMEOUT` (int): The number of seconds to wait before timing out of the socket in the accept step
- `CHAT_SERVERS` (list[str]): A list of the other servers address (used in multi-deployment)

# Cloud deployment

The script `cloud/aws_ec2.py` automatically creates an EC2 instance, copies the source code and starts the server. A file named `aws_config.py` should be created in `cloud/` defining the following variables: 
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_DEFAULT_REGION`