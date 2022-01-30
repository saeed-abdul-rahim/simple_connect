# -*- coding: utf-8 -*-
"""
Created on Fri Aug 10 15:20:03 2018

@author: Saeed
"""

import httplib2
import os
import json
import oauth2client
from oauth2client import file, client, tools
import base64
from email import encoders
import mimetypes
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import pandas as pd
import pymysql as db
from sqlalchemy import create_engine
from sqlalchemy.sql import text
from sshtunnel import SSHTunnelForwarder
from googleapiclient.discovery import build
from googleapiclient import errors, discovery
from googleapiclient.http import MediaIoBaseDownload
from httplib2 import Http
import io
import boto3
from tqdm import tqdm


class Common(object):

    def __init__(self, sql_serverhost, sql_user, sql_password, database):
        self.sql_serverhost = sql_serverhost
        self.sql_user = sql_user
        self.sql_password = sql_password
        self.database = database

    def create_sq_string(col_set, sep):
        cols = ""
        for i, col in enumerate(col_set):
            cols = cols + col + " = :"+col
            if not i == (len(col_set)-1):
                cols = cols+" "+sep+" "
        return cols

    def update_main(self, df, conn, table_name, set_cols, where_cols):
        dict_data = df.to_dict('records')
        dict_data = tuple(dict_data)
        set_columns = Common.create_sq_string(set_cols, ",")
        where_columns = Common.create_sq_string(where_cols, "AND")
        stmt = "UPDATE "+table_name+" SET "+set_columns+" WHERE "+where_columns
        stmt = text(stmt)
        for line in tqdm(dict_data):
            conn.execute(stmt, **line)

    def delete_main(self, df, conn, table_name, where_cols):
        dict_data = df.to_dict('records')
        dict_data = tuple(dict_data)
        where_columns = Common.create_sq_string(where_cols, "AND")
        stmt = "DELETE FROM "+table_name+" WHERE "+where_columns
        stmt = text(stmt)
        for line in tqdm(dict_data):
            conn.execute(stmt, **line)


class Connect(Common):

    def __init__(self, credentials, database):
        cred_dir = os.path.join(os.path.expanduser('~'), '.credentials')
        cred_file = os.path.join(cred_dir, credentials)
        with open(cred_file) as f:
            cred = json.load(f)
        sql_serverhost = cred['SQL_HOST']
        sql_user = cred['SQL_USER']
        sql_password = cred['SQL_PASSWORD']
        self.common = Common(sql_serverhost, sql_user, sql_password, database)
        self.mydb = create_engine('mysql+pymysql://' + sql_user + ':' + sql_password +
                                  '@' + sql_serverhost + ':' + str(3306) + '/' + database, echo=False)

    def to_db(self, data, table):
        data.to_sql(name=table, con=self.mydb, if_exists='append',
                    index=False, chunksize=5000)

    def query(self, q):
        return pd.read_sql_query(q, self.mydb)

    def update_table(self, df, table_name, set_cols, where_cols):
        self.common.update_main(
            df, self.mydb, table_name, set_cols, where_cols)

    def delete_row(self, df, table_name, where_cols):
        self.common.delete_main(df, self.mydb, table_name, where_cols)


