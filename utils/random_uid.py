import re
import uuid
import base64


def short_uuid():
    full_uuid = uuid.uuid4().bytes
    encoded = base64.urlsafe_b64encode(full_uuid).decode('utf-8').rstrip("=")

    clean_id = re.sub(r'[^a-zA-Z0-9]', '', encoded)

    return clean_id[:6].upper()


if __name__ == '__main__':
    print(short_uuid())
