import sys
import json
import pickle
import os
import time
import logging
import email
import getpass
import imaplib

import configuration as cfg

logging.basicConfig(level=logging.INFO, format='%(asctime)s: %(levelname)s %(message)s')

class MailHandler:
    def __init__(self, username):
        self.mail_handle = imaplib.IMAP4_SSL('imap.gmail.com')
        self.mail_id = username
        logging.info(f'Please provide the password:')
        rv, data = self.login()
        if rv != 'OK':
            logging.warning(f'Could not login')
        '''if os.path.exists(cfg.counter_file):
            self.in_mail_start_id = pickle.load(open(cfg.counter_file, 'r').read())
        else:
            self.in_mail_start_id = 1
            pickle.dump(1, open(cfg.counter_file, 'w'))'''
        self.in_mail_start_id = 1

    @staticmethod
    def load():
        return pickle.load(open(cfg.counter_file, 'r').read())

    def login(self):
        rv = None
        data = None
        try:
            rv, data = self.mail_handle.login(self.mail_id, getpass.getpass())
        except imaplib.IMAP4.error as e:
            raise PermissionError
        return rv, data

    def logout(self):
        logging.info(f'Logging out..')
        self.mail_handle.close()
        self.mail_handle.logout()

    def process_mailbox(self):
        try:
            self.mail_handle.select('Inbox')
            r, in_mail_ids = self.mail_handle.search(None, f'{self.in_mail_start_id}:*')
            in_mail_ids_int = list(map(int, in_mail_ids[0].decode('utf-8').split()))
            if in_mail_ids_int:
                last_read_mail_id = max(in_mail_ids_int)
                if last_read_mail_id >= self.in_mail_start_id:
                    logging.info(f'New mail...')
                    for i, item in enumerate(in_mail_ids[0].split()):
                        body = None
                        r, v = self.mail_handle.fetch(item, '(RFC822)')
                        msg = email.message_from_string(v[0][1].decode('utf-8'))

                        subject = email.header.make_header(email.header.decode_header(msg['Subject']))
                        if msg.is_multipart():
                            for part in msg.walk():
                                c_type = part.get_content_type()
                                if c_type == 'text/plain':
                                    body = part.get_payload(decode=True)  # decode
                        else:
                            body = msg.get_payload(decode=True)
                        save_as = {
                                   'subject': str(subject),
                                   'to': str(msg.get('To')),
                                   'from': str(msg.get('From')),
                                   'date': str(msg.get('Date')),
                                   'body': '\n'.join(str(body.decode('utf-8')).splitlines())
                                  }
                        with open(os.path.join(cfg.dest, str(time.ctime()).replace(" ", "_").replace(":", "_") + ".json"), 'w') as fp:
                            json.dump(save_as, fp)

                    self.in_mail_start_id = last_read_mail_id + 1
                else:
                    logging.info(f'No new mail')
            else:
                logging.info(f'Empty inbox')
                self.in_mail_start_id = 1 # If all the in messages are deleted

        except KeyboardInterrupt:
            logging.info(f'Keyboard Interrupt.')
            logging.info('Exiting. . .')
            self.logout()
            sys.exit()

        except imaplib.IMAP4.error as e:
            logging.error(f'ERROR: {e}')
            pass

    def watch_inbox(self):
        while True:
            self.process_mailbox()
            time.sleep(cfg.wait)

if __name__ == '__main__':
    current_attempt = 0
    while True:
        if current_attempt >= cfg.login_attempt:
            logging.warning(f'3 incorrect attempts')
            break
        try:
            mail_handle = MailHandler(cfg.user_mail_id)
            mail_handle.watch_inbox()
        except PermissionError as e:
            print('Incorrect credentials. ')
            current_attempt += 1