class BastionConnect(Common):

    def __init__(self, credentials, database):
        cred_dir = os.path.join(os.path.expanduser('~'), '.credentials')
        cred_file = os.path.join(cred_dir, credentials)
        with open(cred_file) as f:
            cred = json.load(f)
        ssh_username = cred['SSH_USERNAME']
        ssh_password = cred['SSH_PASSWORD']
        sql_serverhost = cred['SQL_HOST']
        sql_user = cred['SQL_USER']
        sql_password = cred['SQL_PASSWORD']
        self.bastion_host = cred['BASTION_HOST']
        self.localhost = '127.0.0.1'
        self.ssh_username = ssh_username
        self.ssh_password = ssh_password
        self.common = Common(sql_serverhost, sql_user, sql_password, database)
        self.server = SSHTunnelForwarder(
            (self.bastion_host, 22),
            ssh_username=self.ssh_username,
            ssh_password=self.ssh_password,
            remote_bind_address=(self.common.sql_serverhost, 3306))
        self.conn = None
        self.mydb = None

    def start_conn(self):
        self.conn = db.connect(host=self.localhost,
                               port=self.server.local_bind_port,
                               user=self.common.sql_user,
                               passwd=self.common.sql_password,
                               db=self.common.database)
        self.mydb = create_engine('mysql+pymysql://' + self.common.sql_user + ':' + self.common.sql_password +
                                  '@' + self.localhost + ':' + str(self.server.local_bind_port) + '/' + self.common.database, echo=False)

    def query(self, q):
        self.server.start()
        self.start_conn()
        df = pd.read_sql_query(q, self.conn)
        self.server.stop()
        return df

    def to_db(self, df, table):
        self.server.start()
        self.start_conn()
        df.to_sql(name=table, con=self.mydb, if_exists='append',
                  index=False, chunksize=5000)
        self.server.stop()

    def update_table(self, df, table_name, set_cols, where_cols):
        self.server.start()
        self.start_conn()
        self.common.update_main(
            df, self.mydb, table_name, set_cols, where_cols)
        self.server.stop()

    def delete_row(self, df, table_name, where_cols):
        self.server.start()
        self.start_conn()
        self.common.delete_main(df, self.mydb, table_name, where_cols)
        self.server.stop()


class Gdrive:

    SCOPES = 'https://www.googleapis.com/auth/drive'

    def __init__(self, credential_file_json, SCOPES=SCOPES):

        credential_file_json = credential_file_json.replace('.json', '')
        home_dir = os.path.expanduser('~')
        credential_dir = os.path.join(home_dir, '.credentials')
        if not os.path.exists(credential_dir):
            os.makedirs(credential_dir)
        credential_path = os.path.join(
            credential_dir, credential_file_json+'-gdrive.json')

        self.store = oauth2client.file.Storage(credential_path)
        self.creds = self.store.get()
        if not self.creds or self.creds.invalid:
            CLIENT_SECRET_FILE = credential_file_json+'.json'
            APPLICATION_NAME = 'Google Drive API Python'
            self.flow = client.flow_from_clientsecrets(
                os.path.join(os.getcwd(), CLIENT_SECRET_FILE), SCOPES)
            self.flow.user_agent = APPLICATION_NAME
            self.creds = tools.run_flow(self.flow, self.store)
        self.service = build('drive', 'v3', http=self.creds.authorize(Http()))
        self.items = []
        self.folder = ''

    def get_files(self, folder):

        self.folder = folder
        service = self.service
        results = service.files().list(
            fields="nextPageToken, files(id, name)",
            q="'"+self.folder+"' in parents").execute()
        self.items = results.get('files', [])

        return self.items

    def download_files(self, folder):

        items = self.get_files(folder)
        for item in items:
            print('{0} ({1})'.format(item['name'], item['id']))
            file_name = item['name']
            file_id = item['id']
            request = self.service.files().get_media(fileId=file_id)
            fh = io.FileIO(file_name, 'wb')
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                print("Download %d%%." % int(status.progress() * 100))


