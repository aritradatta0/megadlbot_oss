import os
import base64
import logging
import aiofiles
import mimetypes
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaFileUpload
from mega.database.users import MegaUsers
from datetime import datetime, timedelta, timezone


class Gdrive:
    def __init__(self):
        self.scope = ["https://www.googleapis.com/auth/drive"]

    async def upload_file(self, user_id: int, file: str):
        user_details = await MegaUsers().get_user(user_id)

        if "gdrive_key" in user_details:
            key_file_location = f"mega/{user_details['gdrive_key_location']}"
            if os.path.isfile(key_file_location) is not True:
                async with aiofiles.open(key_file_location, mode='wb') as key_file_aio:
                    await key_file_aio.write(base64.decodebytes(user_details["gdrive_key"]))

            credentials = service_account.Credentials.from_service_account_file(
                filename=key_file_location, scopes=self.scope,
            )

            service = build('drive', 'v3', credentials=credentials)

            file_name = os.path.basename(file)
            file_metadata = {
                'name': file_name,
                'mimeType': (mimetypes.guess_type(file_name))[0]
            }

            media = MediaFileUpload(key_file_location,
                                    mimetype=(mimetypes.guess_type(file_name))[0],
                                    resumable=True)

            gfile = service.files().create(body=file_metadata,
                                           media_body=media,
                                           fields='id').execute()

            service.permissions().create(body={"role": "reader", "type": "anyone"}, fileId=gfile.get("id")).execute()
            await Gdrive().clean_old_files(service)

            return gfile

    @staticmethod
    async def clean_old_files(service: build):
        twelve_hours_since_now = datetime.now(tz=timezone.utc) - timedelta(hours=12)
        twelve_hours_since_now.strftime("%Y-%m-%dT%H:%M:%SZ")
        date_str = twelve_hours_since_now.isoformat(timespec='milliseconds')
        date_str = str(date_str).replace('+00:00', '')

        response = service.files().list(q=f"modifiedTime < '{date_str}'",
                                        spaces="drive",
                                        fields="nextPageToken, files(id, name)").execute()

        old_files = response.get("files")

        for file in old_files:
            logging.info(f"I am removing {file} from google drive since its already old enough.")
            service.files().delete(fileId=file.get("id")).execute()
