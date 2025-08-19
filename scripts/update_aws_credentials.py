import boto3
import yaml
import sys


def get_aws_credentials(profile):
    session = boto3.Session(profile_name=profile)
    creds = session.get_credentials().get_frozen_credentials()
    return {
        "AWS_ACCESS_KEY_ID": creds.access_key,
        "AWS_SECRET_ACCESS_KEY": creds.secret_key,
        "AWS_SESSION_TOKEN": creds.token,
    }


def update_env_file(env_path, creds):
    with open(env_path, "r") as f:
        lines = f.readlines()
    with open(env_path, "w") as f:
        for line in lines:
            for key, value in creds.items():
                if line.startswith(key + "="):
                    line = f"{key}={value}\n"
            f.write(line)


def recursive_update(data, creds):
    if isinstance(data, dict):
        for key, value in data.items():
            if key in creds:
                data[key] = creds[key]  # update match
            else:
                recursive_update(value, creds)
    return data


def update_yaml_file(yaml_path, creds):
    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f)

    recursive_update(data, creds)

    with open(yaml_path, "w") as f:
        yaml.safe_dump(data, f)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python update_aws_credentials.py <profile>")
        sys.exit(1)
    profile = sys.argv[1]
    creds = get_aws_credentials(profile)
    update_env_file(".env", creds)
    update_yaml_file("secrets.yaml", creds)