class Gmail:

    def __init__(self, credential_file_json):

        credential_file_json = credential_file_json.replace('.json', '')
        home_dir = os.path.expanduser('~')
        credential_dir = os.path.join(home_dir, '.credentials')
        if not os.path.exists(credential_dir):
            os.makedirs(credential_dir)
        credential_path = os.path.join(
            credential_dir, credential_file_json+'-gmail.json')

        store = oauth2client.file.Storage(credential_path)
        self.credentials = store.get()
        if not self.credentials or self.credentials.invalid:
            CLIENT_SECRET_FILE = credential_file_json+'.json'
            APPLICATION_NAME = 'Gmail API Python Send Email'
            SCOPES = 'https://www.googleapis.com/auth/gmail.send'
            flow = client.flow_from_clientsecrets(
                os.path.join(os.getcwd(), CLIENT_SECRET_FILE), SCOPES)
            flow.user_agent = APPLICATION_NAME
            self.credentials = tools.run_flow(flow, store)

    def create_message_and_send(self, sender, to, subject, message_text_html, image=None, attached_file=None):

        credentials = self.credentials
        http = httplib2.Http()
        http = credentials.authorize(http)
        service = discovery.build('gmail', 'v1', http=http)

        message = self.create_message(
            sender, to, subject, message_text_html, image, attached_file)
        self.send_message(service, "me", message)

    def create_message(self, sender, to, subject, message_text_html, image=None, attached_file=None):

        message = MIMEMultipart()
        message['Subject'] = subject
        message['From'] = sender
        message['To'] = to

        table = "table{color: #333;font-family: Helvetica, Arial, sans-serif;border-collapse: collapse; border-spacing: 0; }"
        tdth = """td,th { border: 1px solid transparent;height: 30px; transition: all 0.3s; padding: 6px 12px;}
                th { background: #aaccff; font-weight: bold;}
                td {  text-align: center;}
                tr:nth-child(even) td { background: #F1F1F1 !important; } 
                tr:nth-child(odd) td { background: #FEFEFE !important; }
                tr:hover { background: #000 !important; color: #FFF !important; }"""
        head = '<html><head><style>'+table+tdth+'</style></head>'
        message_text_html = head+'<body>'+message_text_html+'</body></html>'

        if image == None:
            message.attach(MIMEText(message_text_html, 'html'))
        else:
            message.attach(
                MIMEText('<p><img src="cid:image1" /></p>'+message_text_html, 'html'))

            image.seek(0)
            img = MIMEImage(image.read(), 'png')
            img.add_header('Content-Id', '<image1>')
            img.add_header("Content-Disposition", "inline", filename="image1")
            message.attach(img)

        if not attached_file == None:
            my_mimetype, encoding = mimetypes.guess_type(attached_file)

            if my_mimetype is None or encoding is not None:
                my_mimetype = 'application/octet-stream'

            main_type, sub_type = my_mimetype.split('/', 1)
            if main_type == 'text':
                print("text")
                temp = open(attached_file, 'r')
                attachement = MIMEText(temp.read(), _subtype=sub_type)
                temp.close()

            elif main_type == 'image':
                print("image")
                temp = open(attached_file, 'rb')
                attachement = MIMEImage(temp.read(), _subtype=sub_type)
                temp.close()

            elif main_type == 'audio':
                print("audio")
                temp = open(attached_file, 'rb')
                attachement = MIMEAudio(temp.read(), _subtype=sub_type)
                temp.close()

            elif main_type == 'application' and sub_type == 'pdf':
                temp = open(attached_file, 'rb')
                attachement = MIMEApplication(temp.read(), _subtype=sub_type)
                temp.close()

            else:
                attachement = MIMEBase(main_type, sub_type)
                temp = open(attached_file, 'rb')
                attachement.set_payload(temp.read())
                temp.close()

            encoders.encode_base64(attachement)
            filename = os.path.basename(attached_file)
            attachement.add_header('Content-Disposition',
                                   'attachment', filename=filename)
            message.attach(attachement)

        raw_message_no_attachment = base64.urlsafe_b64encode(
            message.as_bytes())
        raw_message_no_attachment = raw_message_no_attachment.decode()
        body = {'raw': raw_message_no_attachment}
        return body

    def send_message(self, service, user_id, body):

        try:
            (service.users().messages().send(userId=user_id, body=body).execute())
            print("Sent")
        except errors.HttpError as error:
            print(f'An error occurred: {error}')


class S3:

    def __init__(self, aws_access_key_id, aws_secret_access_key, region_name):
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.region_name = region_name
        self.client = boto3.client('s3', aws_access_key_id=aws_access_key_id,
                                   aws_secret_access_key=aws_secret_access_key, region_name=region_name)
